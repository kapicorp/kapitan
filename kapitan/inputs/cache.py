import hashlib
import pickle
import os
from pathlib import Path
from kapitan.errors import CompileError
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class InputCache:
    def __init__(self, input_type_name: str):
        if cache_home := os.environ.get("XDG_CACHE_HOME"):
            self.input_cache_home = f"{cache_home}/kapitan/{input_type_name}"
        elif cache_home := os.environ.get("HOME"):
            self.input_cache_home = f"{cache_home}/.cache/kapitan/{input_type_name}"
        else:
            raise CompileError(
                "Could not get cache dir: $XDG_CACHE_HOME or $HOME not set."
            )

        self.kv_cache = {}

        logger.debug("Input cache home: %s", self.input_cache_home)

    def hash_paths(self, inputs_hash) -> Tuple[Path, Path, Path]:
        sub_path = Path(self.input_cache_home, inputs_hash[:2])
        cached_path = Path(sub_path, inputs_hash[2:])
        cached_path_lock = Path(str(cached_path) + ".lock")
        return cached_path, cached_path_lock, sub_path

    def get(self, inputs_hash, lock_retries=2) -> dict:  # output_obj
        cached_path, cached_path_lock, _ = self.hash_paths(inputs_hash)
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
                        return self.load_output(fp)
                except FileNotFoundError:
                    pass
        return None

    def set(self, inputs_hash, output_obj, lock_retries=2):
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
        return hashlib.file_digest(fp, "blake2b")

    def dump_output(self, output_obj, fp):
        return pickle.dump(output_obj, fp)

    def load_output(self, fp):
        return pickle.load(fp)
