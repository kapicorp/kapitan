import contextvars
import hashlib
import json
import logging
import multiprocessing
import os
import pickle
import sys
from contextlib import contextmanager, suppress
from importlib.util import source_from_cache
from pathlib import Path
from typing import Tuple

from kapitan.defaults import KADET_COMPONENT_MODULE_PREFIX
from kapitan.errors import CompileError


logger = logging.getLogger(__name__)

# Set of the files opened for reading inside record_reads(), else None
_reads = contextvars.ContextVar("files opened for reading", default=None)


def _record_open(event, args):
    """Audit hook: adds each file opened read-only to the set of record_reads()."""
    if event != "open" or (reads := _reads.get()) is None:
        return
    path, _, flags = args
    if not isinstance(path, str | bytes | os.PathLike) or flags & (
        os.O_WRONLY | os.O_RDWR
    ):
        return
    path = os.path.abspath(os.fsdecode(path))
    if path.endswith(".pyc"):
        # imports read only the bytecode while it is current, the source is what changes
        with suppress(ValueError):
            path = source_from_cache(path)
    reads.add(path)


sys.addaudithook(_record_open)


@contextmanager
def record_reads():
    """Collects the absolute paths of the files opened for reading in this context."""
    reads = set()
    token = _reads.set(reads)
    try:
        yield reads
    finally:
        _reads.reset(token)


class CacheMetrics:
    """Process-safe counters for cache hits, misses and fills.

    Backed by ``multiprocessing.Value`` so workers spawned by the compile
    Pool can share a single tally with the parent. Pass the same instance
    to every ``InputCache`` that should report into the same totals.
    """

    def __init__(self):
        # 'Q' is unsigned long long (uint64); plenty of headroom for counters.
        self.hits = multiprocessing.Value("Q", 0)
        self.misses = multiprocessing.Value("Q", 0)
        self.fills = multiprocessing.Value("Q", 0)

    @staticmethod
    def _bump(counter):
        with counter.get_lock():
            counter.value += 1

    def hit(self):
        self._bump(self.hits)

    def miss(self):
        self._bump(self.misses)

    def fill(self):
        self._bump(self.fills)

    def snapshot(self) -> dict:
        return {
            "hits": self.hits.value,
            "misses": self.misses.value,
            "fills": self.fills.value,
        }


class InputCache:
    def __init__(self, input_type_name: str, metrics: CacheMetrics | None = None):
        if cache_home := os.environ.get("XDG_CACHE_HOME"):
            self.input_cache_home = f"{cache_home}/kapitan/{input_type_name}"
        elif cache_home := os.environ.get("HOME"):
            self.input_cache_home = f"{cache_home}/.cache/kapitan/{input_type_name}"
        else:
            raise CompileError(
                "Could not get cache dir: $XDG_CACHE_HOME or $HOME not set."
            )

        self.input_type_name = input_type_name
        self.kv_cache = {}
        self.metrics = metrics if metrics is not None else CacheMetrics()

        logger.debug("Input cache home: %s", self.input_cache_home)

    def hash_paths(self, inputs_hash) -> Tuple[Path, Path, Path]:
        sub_path = Path(self.input_cache_home, inputs_hash[:2])
        cached_path = Path(sub_path, inputs_hash[2:])
        cached_path_lock = Path(str(cached_path) + ".lock")
        return cached_path, cached_path_lock, sub_path

    def reads_path(self, inputs_hash) -> Path:
        """Path of the list of files that the output for inputs_hash read."""
        cached_path, _, _ = self.hash_paths(inputs_hash)
        return Path(f"{cached_path}.reads")

    def reads_hash(self, inputs_hash, reads) -> str:
        """Mixes the paths and current content of the files in reads into inputs_hash."""
        if not reads:
            return inputs_hash
        h = self.hash_object()
        h.update(inputs_hash.encode())
        for path in reads:
            h.update(os.fsencode(path) + b"\0")
            walk_and_hash(Path(path), self, h)
        return h.hexdigest()

    def get(self, inputs_hash, lock_retries=2) -> dict | None:  # output_obj
        try:
            reads = json.loads(self.reads_path(inputs_hash).read_text())
        except FileNotFoundError:
            reads = []
        cached_path, cached_path_lock, _ = self.hash_paths(
            self.reads_hash(inputs_hash, reads)
        )
        if not cached_path_lock.exists():
            for retry in range(lock_retries):
                try:
                    with open(cached_path, "rb") as fp:
                        logger.debug(
                            "Loading cache hit: %s (try %d/%d)",
                            cached_path,
                            retry,
                            lock_retries,
                        )
                        output_obj = self.load_output(fp)
                        # load_output can return None when a kadet
                        # ModuleNotFoundError is swallowed; treat that as a
                        # miss so the caller recomputes.
                        if output_obj is None:
                            self.metrics.miss()
                        else:
                            self.metrics.hit()
                        return output_obj
                except FileNotFoundError:
                    pass
        self.metrics.miss()
        return None

    def set(self, inputs_hash, output_obj, lock_retries=2, reads=()):
        """Stores output_obj under inputs_hash and the content of the files in reads.

        The list of files is kept next to the output. get() hashes their
        current content, so a changed file is a miss.
        """
        # the cache's own files, e.g. a HelmChart() hit, are not inputs
        cache_root = os.path.abspath(os.path.dirname(self.input_cache_home)) + os.sep
        reads = sorted(path for path in reads if not path.startswith(cache_root))
        reads_path = self.reads_path(inputs_hash)
        if reads:
            reads_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = Path(f"{reads_path}.{os.getpid()}")
            tmp_path.write_text(json.dumps(reads))
            tmp_path.replace(reads_path)
        else:
            reads_path.unlink(missing_ok=True)

        inputs_hash = self.reads_hash(inputs_hash, reads)
        cached_path, cached_path_lock, sub_path = self.hash_paths(inputs_hash)
        for retry in range(lock_retries):
            # dont write if already exists
            if cached_path.exists():
                return inputs_hash

            if not cached_path_lock.exists():
                sub_path.mkdir(parents=True, exist_ok=True)
                with open(cached_path_lock, "wb") as fp:
                    logger.debug(
                        "Writing cache file: %s (try %d/%d)",
                        cached_path_lock,
                        retry,
                        lock_retries,
                    )
                    self.dump_output(output_obj, fp)
                cached_path_lock.rename(
                    Path(str(cached_path_lock).removesuffix(".lock"))
                )
                logger.debug(
                    "Moved cache lock to: %s (try %d/%d)",
                    cached_path,
                    retry,
                    lock_retries,
                )
                self.metrics.fill()
                return inputs_hash
        return None

    def set_value(self, key, value):
        self.kv_cache[key] = value

    def get_key(self, key):
        return self.kv_cache[key]

    @staticmethod
    def hash_object():
        return hashlib.blake2b(digest_size=32)

    @staticmethod
    def hash_file_digest(fp):
        # hashlib.file_digest is only available from Python 3.11.
        try:
            return hashlib.file_digest(fp, "blake2b")
        except AttributeError:
            h = hashlib.blake2b(digest_size=64)
            while chunk := fp.read(8192):
                h.update(chunk)
            return h

    def dump_output(self, output_obj, fp):
        return pickle.dump(output_obj, fp)

    def load_output(self, fp):
        try:
            return pickle.load(fp)
        except ModuleNotFoundError as e:
            # It is safe to ignore exception for kadet modules (prefixed with KADET_COMPONENT_MODULE_PREFIX)
            # since they are lazy loaded at runtime.
            # This is most likely to happen when using kapicorp/generators
            if e.name.startswith(KADET_COMPONENT_MODULE_PREFIX):
                pass
            else:
                raise


def walk_and_hash(path: Path, input_cache: InputCache | None, path_hash):
    """
    Recursively walk a path and update a hash object with the contents of all files.
    This implementation is deterministic.

    ``input_cache`` may be ``None`` or a falsy ``InputCache``; when truthy its
    ``kv_cache`` dict is used to memoize per-file digests across calls so the
    same file isn't re-read for every walk within a worker process.
    """
    if (reads := _reads.get()) is not None:
        # the kv_cache memo below skips the open() that _record_open sees
        reads.add(os.path.abspath(path))
    if not path.exists() or str(path).endswith("__pycache__"):
        return

    if path.is_file():
        if cached_hash_digest := get_path_hash_from_input_kv(path, input_cache):
            path_hash.update(cached_hash_digest)
            logger.debug(
                "KV Memory hit for path: %s, digest: %s", path, path_hash.hexdigest()
            )
            return

        with open(path, "rb") as fp:
            file_hash = InputCache.hash_file_digest(fp)
            digest = file_hash.digest()
            set_path_hash_input_kv(path, digest, input_cache)
            path_hash.update(digest)

    elif path.is_dir():
        for item in sorted(path.iterdir(), key=lambda p: p.name):
            walk_and_hash(item, input_cache, path_hash)


def get_path_hash_from_input_kv(path: Path, input_cache: InputCache | None):
    try:
        if input_cache:
            return input_cache.kv_cache[str(path)]
    except KeyError:
        return None


def set_path_hash_input_kv(path: Path, h_file, input_cache: InputCache | None):
    if input_cache:
        input_cache.kv_cache[str(path)] = h_file
