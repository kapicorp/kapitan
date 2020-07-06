import os
import logging
from collections import defaultdict
from functools import partial
import hashlib

from kapitan import cached
from kapitan.dependency_manager.base import fetch_git_dependency, fetch_http_dependency

logger = logging.getLogger(__name__)


def fetch_inventories(inventory_path, target_objs, temp_dir, pool):
    """Parses through the 'inventory' parameter in target_objs to fetch the remote
       inventories and stores it in a temporary directory before recursively
       copying it to the output_path (relative to the inventory path)

       :param inventory_path: default or user specified inventory path
       :param target_objs: target objects
       :param pool: pool object for multiprocessing

       :return: None
    """

    git_inventories = defaultdict(list)
    http_inventories = defaultdict(list)

    # To ensure no duplicate output path
    inv_output_path = defaultdict(set)

    for target_obj in target_objs:
        try:
            inventories = target_obj["inventories"]
            for inv in inventories:
                inv_type = inv["type"]
                source_uri = inv["source"]
                source_hash = hashlib.sha256(source_uri.encode())
                # hashing the source, subdir and ref together for git sources
                # as different inventory items can have the same git uri
                if "subdir" in inv:
                    subdir = inv["subdir"]
                    source_hash.update(subdir.encode())
                if "ref" in inv:
                    ref = inv["ref"]
                    source_hash = hashlib.sha256(ref.encode())
                if source_hash in cached.inv_sources:
                    continue
                # output_path is relative to inventory_path
                # ./inventory by default
                output_path = os.path.join(inventory_path, inv["output_path"])
                logger.debug("Updated output_path from {} to {}".format(inv["output_path"], output_path))
                inv["output_path"] = output_path

                if output_path in inv_output_path[source_uri]:
                    # if the output_path is duplicated for the same source_uri
                    logger.warning("skipping duplicate output path for uri {}".format(source_uri))
                    continue
                else:
                    inv_output_path[source_uri].add(output_path)

                if inv_type == "git":
                    git_inventories[source_uri].append(inv)
                elif inv_type in ("http", "https"):
                    http_inventories[source_uri].append(inv)
        except KeyError:
            logger.debug("Target object {} has no inventory key".format(target_obj["vars"]["target"]))
            continue

    git_worker = partial(fetch_git_dependency, save_dir=temp_dir, item_type="inventory")
    http_worker = partial(fetch_http_dependency, save_dir=temp_dir, item_type="inventory")
    [p.get() for p in pool.imap_unordered(git_worker, git_inventories.items()) if p]
    [p.get() for p in pool.imap_unordered(http_worker, http_inventories.items()) if p]


def list_sources(target_objs):
    "returns list of all remote inventory sources"
    sources = []
    for target_obj in target_objs:
        try:
            invs = target_obj["inventories"]
            for inv in invs:
                source_uri = inv["source"]
                source_hash = hashlib.sha256(source_uri.encode())
                # hashing the source, subdir, ref together to idenntify unique items
                if "subdir" in inv:
                    subdir = inv["subdir"]
                    source_hash.update(subdir.encode())
                if "ref" in inv:
                    ref = inv["ref"]
                    source_hash.update(ref.encode())

                sources.append(source_hash.hexdigest()[:8])
        except KeyError:
            logger.debug(
                "listing sources: target object {} has no 'inventories' key, continuing".format(
                    target_obj["vars"]["target"]
                )
            )
            continue
    return sources
