import logging
import os
import requests

from kapitan.dependency_manager.base import Dependency

logger = logging.getLogger(__name__)


class Http(Dependency):
    def __init__(self, source_uri, output_path, **kwargs):
        super().__init__(source_uri, os.path.join(Dependency.dependencies_root_path, output_path))
        self.kwargs = kwargs

    def fetch(self):
        if self.kwargs.get('fetch_always', False):
            self.clear_cache()

        if os.path.isfile(self.output_path):
            logging.info("Dependency {} : already exists. skipping fetch".format(self.source_uri, self.output_path))
            return

        content = self._make_request()
        if content is not None:
            dir = os.path.dirname(self.output_path)
            if not os.path.exists(dir):
                os.makedirs(dir)
            with open(self.output_path, 'wb') as f:
                f.write(content)

    def _make_request(self):
        logger.info("Dependency {} : fetching now".format(self.source_uri))
        r = requests.get(self.source_uri)
        if r.ok:
            logger.info("Dependency {} : successfully fetched".format(self.source_uri))
            return r.content
        else:
            r.raise_for_status()
        return None

    def clear_cache(self):
        if os.path.isfile(self.output_path):
            os.remove(self.output_path)
            logger.info("Dependency {} : removed cache from {}".format(self.source_uri, self.output_path))
