import os
from abc import abstractmethod


class Dependency(object):
    cache_path = './components/external'

    @classmethod
    def set_cache_path(cls, new_path):
        cls.cache_path = os.path.join(new_path, 'external')

    def __init__(self, source_uri, output_path):
        self.source_uri = source_uri
        self.output_path = output_path

    @abstractmethod
    def fetch(self):
        pass


