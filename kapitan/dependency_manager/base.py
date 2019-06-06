import os
from abc import abstractmethod


class Dependency(object):
    cache_path = '.cache'
    dependencies_root_path = ''

    @classmethod
    def set_cache_path(cls, new_path):
        cls.cache_path = os.path.join(new_path)

    @classmethod
    def set_root_output_path(cls, new_path):
        """prepends absolute path to output_path. Only to be used in testing"""
        cls.dependencies_root_path = new_path

    def __init__(self, source_uri, output_path):
        self.source_uri = source_uri
        self.output_path = output_path

    @abstractmethod
    def fetch(self):
        pass

    @abstractmethod
    def clear_cache(self):
        pass


