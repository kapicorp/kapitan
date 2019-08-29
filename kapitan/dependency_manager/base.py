import os
import tempfile
from collections import defaultdict
import logging
from distutils.dir_util import copy_tree
from functools import partial
from shutil import copyfile
import hashlib
import tarfile
import re
from zipfile import ZipFile
from git import Repo

from kapitan.errors import GitSubdirNotFoundError
from kapitan.utils import make_request

logger = logging.getLogger(__name__)

# this is used just to change the root directory of save_dir in testing
DEPENDENCY_OUTPUT_CONFIG = {}


def fetch_dependencies(target_objs, pool):
    """
    parses through the dependencies parameters in target_objs and fetches them
    all dependencies are first fetched into tmp dir, after which they are copied to their respective output_path.
    dependencies whose output_path already exists are skipped
    """
    temp_dir = tempfile.mkdtemp()
    # there could be multiple dependency items per source_uri due to reclass inheritance or
    # other user requirements. So create a mapping from source_uri to a set of dependencies with
    # that source_uri
    git_deps = defaultdict(list)
    http_deps = defaultdict(list)

    # this dict is to make sure no duplicated output_paths exist per source
    deps_output_paths = defaultdict(set)
    for target_obj in target_objs:
        try:
            dependencies = target_obj["dependencies"]
            for item in dependencies:
                dependency_type = item["type"]
                source_uri = item["source"]
                if "root_dir" in DEPENDENCY_OUTPUT_CONFIG:
                    # should only be used in test environment
                    item["output_path"] = os.path.join(DEPENDENCY_OUTPUT_CONFIG["root_dir"], item["output_path"])
                output_path = item["output_path"]
                if os.path.exists(os.path.abspath(output_path)) and not item.get('unpack', False):
                    # if unpack: True, then allow the user to specify the parent directory as output_path where the
                    # files will be extracted to
                    logger.info("Dependency {} : already exists. Ignoring".format(output_path))
                    continue

                if output_path in deps_output_paths[source_uri]:
                    # if the output_path is duplicated for the same source_uri
                    continue
                else:
                    deps_output_paths[source_uri].add(output_path)

                if dependency_type == "git":
                    git_deps[source_uri].append(item)
                elif dependency_type in ("http", "https"):
                    http_deps[source_uri].append(item)

        except KeyError:
            continue

    git_worker = partial(fetch_git_dependency, save_dir=temp_dir)
    http_worker = partial(fetch_http_dependency, save_dir=temp_dir)
    [p.get() for p in pool.imap_unordered(http_worker, http_deps.items()) if p]
    [p.get() for p in pool.imap_unordered(git_worker, git_deps.items()) if p]


def fetch_git_dependency(dep_mapping, save_dir):
    """
    fetches a git repository at source into save_dir, and copy the repository into output_path
    ref is used to checkout if exists
    only subdir is copied into output_path if specified
    """
    source, deps = dep_mapping
    fetch_git_source(source, save_dir)
    for dep in deps:
        repo_path = os.path.join(save_dir, os.path.basename(source))
        repo = Repo(repo_path)
        output_path = dep["output_path"]
        copy_src_path = repo_path
        if 'ref' in dep:
            ref = dep['ref']
            repo.git.checkout(ref)
        else:
            repo = Repo(repo_path)
            repo.git.checkout("master")  # default ref

        if 'subdir' in dep:
            sub_dir = dep['subdir']
            full_subdir = os.path.join(repo_path, sub_dir)
            if os.path.isdir(full_subdir):
                copy_src_path = full_subdir
            else:
                raise GitSubdirNotFoundError("Dependency {} : subdir {} not found in repo".format(source, sub_dir))

        if not os.path.exists(os.path.abspath(output_path)):
            copy_tree(copy_src_path, output_path)
            logger.info("Dependency {} : saved to {}".format(source, output_path))


def fetch_git_source(source, save_dir):
    """clones a git repository at source and saves into save_dir"""
    logger.info("Dependency {} : fetching now".format(source))
    Repo.clone_from(source, os.path.join(save_dir, os.path.basename(source)))
    logger.info('Dependency {} : successfully fetched'.format(source))


def fetch_http_dependency(dep_mapping, save_dir):
    """
    fetches a http[s] file at source and saves into save_dir, after which it is copied into
    the output_path stored in dep_mapping
    """
    source, deps = dep_mapping
    content_type = fetch_http_source(source, save_dir)
    path_hash = hashlib.sha256(os.path.dirname(source).encode()).hexdigest()[:8]
    copy_src_path = os.path.join(save_dir, path_hash + os.path.basename(source))
    for dep in deps:
        output_path = dep["output_path"]
        if dep.get('unpack', False):
            # ensure that the directory we are extracting to exists
            os.makedirs(output_path, exist_ok=True)
            is_unpacked = False
            if content_type == 'application/x-tar':
                tar = tarfile.open(copy_src_path)
                tar.extractall(path=output_path)
                tar.close()
                is_unpacked = True
            elif content_type == 'application/zip':
                zfile = ZipFile(copy_src_path)
                zfile.extractall(output_path)
                zfile.close()
                is_unpacked = True
            elif content_type == 'application/octet-stream':
                if re.search(r'(\.tar\.gz|\.tgz)$', source):
                    tar = tarfile.open(copy_src_path)
                    tar.extractall(path=output_path)
                    tar.close()
                    is_unpacked = True
            if is_unpacked:
                logger.info("Dependency {} : extracted to {}".format(source, output_path))
            else:
                logger.info("Dependency {} : Content-Type {} is not supported for unpack. Ignoring save".
                            format(source, content_type))
        else:
            # we are downloading a single file
            parent_dir = os.path.dirname(output_path)
            if parent_dir != '':
                os.makedirs(parent_dir, exist_ok=True)
            copyfile(copy_src_path, output_path)
            logger.info("Dependency {} : saved to {}".format(source, output_path))


def fetch_http_source(source, save_dir):
    """downloads a http[s] file from source and saves into save_dir"""
    logger.info("Dependency {} : fetching now".format(source))
    content, content_type = make_request(source)
    logger.info("Dependency {} : successfully fetched".format(source))
    if content is not None:
        basename = os.path.basename(source)
        # to avoid collisions between basename(source)
        path_hash = hashlib.sha256(os.path.dirname(source).encode()).hexdigest()[:8]
        full_save_path = os.path.join(save_dir,  path_hash + basename)
        with open(full_save_path, 'wb') as f:
            f.write(content)
        return content_type
    else:
        logger.warning("Dependency {} : failed to fetch".format(source))
        return None
