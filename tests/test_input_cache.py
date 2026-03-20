import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kapitan.errors import CompileError
from kapitan.inputs.cache import InputCache


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
