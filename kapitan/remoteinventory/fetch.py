import hashlib
import logging
import os
from collections import defaultdict
from functools import partial

from kapitan import cached
from kapitan.dependency_manager.base import fetch_git_dependency, fetch_http_dependency
from kapitan.utils import normalise_join_path

logger = logging.getLogger(__name__)


def fetch_inventories(inventory_path, target_objs, save_dir, force, pool):
    """Parses through the 'inventory' parameter in target_objs to fetch the remote
    inventories and stores it in save_dir before recursively
    copying it to the output_path (relative to the inventory path)
    Overwrites existing inventory items if force fetched

    :param inventory_path: default or user specified inventory path
    :param target_objs: target objects
    :param save_dir: directory to save the fetched items
    :param force: bool value
    :param pool: pool object for multiprocessing
    :return: None
    """
    git_inventories = defaultdict(list)
    http_inventories = defaultdict(list)
    # To ensure no duplicate output path
    inv_output_path = defaultdict(set)

    for target_obj in target_objs:
        try:
            inventories = target_obj["inventory"]
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
                    source_hash.update(ref.encode())
                if source_hash in cached.inv_sources:
                    continue
                # output_path is relative to inventory_path
                # ./inventory by default
                output_path = normalise_join_path(inventory_path, inv["output_path"])
                logger.debug("Updated output_path from %s to %s", inv["output_path"], output_path)
                inv["output_path"] = output_path

                if output_path in inv_output_path[source_uri]:
                    # if the output_path is duplicated for the same source_uri
                    logger.warning("Skipping duplicate output path for uri %s", source_uri)
                    continue
                else:
                    inv_output_path[source_uri].add(output_path)

                if inv_type == "git":
                    git_inventories[source_uri].append(inv)
                elif inv_type in ("http", "https"):
                    http_inventories[source_uri].append(inv)
                else:
                    logger.warning("%s is not a valid source type", inv_type)
        except KeyError:
            logger.debug("Target object %s has no inventory key", target_obj["vars"]["target"])
            continue

    git_worker = partial(fetch_git_dependency, save_dir=save_dir, force=force, item_type="Inventory")
    http_worker = partial(fetch_http_dependency, save_dir=save_dir, force=force, item_type="Inventory")
    [p.get() for p in pool.imap_unordered(git_worker, git_inventories.items()) if p]
    [p.get() for p in pool.imap_unordered(http_worker, http_inventories.items()) if p]


def list_sources(target_objs):
    "returns list of all remote inventory sources"
    sources = []
    for target_obj in target_objs:
        try:
            invs = target_obj["inventory"]
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
                "Listing sources: target object %s has no 'inventory' key, continuing",
                target_obj["vars"]["target"],
            )
            continue
    return sources
