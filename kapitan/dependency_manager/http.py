import logging
import os
from distutils.file_util import copy_file
import requests

from kapitan.dependency_manager.base import Dependency
logger = logging.getLogger(__name__)


class Http(Dependency):
    def __init__(self, source_uri, output_path, **kwargs):
        super().__init__(source_uri, output_path)
        self.kwargs = kwargs

    def fetch(self):
        file_cache_path = self._get_file_cache_path()
        if 'fresh_fetch' in self.kwargs:
            self._clear_cache()

        if not os.path.isfile(file_cache_path):
            self.make_request()

        copy_file(file_cache_path, self.output_path)

    def make_request(self):
        logger.info("fetching dependency at {}".format(self.source_uri))
        r = requests.get(self.source_uri)
        if r.ok:
            with open(self._get_file_cache_path(), 'wb') as f:
                f.write(r.content)
        else:
            r.raise_for_status()

        logger.info("successfully fetched dependency at {}".format(self.source_uri))

    def _get_file_cache_path(self):
        cache_filename = os.path.basename(self.source_uri)
        cache_file_path = os.path.join(Dependency.cache_path, cache_filename)
        return cache_file_path

    def _clear_cache(self):
        file_path = self._get_file_cache_path()
        if os.path.isfile(file_path):
            os.remove(file_path)
