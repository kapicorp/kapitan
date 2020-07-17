# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import hashlib
import logging
import os
from collections import defaultdict
from distutils.dir_util import copy_tree
from functools import partial
from shutil import copyfile, rmtree
import platform
from mimetypes import MimeTypes
from git import GitCommandError
from git import Repo

from kapitan.errors import GitSubdirNotFoundError, GitFetchingError, HelmBindingUnavailableError
from kapitan.utils import (
    make_request,
    unpack_downloaded_file,
    safe_copy_tree,
    safe_copy_file,
    normalise_join_path,
)


logger = logging.getLogger(__name__)

try:
    from kapitan.dependency_manager.helm.helm_fetch_binding import ffi
except ImportError as ie:
    logger.debug("Error importing ffi from kapitan.dependency_manager.helm.helm_fetch_binding: {}".format(ie))
    pass  # make this feature optional


def fetch_dependencies(output_path, target_objs, save_dir, force, pool):
    """
    parses through the dependencies parameters in target_objs and fetches them
    all dependencies are first fetched into save_dir, after which they are copied to their respective output_path.
    overwites older version of existing dependencies if force fetced
    """
    # there could be multiple dependency items per source_uri due to reclass inheritance or
    # other user requirements. So create a mapping from source_uri to a set of dependencies with
    # that source_uri
    git_deps = defaultdict(list)
    http_deps = defaultdict(list)
    helm_deps = defaultdict(list)

    # this dict is to make sure no duplicated output_paths exist per source
    deps_output_paths = defaultdict(set)
    for target_obj in target_objs:
        try:
            dependencies = target_obj["dependencies"]
            for item in dependencies:
                dependency_type = item["type"]
                source_uri = item["source"]

                # The target key "output_path" is relative to the compile output path set by the user
                # point to the full output path
                full_output_path = normalise_join_path(output_path, item["output_path"])
                logger.debug("Updated output_path from {} to {}".format(item["output_path"], output_path))
                item["output_path"] = full_output_path

                if full_output_path in deps_output_paths[source_uri]:
                    # if the output_path is duplicated for the same source_uri
                    logger.warning("Skipping duplicate output path for uri {}".format(source_uri))
                    continue
                else:
                    deps_output_paths[source_uri].add(full_output_path)

                if dependency_type == "git":
                    git_deps[source_uri].append(item)
                elif dependency_type in ("http", "https"):
                    http_deps[source_uri].append(item)
                elif dependency_type == "helm":
                    version = item.get("version", "")
                    if version == "":
                        version = "latest"
                    helm_deps[item["chart_name"] + "-" + version].append(item)
                else:
                    logger.warning("{} is not a valid source type".format(dependency_type))

        except KeyError:
            logger.debug(
                "Target object {} has no 'dependencies' key, continuing".format(target_obj["vars"]["target"])
            )
            continue

    git_worker = partial(fetch_git_dependency, save_dir=save_dir, force=force)
    http_worker = partial(fetch_http_dependency, save_dir=save_dir, force=force)
    helm_worker = partial(fetch_helm_chart)
    [p.get() for p in pool.imap_unordered(http_worker, http_deps.items()) if p]
    [p.get() for p in pool.imap_unordered(git_worker, git_deps.items()) if p]
    [p.get() for p in pool.imap_unordered(helm_worker, helm_deps.items()) if p]


def fetch_git_dependency(dep_mapping, save_dir, force, item_type="Dependency"):
    """
    fetches a git repository at source into save_dir, and copy the repository into
    output_path stored in dep_mapping. ref is used to checkout if exists, fetches master branch by default.
    only subdir is copied into output_path if specified.
    """
    source, deps = dep_mapping
    # to avoid collisions between basename(source)
    path_hash = hashlib.sha256(os.path.dirname(source).encode()).hexdigest()[:8]
    cached_repo_path = os.path.join(save_dir, path_hash + os.path.basename(source))
    if not exists_in_cache(cached_repo_path) or force:
        fetch_git_source(source, cached_repo_path, item_type)
    else:
        logger.debug("Using cached {} {}".format(item_type, cached_repo_path))
    for dep in deps:
        repo = Repo(cached_repo_path)
        output_path = dep["output_path"]
        copy_src_path = cached_repo_path
        if "ref" in dep:
            ref = dep["ref"]
            repo.git.checkout(ref)
        else:
            repo.git.checkout("master")  # default ref

        if "subdir" in dep:
            sub_dir = dep["subdir"]
            full_subdir = os.path.join(cached_repo_path, sub_dir)
            if os.path.isdir(full_subdir):
                copy_src_path = full_subdir
            else:
                raise GitSubdirNotFoundError(
                    "{} {}: subdir {} not found in repo".format(item_type, source, sub_dir)
                )
        if force:
            copy_tree(copy_src_path, output_path)
        else:
            safe_copy_tree(copy_src_path, output_path)
        logger.info("{} {}: saved to {}".format(item_type, source, output_path))


def fetch_git_source(source, save_dir, item_type):
    """clones a git repository at source and saves into save_dir"""

    if os.path.exists(save_dir):
        rmtree(save_dir)
        logger.debug("Removed {}".format(save_dir))
    logger.info("{} {}: fetching now".format(item_type, source))
    try:
        Repo.clone_from(source, save_dir)
        logger.info("{} {}: successfully fetched".format(item_type, source))
        logger.debug("Git clone cached to {}".format(save_dir))
    except GitCommandError as e:
        logger.error(e)
        raise GitFetchingError("{} {}: fetching unsuccessful\n{}".format(item_type, source, e.stderr))


def fetch_http_dependency(dep_mapping, save_dir, force, item_type="Dependency"):
    """
    fetches a http[s] file at source and saves into save_dir, after which it is copied into
    the output_path stored in dep_mapping
    """
    source, deps = dep_mapping
    # to avoid collisions between basename(source)
    path_hash = hashlib.sha256(os.path.dirname(source).encode()).hexdigest()[:8]
    cached_source_path = os.path.join(save_dir, path_hash + os.path.basename(source))
    if not exists_in_cache(cached_source_path) or force:
        content_type = fetch_http_source(source, cached_source_path, item_type)
    else:
        logger.debug("Using cached {} {}".format(item_type, cached_source_path))
        content_type = MimeTypes().guess_type(cached_source_path)[0]
    for dep in deps:
        output_path = dep["output_path"]
        if dep.get("unpack", False):
            # ensure that the directory we are extracting to exists
            os.makedirs(output_path, exist_ok=True)
            if force:
                is_unpacked = unpack_downloaded_file(cached_source_path, output_path, content_type)
            else:
                unpack_output = os.path.join(save_dir, "extracted")
                os.makedirs(unpack_output)
                is_unpacked = unpack_downloaded_file(cached_source_path, unpack_output, content_type)
                safe_copy_tree(unpack_output, output_path)
                # delete unpack output
                rmtree(unpack_output)
            if is_unpacked:
                logger.info("{} {}: extracted to {}".format(item_type, source, output_path))
            else:
                logger.info(
                    "{} {}: Content-Type {} is not supported for unpack. Ignoring save".format(
                        item_type, source, content_type
                    )
                )
        else:
            # we are downloading a single file
            parent_dir = os.path.dirname(output_path)
            if parent_dir != "":
                os.makedirs(parent_dir, exist_ok=True)
            if force:
                copyfile(cached_source_path, output_path)
            else:
                safe_copy_file(cached_source_path, output_path)
            logger.info("{} {}: saved to {}".format(item_type, source, output_path))


def fetch_http_source(source, save_path, item_type):
    """downloads a http[s] file from source and saves into save_path(which is a file)"""

    if os.path.exists(save_path):
        os.remove(save_path)
        logger.debug("Removed {}".format(save_path))
    logger.info("{} {}: fetching now".format(item_type, source))
    content, content_type = make_request(source)
    logger.info("{} {}: successfully fetched".format(item_type, source))
    if content is not None:
        with open(save_path, "wb") as f:
            f.write(content)
        logger.debug("Cached to {}".format(save_path))
        return content_type
    logger.warning("{} {}: failed to fetch".format(item_type, source))
    return None


def fetch_helm_chart(dep_mapping):
    """
    downloads a helm chart and its subcharts from source then untars and moves it to save_dir
    """
    lib = initialise_helm_fetch_binding()
    unique_chart, deps = dep_mapping
    for dep in deps:
        chart_name = dep["chart_name"]
        version = dep.get("version", "")
        repo_url = dep["source"]
        destination_dir = dep["output_path"]

        if version == "":
            logger.info(
                "Dependency helm chart {} being fetch with using latest version available".format(chart_name)
            )

        logger.info("Dependency helm chart {} and version {}: fetching now".format(chart_name, version))
        c_chart_name = ffi.new("char[]", chart_name.encode("ascii"))
        c_version = ffi.new("char[]", version.encode("ascii"))
        c_repo_url = ffi.new("char[]", repo_url.encode("ascii"))
        c_destination_dir = ffi.new("char[]", destination_dir.encode("ascii"))

        res = lib.fetchHelmChart(c_repo_url, c_chart_name, c_version, c_destination_dir)
        response = ffi.string(res).decode("utf-8")
        if response != "":
            logger.warning(
                "Dependency helm chart {} and version {}: {}".format(chart_name, version, response)
            )
        else:
            logger.info(
                "Dependency helm chart {} and version {}: successfully fetched".format(chart_name, version)
            )
            logger.info(
                "Dependency helm chart {} and version {}: saved to {}".format(
                    chart_name, version, destination_dir
                )
            )


def initialise_helm_fetch_binding():
    """returns the dl_opened library (.so file) if exists, otherwise None"""
    if platform.system() not in ("Linux", "Darwin"):  # TODO: later add binding for Mac
        return None
    # binding_path is kapitan/dependency_manager/helm/helm_fetch.so
    binding_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "helm/helm_fetch.so")
    if not os.path.exists(binding_path):
        logger.debug("The helm_fetch binding does not exist at {}".format(binding_path))
        return None
    try:
        lib = ffi.dlopen(binding_path)
    except (NameError, OSError) as e:
        raise HelmBindingUnavailableError(
            "There was an error opening helm_fetch.so binding. " "Refer to the exception below:\n" + str(e)
        )
    return lib


def exists_in_cache(item_path):
    dep_cache_path = os.path.dirname(item_path)
    if not os.path.exists(dep_cache_path):
        return False
    return os.path.basename(item_path) in os.listdir(dep_cache_path)
