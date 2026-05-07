# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import hashlib
import logging
import multiprocessing
import os
import sys
import tarfile
from collections import defaultdict, namedtuple
from functools import partial
from mimetypes import MimeTypes
from pathlib import Path
from shutil import copyfile, rmtree


try:
    import oras.client
except ImportError:
    oras = None

from git import GitCommandError, Repo

from kapitan.errors import (
    GitFetchingError,
    GitSubdirNotFoundError,
    HelmFetchingError,
    OCIFetchingError,
)
from kapitan.helm_cli import helm_cli
from kapitan.inventory.model.dependencies import KapitanDependencyTypes
from kapitan.utils import (
    copy_tree,
    make_request,
    normalise_join_path,
    safe_copy_file,
    safe_copy_tree,
    unpack_downloaded_file,
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
    oci_deps = defaultdict(list)

    # this dict is to make sure no duplicated output_paths exist per source
    deps_output_paths = defaultdict(set)
    for target_obj in target_objs:
        try:
            dependencies = target_obj.dependencies
            for item in dependencies:
                dependency_type = item.type
                source_uri = item.source

                # The target key "output_path" is relative to the compile output path set by the user
                # point to the full output path
                full_output_path = normalise_join_path(output_path, item.output_path)
                logger.debug(
                    "Updated output_path from %s to %s", item.output_path, output_path
                )
                item.output_path = full_output_path

                if full_output_path in deps_output_paths[source_uri]:
                    # if the output_path is duplicated for the same source_uri
                    logger.debug(
                        "Skipping duplicate output path for uri %s", source_uri
                    )
                    continue
                deps_output_paths[source_uri].add(full_output_path)

                if dependency_type == KapitanDependencyTypes.GIT:
                    git_deps[source_uri].append(item)
                elif dependency_type in (
                    KapitanDependencyTypes.HTTP,
                    KapitanDependencyTypes.HTTPS,
                ):
                    http_deps[source_uri].append(item)
                elif dependency_type == KapitanDependencyTypes.HELM:
                    version = item.version
                    helm_deps[
                        HelmSource(source_uri, item.chart_name, version, item.helm_path)
                    ].append(item)
                elif dependency_type == KapitanDependencyTypes.OCI:
                    oci_deps[source_uri].append(item)
                else:
                    logger.warning("%s is not a valid source type", dependency_type)

        except KeyError:
            logger.debug(
                "Target object %s has no 'dependencies' key, continuing",
                target_obj["vars"]["target"],
            )
            continue

    git_worker = partial(fetch_git_dependency, save_dir=save_dir, force=force)
    http_worker = partial(fetch_http_dependency, save_dir=save_dir, force=force)
    helm_worker = partial(fetch_helm_chart, save_dir=save_dir, force=force)
    oci_worker = partial(fetch_oci_dependency, save_dir=save_dir, force=force)
    [p.get() for p in pool.imap_unordered(http_worker, http_deps.items()) if p]
    [p.get() for p in pool.imap_unordered(git_worker, git_deps.items()) if p]
    [p.get() for p in pool.imap_unordered(helm_worker, helm_deps.items()) if p]
    [p.get() for p in pool.imap_unordered(oci_worker, oci_deps.items()) if p]


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

    # Resolve the default branch once so that dep.ref=None always means the
    # original HEAD, not whatever a prior dep checkout left the repo at.
    init_repo = Repo(cached_repo_path)
    try:
        default_branch = init_repo.active_branch.name
    except TypeError:
        # Detached HEAD (e.g. left from a prior forced fetch); try symbolic remote HEAD.
        try:
            default_branch = init_repo.git.symbolic_ref(
                "refs/remotes/origin/HEAD"
            ).split("/")[-1]
        except Exception:
            default_branch = None

    for dep in deps:
        repo = Repo(cached_repo_path)
        output_path = dep.output_path
        copy_src_path = cached_repo_path
        ref = dep.ref if dep.ref is not None else default_branch
        if ref is not None:
            repo.git.checkout(ref)

        # initialising submodules
        if dep.submodules:
            for submodule in repo.submodules:
                submodule.update(init=True)

        if dep.subdir:
            sub_dir = dep.subdir
            full_subdir = os.path.join(cached_repo_path, sub_dir)
            if os.path.isdir(full_subdir):
                copy_src_path = full_subdir
            else:
                raise GitSubdirNotFoundError(
                    f"{item_type} {source}: subdir {sub_dir} not found in repo"
                )
        if force:
            # We need `clobber_files=True` here, since we otherwise can't overwrite read-only Git
            # index and pack files if the destination already contains a copy of the Git repo.
            copied = copy_tree(copy_src_path, output_path, clobber_files=True)
        else:
            copied = safe_copy_tree(copy_src_path, output_path)
        if copied:
            logger.info("%s %s: saved to %s", item_type, source, output_path)


def fetch_git_source(source, save_dir, item_type):
    """clones a git repository at source and saves into save_dir"""

    if os.path.exists(save_dir):
        rmtree(save_dir)
        logger.debug("Removed %s", save_dir)
    logger.debug("%s %s: fetching now", item_type, source)
    try:
        Repo.clone_from(source, save_dir)
        logger.debug("%s %s: successfully fetched", item_type, source)
        logger.debug("Git clone cached to %s", save_dir)
    except GitCommandError as e:
        logger.error(e)
        raise GitFetchingError(
            f"{item_type} {source}: fetching unsuccessful\n{e.stderr}"
        )


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
        output_path = dep.output_path
        if dep.unpack:
            # ensure that the directory we are extracting to exists
            os.makedirs(output_path, exist_ok=True)
            if force:
                is_unpacked = unpack_downloaded_file(
                    cached_source_path, output_path, content_type
                )
            else:
                unpack_output = os.path.join(
                    save_dir, "extracted-" + str(multiprocessing.current_process().name)
                )
                os.makedirs(unpack_output)
                is_unpacked = unpack_downloaded_file(
                    cached_source_path, unpack_output, content_type
                )
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
            logger.debug("%s %s: saved to %s", item_type, source, output_path)


def fetch_http_source(source, save_path, item_type):
    """downloads a http[s] file from source and saves into save_path(which is a file)"""

    if os.path.exists(save_path):
        os.remove(save_path)
        logger.debug("Removed %s", save_path)
    logger.debug("%s %s: fetching now", item_type, source)
    content, content_type = make_request(source)
    logger.debug("%s %s: successfully fetched", item_type, source)
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

    for dep in deps:
        output_path = dep.output_path

        if not os.path.exists(output_path) or force:
            if not exists_in_cache(cached_repo_path):
                fetch_helm_archive(
                    source.helm_path,
                    source.repo,
                    source.chart_name,
                    source.version,
                    cached_repo_path,
                )
            else:
                logger.debug("Using cached helm chart at %s", cached_repo_path)

            parent_dir = os.path.dirname(output_path)
            if parent_dir != "":
                os.makedirs(parent_dir, exist_ok=True)

            if force:
                copied = copy_tree(cached_repo_path, output_path)
            else:
                copied = safe_copy_tree(cached_repo_path, output_path)

            if copied:
                logger.info(
                    "Dependency %s: saved to %s", source.chart_name, output_path
                )


def fetch_helm_archive(helm_path, repo, chart_name, version, save_path):
    logger.debug(
        "Dependency helm chart %s and version %s: fetching now",
        chart_name,
        version or "latest",
    )
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
        logger.warning(
            "Dependency helm chart %s and version %s: %s", chart_name, version, response
        )
        raise HelmFetchingError(response)
    # rename chart to requested name
    os.rename(os.path.join(save_dir, chart_name), save_path)
    logger.debug(
        "Dependency helm chart %s and version %s: successfully fetched",
        chart_name,
        version,
    )
    logger.debug(
        "Dependency helm chart %s and version %s: saved to %s",
        chart_name,
        version,
        save_path,
    )


def exists_in_cache(item_path):
    dep_cache_path = os.path.dirname(item_path)
    if not os.path.exists(dep_cache_path):
        return False
    return os.path.basename(item_path) in os.listdir(dep_cache_path)


def _extract_tar_blobs(target_dir: str) -> None:
    """Walk target_dir and extract any tar archive files found there.

    oras-py saves each OCI layer as a raw blob file, preserving the layer's
    manifest title as its on-disk path (e.g. ``system/generators/mygenerator``).
    When the layer is a tar+gzip archive the saved file IS the tarball rather
    than its extracted contents. This helper detects those blobs and extracts
    them so that the directory tree matches what was originally pushed.
    """
    blobs = []
    for dirpath, _dirs, filenames in os.walk(target_dir):
        for fname in filenames:
            candidate = os.path.join(dirpath, fname)
            try:
                if tarfile.is_tarfile(candidate):
                    blobs.append(candidate)
            except Exception:
                logger.debug("Skipping %s: not a readable tar archive", candidate)

    for blob_path in blobs:
        logger.debug("Extracting OCI tar blob %s into %s", blob_path, target_dir)
        with tarfile.open(blob_path, "r:*") as tar:
            os.unlink(blob_path)
            if sys.version_info >= (3, 12):
                tar.extractall(target_dir, filter="data")
            else:
                tar.extractall(target_dir)


def fetch_oci_dependency(dep_mapping, save_dir, force=False, item_type="Dependency"):
    """
    Pulls an OCI artifact from a registry into save_dir, then copies it (or a declared subpath
    within it) into each dependency's output_path. The artifact is cached by source reference so
    multiple dependencies sharing the same source trigger only one pull. Connection settings
    (insecure, tls_verify) must be identical across all deps for the same source; media_type
    filters are unioned so a single pull retrieves all required layers.
    """
    if oras is None:
        raise ImportError(
            "The 'oras' package is required for OCI dependencies. "
            "Install it with: pip install kapitan[oci]"
        )

    source, deps = dep_mapping

    # Derive a stable local cache directory from the full source reference,
    # including any digest, so tag@sha256:… and tag alone cache separately.
    cache_key = hashlib.sha256(source.encode()).hexdigest()[:8]
    target_dir = os.path.join(save_dir, f"oci_{cache_key}")

    if not exists_in_cache(target_dir) or force:
        if force and os.path.exists(target_dir):
            rmtree(target_dir)
            logger.debug("Removed cached %s %s", item_type, target_dir)
        logger.debug("%s %s: fetching now", item_type, source)
        first = deps[0]
        if len(deps) > 1 and any(
            dep.insecure != first.insecure or dep.tls_verify != first.tls_verify
            for dep in deps[1:]
        ):
            raise OCIFetchingError(
                f"{item_type} {source}: multiple dependencies share the same source but "
                f"declare conflicting connection settings. All dependencies for "
                f"the same source must use identical insecure and tls_verify settings."
            )
        # Union media_type filters: if any dep requests everything (None), pull all layers;
        # otherwise collect the distinct types so each dep gets the layers it needs.
        if any(dep.media_type is None for dep in deps):
            allowed_media_type = None
        else:
            allowed_media_type = list({dep.media_type for dep in deps})
        try:
            client = oras.client.OrasClient(
                insecure=first.insecure, tls_verify=first.tls_verify
            )
            username = os.environ.get("OCI_USERNAME")
            password = os.environ.get("OCI_PASSWORD")
            if username and password:
                client.auth.set_basic_auth(username, password)
            client.pull(
                target=source,
                outdir=target_dir,
                allowed_media_type=allowed_media_type,
            )
            logger.debug("%s %s: successfully fetched", item_type, source)
            # Log the top-level entries in the pulled artifact so users can
            # identify the correct 'subpath' when the artifact has nested dirs.
            top_entries = sorted(p.name for p in Path(target_dir).iterdir())
            if top_entries:
                logger.info(
                    "%s %s: artifact root contains: [%s]. "
                    "Set 'subpath' in the dependency if content is nested.",
                    item_type,
                    source,
                    ", ".join(top_entries),
                )
        except Exception as e:
            raise OCIFetchingError(
                f"{item_type} {source}: fetching unsuccessful\n{e}"
            ) from e
    else:
        logger.debug("Using cached %s %s", item_type, target_dir)

    # Extract tar blobs every time — idempotent (no blobs = no-op) and handles
    # caches populated by older kapitan versions before blob extraction was added.
    try:
        _extract_tar_blobs(target_dir)
    except Exception as e:
        raise OCIFetchingError(
            f"{item_type} {source}: failed to extract tar blobs from pulled artifact\n{e}"
        ) from e

    for dep in deps:
        # Copy either the full artifact or only the declared subdirectory.
        # NOTE: subpath validation happens after the pull because we don't inspect the
        # manifest before fetching. A typo in subpath wastes a pull but avoids the
        # complexity of a pre-pull manifest walk.
        src = os.path.join(target_dir, dep.subpath) if dep.subpath else target_dir
        if dep.subpath:
            # Guard against path traversal (e.g. subpath="../../etc/passwd").
            real_target = os.path.realpath(target_dir)
            real_src = os.path.realpath(src)
            if (
                not real_src.startswith(real_target + os.sep)
                and real_src != real_target
            ):
                raise OCIFetchingError(
                    f"{item_type} {source}: subpath '{dep.subpath}' resolves outside "
                    f"the artifact directory"
                )
            if not os.path.isdir(src):
                raise OCIFetchingError(
                    f"{item_type} {source}: subpath '{dep.subpath}' not found in pulled artifact"
                )
        if force:
            copied = copy_tree(src, dep.output_path)
        else:
            copied = safe_copy_tree(src, dep.output_path)
        if copied:
            logger.info("%s %s: saved to %s", item_type, source, dep.output_path)

        # Warn when output_path has only subdirectories (no files) and no subpath
        # was configured. This is the classic symptom of an oras artifact pushed
        # from a parent directory: oras preserves push-time paths, so all content
        # lands one or more levels deep instead of directly under output_path.
        if not dep.subpath and os.path.isdir(dep.output_path):
            children = [
                p for p in Path(dep.output_path).iterdir() if not p.name.startswith(".")
            ]
            has_files = any(p.is_file() for p in children)
            only_dirs = [p for p in children if p.is_dir()]
            if only_dirs and not has_files:
                logger.warning(
                    "%s %s: output_path '%s' contains only subdirectories: [%s]. "
                    "The artifact may have been pushed with nested paths — set 'subpath' "
                    "to the directory that contains your content "
                    "(e.g. subpath: %s).",
                    item_type,
                    source,
                    dep.output_path,
                    ", ".join(sorted(p.name for p in only_dirs)),
                    sorted(p.name for p in only_dirs)[0],
                )
