import shutil
from git import Repo
import logging
import os
from distutils.dir_util import copy_tree, remove_tree

from kapitan.dependency_manager.base import Dependency

logger = logging.getLogger(__name__)


class Git(Dependency):
    def __init__(self, source_uri, output_path, **kwargs):
        super().__init__(source_uri, output_path)
        self.kwargs = kwargs

    def fetch(self):
        repo_cache_dirname = self._get_repo_cache_dirname()
        if 'fresh_fetch' in self.kwargs:
            self._clear_cache()
        repo = self._get_repo_cache_or_clone()

        if 'ref' in self.kwargs:
            ref = self.kwargs['ref']
            repo.git.checkout(ref)
            copy_tree(repo_cache_dirname, self.output_path)

        if 'subdir' in self.kwargs:
            full_subdir = os.path.join(repo_cache_dirname, self.kwargs['subdir'])

            if os.path.isdir(os.path.join(full_subdir)):
                copy_tree(full_subdir, self.output_path)

    def _get_repo_cache_dirname(self):
        repo_name = os.path.basename(self.source_uri)
        repo_cache_dir = os.path.join(self.cache_dir, repo_name)
        return repo_cache_dir

    def _get_repo_cache_or_clone(self):
        repo_cache_dir = os.path.join(self._get_repo_cache_dirname())
        if os.path.isdir(repo_cache_dir):
            repo = Repo(repo_cache_dir)
            logger.info('Repository cache loaded from {}'.format(repo_cache_dir))
        else:
            logger.info("Fetching dependency at {}".format(self.source_uri))
            repo = Repo.clone_from(self.source_uri, repo_cache_dir)
            logger.info('Repository successfully fetched from {}'.format(self.source_uri))
        return repo

    def _clear_cache(self):
        repo_cache_dir = self._get_repo_cache_dirname()
        remove_tree(repo_cache_dir)
        logger.info("Removed cache in {}".format(repo_cache_dir))
