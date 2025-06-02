import hashlib
import os
from pathlib import Path
from kapitan.errors import CompileError
import logging
from typing import Tuple
import json

logger = logging.getLogger(__name__)


class InputCache(object):
    def __init__(self, input_type_name: str):
        if cache_home := os.environ.get("XDG_CACHE_HOME"):
            self.input_cache_home = f"{cache_home}/kapitan/{input_type_name}"
        elif cache_home := os.environ.get("HOME"):
            self.input_cache_home = f"{cache_home}/.cache/kapitan/{input_type_name}"
        else:
            raise CompileError("Could not get cache dir: $XDG_CACHE_HOME or $HOME not set.")

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
                        logger.debug("Loading cache hit: %s", cached_path)
                        return json.load(fp)
                except FileNotFoundError:
                    pass
        return None

    def set(self, inputs_hash, output_obj, lock_retries=2):
        cached_path, cached_path_lock, sub_path = self.hash_paths(inputs_hash)
        for retry in range(lock_retries):
            if not cached_path_lock.exists():
                sub_path.mkdir(parents=True, exist_ok=True)
                with open(cached_path_lock, "wb") as fp:
                    output_obj_dump = json.dumps(output_obj, sort_keys=True).encode("utf-8")
                    logger.debug("Writing cache: %s", cached_path_lock)
                    fp.write(output_obj_dump)
                cached_path_lock.rename(Path(str(cached_path_lock).removesuffix(".lock")))
                logger.debug("Moved cache lock to: %s", cached_path)

                return inputs_hash
        return None

    @staticmethod
    def hash_object():
        return hashlib.blake2b(digest_size=32)
