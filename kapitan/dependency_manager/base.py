# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import hashlib
import logging
import multiprocessing
import os
from collections import defaultdict, namedtuple
from distutils.dir_util import copy_tree
from functools import partial
from mimetypes import MimeTypes
from shutil import copyfile, rmtree

from git import GitCommandError
from git import Repo
from kapitan.errors import GitSubdirNotFoundError, GitFetchingError, HelmFetchingError
from kapitan.helm_cli import helm_cli
from kapitan.utils import (
    make_request,
    unpack_downloaded_file,
    safe_copy_tree,
    safe_copy_file,
    normalise_join_path,
)

logger = logging.getLogger(__name__)

HelmSource = namedtuple("HelmSource", ["repo", "chart_name", "version", "helm_path"])


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
                logger.debug("Updated output_path from %s to %s", item["output_path"], output_path)
                item["output_path"] = full_output_path

                if full_output_path in deps_output_paths[source_uri]:
                    # if the output_path is duplicated for the same source_uri
                    logger.warning("Skipping duplicate output path for uri %s", source_uri)
                    continue
                else:
                    deps_output_paths[source_uri].add(full_output_path)

                if dependency_type == "git":
                    git_deps[source_uri].append(item)
                elif dependency_type in ("http", "https"):
                    http_deps[source_uri].append(item)
                elif dependency_type == "helm":
                    version = item.get("version", "")
                    helm_deps[
                        HelmSource(source_uri, item["chart_name"], version, item.get("helm_path"))
                    ].append(item)
                else:
                    logger.warning("%s is not a valid source type", dependency_type)

        except KeyError:
            logger.debug(
                "Target object %s has no 'dependencies' key, continuing", target_obj["vars"]["target"]
            )
            continue

    git_worker = partial(fetch_git_dependency, save_dir=save_dir, force=force)
    http_worker = partial(fetch_http_dependency, save_dir=save_dir, force=force)
    helm_worker = partial(fetch_helm_chart, save_dir=save_dir, force=force)
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
        logger.debug("Using cached %s %s", item_type, cached_repo_path)
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
        logger.info("%s %s: saved to %s", item_type, source, output_path)


def fetch_git_source(source, save_dir, item_type):
    """clones a git repository at source and saves into save_dir"""

    if os.path.exists(save_dir):
        rmtree(save_dir)
        logger.debug("Removed %s", save_dir)
    logger.info("%s %s: fetching now", item_type, source)
    try:
        Repo.clone_from(source, save_dir)
        logger.info("%s %s: successfully fetched", item_type, source)
        logger.debug("Git clone cached to %s", save_dir)
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
        logger.debug("Using cached %s %s", item_type, cached_source_path)
        content_type = MimeTypes().guess_type(cached_source_path)[0]
    for dep in deps:
        output_path = dep["output_path"]
        if dep.get("unpack", False):
            # ensure that the directory we are extracting to exists
            os.makedirs(output_path, exist_ok=True)
            if force:
                is_unpacked = unpack_downloaded_file(cached_source_path, output_path, content_type)
            else:
                unpack_output = os.path.join(
                    save_dir, "extracted-" + str(multiprocessing.current_process().name)
                )
                os.makedirs(unpack_output)
                is_unpacked = unpack_downloaded_file(cached_source_path, unpack_output, content_type)
                safe_copy_tree(unpack_output, output_path)
                # delete unpack output
                rmtree(unpack_output)
            if is_unpacked:
                logger.info("%s %s: extracted to %s", item_type, source, output_path)
            else:
                logger.info(
                    "%s %s: Content-Type %s is not supported for unpack. Ignoring save",
                    item_type,
                    source,
                    content_type,
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
            logger.info("%s %s: saved to %s", item_type, source, output_path)


def fetch_http_source(source, save_path, item_type):
    """downloads a http[s] file from source and saves into save_path(which is a file)"""

    if os.path.exists(save_path):
        os.remove(save_path)
        logger.debug("Removed %s", save_path)
    logger.info("%s %s: fetching now", item_type, source)
    content, content_type = make_request(source)
    logger.info("%s %s: successfully fetched", item_type, source)
    if content is not None:
        with open(save_path, "wb") as f:
            f.write(content)
        logger.debug("Cached to %s", save_path)
        return content_type
    logger.warning("%s %s: failed to fetch", item_type, source)
    return None


def fetch_helm_chart(dep_mapping, save_dir, force):
    """
    downloads a helm chart and its subcharts from source then untars and moves it to save_dir
    """
    source, deps = dep_mapping

    # to avoid collisions between source.chart_name/source.version
    path_hash = hashlib.sha256(source.repo.encode()).hexdigest()[:8]
    cached_repo_path = os.path.join(
        save_dir, path_hash, source.chart_name + "-" + (source.version or "latest")
    )
    if force or not exists_in_cache(cached_repo_path):
        fetch_helm_archive(source.helm_path, source.repo, source.chart_name, source.version, cached_repo_path)
    else:
        logger.debug("Using cached helm chart at %s", cached_repo_path)

    for dep in deps:
        output_path = dep["output_path"]

        parent_dir = os.path.dirname(output_path)
        if parent_dir != "":
            os.makedirs(parent_dir, exist_ok=True)
        if force:
            copy_tree(cached_repo_path, output_path)
        else:
            safe_copy_tree(cached_repo_path, output_path)
        logger.info("Dependency %s: saved to %s", source.chart_name, output_path)


def fetch_helm_archive(helm_path, repo, chart_name, version, save_path):
    logger.info("Dependency helm chart %s and version %s: fetching now", chart_name, version or "latest")
    # Fetch archive and untar it into parent dir
    save_dir = os.path.dirname(save_path)
    args = ["pull", "--destination", save_dir, "--untar"]

    if version:
        args.append("--version")
        args.append(version)

    if repo.startswith("oci://"):
        args.append(repo)
    else:
        args.append("--repo")
        args.append(repo)
        args.append(chart_name)

    response = helm_cli(helm_path, args)
    if response != "":
        logger.warning("Dependency helm chart %s and version %s: %s", chart_name, version, response)
        raise HelmFetchingError(response)
    else:
        # rename chart to requested name
        os.rename(os.path.join(save_dir, chart_name), save_path)
        logger.info("Dependency helm chart %s and version %s: successfully fetched", chart_name, version)
        logger.info("Dependency helm chart %s and version %s: saved to %s", chart_name, version, save_path)


def exists_in_cache(item_path):
    dep_cache_path = os.path.dirname(item_path)
    if not os.path.exists(dep_cache_path):
        return False
    return os.path.basename(item_path) in os.listdir(dep_cache_path)
