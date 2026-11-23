import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kapitan.errors import CompileError
from kapitan.inputs.cache import (
    CacheMetrics,
    InputCache,
    record_reads,
    walk_and_hash,
)
from kapitan.inputs.kadet import Kadet
from kapitan.inventory.model.input_types import KapitanInputTypeKadetConfig


class InputCacheTest(unittest.TestCase):
    def test_cache_home_xdg(self):
        """
        tests if the cache home is set via XDG_CACHE_HOME
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"XDG_CACHE_HOME": tmpdir}):
                cache = InputCache("test_input")
                self.assertEqual(cache.input_cache_home, f"{tmpdir}/kapitan/test_input")

    def test_cache_home_home(self):
        """
        tests if the cache home is set via HOME
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"HOME": tmpdir}, clear=True):
                cache = InputCache("test_input")
                self.assertEqual(
                    cache.input_cache_home, f"{tmpdir}/.cache/kapitan/test_input"
                )

    def test_cache_home_missing(self):
        """
        tests if CompileError is raised when no cache home can be set
        """
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(CompileError):
                InputCache("test_input")

    def test_hash_paths(self):
        """
        tests if the cache paths are correctly derived from the input hash
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"HOME": tmpdir}, clear=True):
                cache = InputCache("test_input")
                inputs_hash = "abcdef123456"
                cached_path, cached_path_lock, sub_path = cache.hash_paths(inputs_hash)
                self.assertEqual(sub_path, Path(cache.input_cache_home, "ab"))
                self.assertEqual(cached_path, Path(sub_path, "cdef123456"))
                self.assertEqual(cached_path_lock, Path(str(cached_path) + ".lock"))

    def test_set_and_get(self):
        """
        tests if an object can be set and retrieved from the cache
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"HOME": tmpdir}, clear=True):
                cache = InputCache("test_input")
                inputs_hash = "abcdef123456"
                test_obj = {"a": 1, "b": 2}

                # Test get on a non-existent cache entry
                self.assertIsNone(cache.get(inputs_hash))

                # Test set and get
                cache.set(inputs_hash, test_obj)
                retrieved_obj = cache.get(inputs_hash)
                self.assertEqual(test_obj, retrieved_obj)

                # Test that set does not overwrite
                cache.set(inputs_hash, {"c": 3})
                retrieved_obj = cache.get(inputs_hash)
                self.assertEqual(test_obj, retrieved_obj)

    def test_kv_cache(self):
        """
        tests the in-memory key-value cache
        """
        cache = InputCache("test_input")
        cache.set_value("key1", "value1")
        self.assertEqual(cache.get_key("key1"), "value1")

    def test_hashing(self):
        """
        tests the hashing functions
        """
        cache = InputCache("test_input")
        hasher = cache.hash_object()
        self.assertIsNotNone(hasher)

        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            tmpfile.write(b"test content")
            tmpfile.flush()
            tmpfile.seek(0)
            digest = cache.hash_file_digest(tmpfile)
            self.assertIsNotNone(digest)
        os.remove(tmpfile.name)

    def test_get_cache_miss(self):
        """
        tests if cache.get returns None on a cache miss
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"HOME": tmpdir}, clear=True):
                cache = InputCache("test_input")
                inputs_hash = "nonexistenthash"
                self.assertIsNone(cache.get(inputs_hash))

    def test_cache_lock_contention(self):
        """
        tests cache lock contention
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"HOME": tmpdir}, clear=True):
                cache = InputCache("test_input")
                inputs_hash = "abcdef123456"
                test_obj = {"a": 1, "b": 2}

                _, cached_path_lock, sub_path = cache.hash_paths(inputs_hash)
                sub_path.mkdir(parents=True, exist_ok=True)
                cached_path_lock.touch()

                # Test get with lock file present
                self.assertIsNone(cache.get(inputs_hash))

                # Test set with lock file present
                self.assertIsNone(cache.set(inputs_hash, test_obj))

    def test_set_file_exists_error(self):
        """
        tests if cache.set handles FileExistsError gracefully
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"HOME": tmpdir}, clear=True):
                cache = InputCache("test_input")
                inputs_hash = "abcdef123456"
                test_obj = {"a": 1, "b": 2}

                # Mocking os.rename to raise FileExistsError
                with patch("pathlib.Path.rename", side_effect=FileExistsError):
                    with self.assertRaises(FileExistsError):
                        cache.set(inputs_hash, test_obj)

    def test_get_file_not_found_error(self):
        """
        tests if cache.get handles FileNotFoundError gracefully
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"HOME": tmpdir}, clear=True):
                cache = InputCache("test_input")
                inputs_hash = "abcdef123456"

                with patch("builtins.open", side_effect=FileNotFoundError):
                    self.assertIsNone(cache.get(inputs_hash))

    def test_different_input_types(self):
        """
        tests if caches for different input types are stored in separate directories
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"HOME": tmpdir}, clear=True):
                cache1 = InputCache("input1")
                cache2 = InputCache("input2")
                self.assertNotEqual(cache1.input_cache_home, cache2.input_cache_home)
                self.assertTrue("input1" in cache1.input_cache_home)
                self.assertTrue("input2" in cache2.input_cache_home)

    def test_metrics_track_hits_misses_fills(self):
        """
        cache.get / cache.set should bump the shared CacheMetrics counters.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"HOME": tmpdir}, clear=True):
                metrics = CacheMetrics()
                cache = InputCache("test_input", metrics=metrics)
                inputs_hash = "abcdef123456"
                test_obj = {"a": 1}

                # miss: nothing cached yet
                self.assertIsNone(cache.get(inputs_hash))
                self.assertEqual(
                    metrics.snapshot(), {"hits": 0, "misses": 1, "fills": 0}
                )

                # fill: write a new entry
                cache.set(inputs_hash, test_obj)
                self.assertEqual(
                    metrics.snapshot(), {"hits": 0, "misses": 1, "fills": 1}
                )

                # hit: the same key now returns
                self.assertEqual(cache.get(inputs_hash), test_obj)
                self.assertEqual(
                    metrics.snapshot(), {"hits": 1, "misses": 1, "fills": 1}
                )

                # second set with the same key is a no-op and must not count as a fill
                cache.set(inputs_hash, {"c": 3})
                self.assertEqual(
                    metrics.snapshot(), {"hits": 1, "misses": 1, "fills": 1}
                )

    def test_metrics_shared_across_caches(self):
        """
        Two InputCache instances sharing the same CacheMetrics should
        aggregate counters together (simulating multiple worker processes).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"HOME": tmpdir}, clear=True):
                metrics = CacheMetrics()
                cache_a = InputCache("input_a", metrics=metrics)
                cache_b = InputCache("input_b", metrics=metrics)

                cache_a.get("hash_a")  # miss
                cache_b.get("hash_b")  # miss
                cache_a.set("hash_a", {"x": 1})  # fill
                cache_b.set("hash_b", {"y": 2})  # fill
                cache_a.get("hash_a")  # hit
                cache_b.get("hash_b")  # hit

                self.assertEqual(
                    metrics.snapshot(), {"hits": 2, "misses": 2, "fills": 2}
                )

    def test_dump_and_load_output(self):
        """
        tests the dump_output and load_output methods
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"HOME": tmpdir}, clear=True):
                cache = InputCache("test_input")
                test_obj = {"a": 1, "b": 2}
                file_path = Path(tmpdir) / "test.txt"

                with open(file_path, "wb") as fp:
                    cache.dump_output(test_obj, fp)

                with open(file_path, "rb") as fp:
                    loaded_obj = cache.load_output(fp)

                self.assertEqual(test_obj, loaded_obj)


class KadetCacheReadsTest(unittest.TestCase):
    """Files a kadet module opens are part of its cache key (#1620)."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        env = patch.dict(os.environ, {"XDG_CACHE_HOME": str(self.root / "cache")})
        env.start()
        self.addCleanup(env.stop)
        self.component = self.root / "reads_component"
        self.component.mkdir()
        self.component.joinpath("__init__.py").write_text(
            "import os\n"
            "from kapitan.inputs.kadet import load_from_search_paths, search_paths\n"
            "lib = load_from_search_paths('reads_lib')\n"
            "def main():\n"
            "    with open(os.path.join(search_paths.get()[0], 'data.txt')) as f:\n"
            "        return {'out': {'data': f.read(), 'lib': lib.VALUE}}\n"
        )
        self.addCleanup(sys.modules.pop, "kadet_component_reads_component", None)
        self.root.joinpath("reads_lib").mkdir()

    def compile(self, compile_path=None, cache=None):
        """Compiles the component as a new kapitan run would; returns output and hits."""
        cache = cache or InputCache("kadet")
        compiler = Kadet.__new__(Kadet)
        compiler.target_name = "demo"
        compiler.search_paths = [str(self.root)]
        config = KapitanInputTypeKadetConfig(
            input_paths=[str(self.component)], output_path="."
        )
        with (
            patch.object(compiler, "cacheable", return_value=cache),
            patch("kapitan.inputs.kadet.inventory_digest", return_value=b"inv"),
            patch("kapitan.inputs.kadet.helm_dependencies_digest", return_value=None),
            patch("kapitan.inputs.kadet.consumed_topics_digest", return_value=None),
            patch.object(compiler, "to_file") as to_file,
        ):
            compiler.compile_file(
                config, str(self.component), compile_path or str(self.root / "out")
            )
        return to_file.call_args.args[2], cache.metrics.snapshot()["hits"]

    def test_files_read_outside_input_path_invalidate_cache(self):
        self.root.joinpath("data.txt").write_text("v1")
        self.root.joinpath("reads_lib", "__init__.py").write_text("VALUE = 'v1'\n")
        self.assertEqual(self.compile(), ({"data": "v1", "lib": "v1"}, 0))
        self.assertEqual(self.compile(), ({"data": "v1", "lib": "v1"}, 1))

        self.root.joinpath("data.txt").write_text("v2")
        self.assertEqual(self.compile(), ({"data": "v2", "lib": "v1"}, 0))

        # this run loaded reads_lib from its .pyc, the key must still use the source
        self.root.joinpath("reads_lib", "__init__.py").write_text("VALUE = 'v2-lib'\n")
        self.assertEqual(self.compile(), ({"data": "v2", "lib": "v2-lib"}, 0))

    def test_files_below_compile_path_are_keyed_by_relative_path(self):
        # like mutate: reads what an earlier compile entry wrote in this run
        self.component.joinpath("__init__.py").write_text(
            "import os\n"
            "def main(input_params):\n"
            "    path = os.path.join(input_params['compile_path'], 'earlier.yml')\n"
            "    with open(path) as f:\n"
            "        return {'out': f.read()}\n"
        )
        for content, hits in (("v1", 0), ("v1", 1), ("v2", 0), ("v2", 1)):
            # each run compiles into a new temporary directory and removes it
            with tempfile.TemporaryDirectory() as compile_path:
                Path(compile_path, "earlier.yml").write_text(content)
                self.assertEqual(self.compile(compile_path), (content, hits))

        # a later compile entry may rewrite the file within the same run
        cache = InputCache("kadet")
        with tempfile.TemporaryDirectory() as compile_path:
            Path(compile_path, "earlier.yml").write_text("v3")
            self.assertEqual(self.compile(compile_path, cache), ("v3", 0))
            Path(compile_path, "earlier.yml").write_text("v4")
            self.assertEqual(self.compile(compile_path, cache), ("v4", 0))

    def test_walk_and_hash_records_memoized_paths(self):
        cache = InputCache("kadet")
        data = self.root / "data.txt"
        data.write_text("v1")
        walk_and_hash(data, cache, InputCache.hash_object())
        with record_reads() as reads:
            walk_and_hash(data, cache, InputCache.hash_object())
        self.assertEqual(reads, {str(data)})
