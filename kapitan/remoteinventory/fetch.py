import os
import tempfile
import logging
from collections import defaultdict
from distutils.dir_util import copy_tree
from functools import partial
from shutil import copyfile, rmtree
from git import Repo

from git import GitCommandError
from kapitan.errors import GitSubdirNotFoundError
from kapitan.errors import GitFetchingError

logger = logging.getLogger(__name__)


def fetch_inventories(inventory_path, target_objs, pool):
    """Parses through the 'inventory' parameter in target_objs to fetch the remote
       inventories and stores it in a temporary directory before recursively
       copying it to the output_path (relative to the inventory path)

       :param inventory_path: default or user specified inventory path
       :param target_objs: target objects
       :param pool: pool object for multiprocessing

       :return: None
    """
    temp_dir = tempfile.mkdtemp()

    git_inventories = defaultdict(list)
    inv_output_path = defaultdict(set)

    for target_obj in target_objs:
        try:
            inventories = target_obj["inventories"]
            for inv in inventories:
                inv_type = inv["type"]
                source_uri = inv["source"]
                # output_path is relative to inventory_path
                # ./inventory by default
                output_path = os.path.join(inventory_path, inv["output_path"])
                if output_path in inv_output_path[source_uri]:
                    continue
                else:
                    inv_output_path[source_uri].add(output_path)
                if inv_type == "git":
                    git_inventories[source_uri].append(inv)
        except KeyError:
            continue

    git_worker = partial(fetch_git_inventories, inventory_path=inventory_path, save_dir=temp_dir)
    [p.get() for p in pool.imap_unordered(git_worker, git_inventories.items()) if p]

    rmtree(temp_dir)
    logger.debug("Removed {}".format(temp_dir))


def fetch_git_inventories(inv_mapping, inventory_path, save_dir):
    """ Fetches remote inventories of git type as declared in target_objs
        and recursively copies it to the output_path

        :param inv_mapping: tupple containing source and list of invetory variables
        :param inventory_path: default or user defined inventory path
        :param save_dir: directory to same the fetched inventory items into

        :returns: None
    """
    source, inventories = inv_mapping
    fetch_git_source(source, save_dir)
    for inv in inventories:
        repo_path = os.path.join(save_dir, os.path.basename(source))
        repo = Repo(repo_path)
        output_path = os.path.join(inventory_path, inv["output_path"])
        copy_src_path = repo_path

        if "ref" in inv:
            ref = inv["ref"]
            repo.git.checkout(ref)
        else:
            repo.git.checkout("master")

        if "subdir" in inv:
            sub_dir = inv["subdir"]
            full_subdir = os.path.join(repo_path, sub_dir)
            if os.path.isdir(full_subdir):
                copy_src_path = full_subdir
            else:
                raise GitSubdirNotFoundError(
                    "Inventory {} : subdir {} not found in repo".format(source, sub_dir)
                )
        # Recursively copy the fetched inventory files (src) to the output path (dst)
        # if those items doen't exist or if it's older than src
        copy_tree(copy_src_path, output_path, update=True)
        logger.info("Inventory {} : saves to {}".format(source, output_path))


def fetch_git_source(source, save_dir):
    """Clones a git repo at source and stores it at save_dir"""
    logger.info("Inventory {} : fetching now".format(source))
    try:
        Repo.clone_from(source, os.path.join(save_dir, os.path.basename(source)))
        logger.info("Inventory {} : successfully fetched".format(source))
    except GitCommandError as e:
        logger.error(e)
        raise GitFetchingError("Inventory {} : fetching unsuccessful{}".format(source, e.stderr))


def list_sources(target_objs):
    "returns list of all remote inventory sources"
    sources = []
    for target_obj in target_objs:
        try:
            invs = target_obj["inventories"]
            for inv in invs:
                source_uri = inv["source"]
                sources.append(source_uri)
        except KeyError:
            continue
    return sources
