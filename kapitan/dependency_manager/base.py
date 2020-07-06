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
from git import GitCommandError
from kapitan.errors import GitFetchingError

from kapitan.errors import GitSubdirNotFoundError, HelmBindingUnavailableError
from kapitan.utils import make_request, unpack_downloaded_file

from git import Repo

logger = logging.getLogger(__name__)

try:
    from kapitan.dependency_manager.helm.helm_fetch_binding import ffi
except ImportError as ie:
    logger.debug("Error importing ffi from kapitan.dependency_manager.helm.helm_fetch_binding: {}".format(ie))
    pass  # make this feature optional


def fetch_dependencies(output_path, target_objs, temp_dir, pool):
    """
    parses through the dependencies parameters in target_objs and fetches them
    all dependencies are first fetched into tmp dir, after which they are copied to their respective output_path.
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
                full_output_path = os.path.join(output_path, item["output_path"])
                logger.debug("Updated output_path from {} to {}".format(item["output_path"], output_path))
                item["output_path"] = full_output_path

                if full_output_path in deps_output_paths[source_uri]:
                    # if the output_path is duplicated for the same source_uri
                    logger.warning("skipping duplicate output path for uri {}".format(source_uri))
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

        except KeyError:
            logger.debug(
                "Target object {} has no 'dependencies' key, continuing".format(target_obj["vars"]["target"])
            )
            continue

    git_worker = partial(fetch_git_dependency, save_dir=temp_dir)
    http_worker = partial(fetch_http_dependency, save_dir=temp_dir)
    helm_worker = partial(fetch_helm_chart, save_dir=temp_dir)
    [p.get() for p in pool.imap_unordered(http_worker, http_deps.items()) if p]
    [p.get() for p in pool.imap_unordered(git_worker, git_deps.items()) if p]
    [p.get() for p in pool.imap_unordered(helm_worker, helm_deps.items()) if p]


def fetch_git_dependency(dep_mapping, save_dir, item_type="dependency"):
    """
    fetches a git repository at source into save_dir, and copy the repository into output_path
    ref is used to checkout if exists
    only subdir is copied into output_path if specified
    """
    source, deps = dep_mapping
    fetch_git_source(source, save_dir, item_type)
    for dep in deps:
        repo_path = os.path.join(save_dir, os.path.basename(source))
        repo = Repo(repo_path)
        output_path = dep["output_path"]
        copy_src_path = repo_path
        if "ref" in dep:
            ref = dep["ref"]
            repo.git.checkout(ref)
        else:
            repo.git.checkout("master")  # default ref

        if "subdir" in dep:
            sub_dir = dep["subdir"]
            full_subdir = os.path.join(repo_path, sub_dir)
            if os.path.isdir(full_subdir):
                copy_src_path = full_subdir
            else:
                raise GitSubdirNotFoundError(
                    "{} {} : subdir {} not found in repo".format(item_type, source, sub_dir)
                )

        if not os.path.exists(os.path.abspath(output_path)) and item_type == "dependency":
            copy_tree(copy_src_path, output_path)
            logger.info("dependency {} : saved to {}".format(source, output_path))
        elif item_type == "inventory":
            copy_tree(copy_src_path, output_path, update=True)
            logger.info("inventory {} : saved to {}".format(source, output_path))

    rmtree(repo_path)
    logger.debug("repo path {} deleted".format(repo_path))


def fetch_git_source(source, save_dir, item_type):
    """clones a git repository at source and saves into save_dir"""
    logger.info("{} {} : fetching now".format(item_type, source))
    try:
        Repo.clone_from(source, os.path.join(save_dir, os.path.basename(source)))
        logger.info("{} {} : successfully fetched".format(item_type, source))
        logger.debug(
            "git clone saved temporarily to {}".format(os.path.join(save_dir, os.path.basename(source)))
        )
    except GitCommandError as e:
        logger.error(e)
        raise GitFetchingError("{} {} : fetching unsuccessful\n{}".format(item_type, source, e.stderr))


def fetch_http_dependency(dep_mapping, save_dir, item_type="dependency"):
    """
    fetches a http[s] file at source and saves into save_dir, after which it is copied into
    the output_path stored in dep_mapping
    """
    source, deps = dep_mapping
    content_type = fetch_http_source(source, save_dir, item_type)
    path_hash = hashlib.sha256(os.path.dirname(source).encode()).hexdigest()[:8]
    copy_src_path = os.path.join(save_dir, path_hash + os.path.basename(source))
    for dep in deps:
        output_path = dep["output_path"]
        if dep.get("unpack", False):
            # ensure that the directory we are extracting to exists
            os.makedirs(output_path, exist_ok=True)
            is_unpacked = unpack_downloaded_file(copy_src_path, output_path, content_type)
            if is_unpacked:
                logger.info("{} {} : extracted to {}".format(item_type, source, output_path))
            else:
                logger.info(
                    "{} {} : Content-Type {} is not supported for unpack. Ignoring save".format(
                        item_type, source, content_type
                    )
                )
        else:
            # we are downloading a single file
            parent_dir = os.path.dirname(output_path)
            if parent_dir != "":
                os.makedirs(parent_dir, exist_ok=True)
            copyfile(copy_src_path, output_path)
            logger.info("{} {} : saved to {}".format(item_type, source, output_path))


def fetch_http_source(source, save_dir, item_type):
    """downloads a http[s] file from source and saves into save_dir"""
    logger.info("{} {} : fetching now".format(item_type, source))
    content, content_type = make_request(source)
    logger.info("{} {} : successfully fetched".format(item_type, source))
    if content is not None:
        basename = os.path.basename(source)
        # to avoid collisions between basename(source)
        path_hash = hashlib.sha256(os.path.dirname(source).encode()).hexdigest()[:8]
        full_save_path = os.path.join(save_dir, path_hash + basename)
        with open(full_save_path, "wb") as f:
            f.write(content)
        return content_type
    logger.warning("{} {} : failed to fetch".format(item_type, source))
    return None


def fetch_helm_chart(dep_mapping, save_dir):
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
