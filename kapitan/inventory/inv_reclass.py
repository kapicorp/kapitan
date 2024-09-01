import logging
import os
from datetime import datetime

import reclass
import reclass.core
import yaml
from reclass.errors import NotFoundError, ReclassException

from kapitan.errors import InventoryError

from .inventory import Inventory, InventoryTarget

logger = logging.getLogger(__name__)


class ReclassInventory(Inventory):

    def render_targets(
        self, targets: list[InventoryTarget] = None, ignore_class_not_found: bool = False
    ) -> None:
        """
        Runs a reclass inventory in inventory_path
        (same output as running ./reclass.py -b inv_base_uri/ --inventory)
        Will attempt to read reclass config from 'reclass-config.yml' otherwise
        it will fall back to the default config.
        Returns a reclass style dictionary

        Does not throw errors if a class is not found while ignore_class_not_found is specified
        """
        reclass_config = get_reclass_config(
            self.inventory_path, ignore_class_not_found, self.compose_target_name
        )

        try:
            storage = reclass.get_storage(
                reclass_config["storage_type"],
                reclass_config["nodes_uri"],
                reclass_config["classes_uri"],
                reclass_config["compose_node_name"],
            )
            class_mappings = reclass_config.get("class_mappings")  # this defaults to None (disabled)
            _reclass = reclass.core.Core(storage, class_mappings, reclass.settings.Settings(reclass_config))
            start = datetime.now()
            rendered_inventory = _reclass.inventory()
            elapsed = datetime.now() - start
            logger.debug(f"Inventory rendering with reclass took {elapsed}")

            # store parameters and classes
            for target_name, rendered_target in rendered_inventory["nodes"].items():
                self.targets[target_name].parameters = rendered_target["parameters"]
                self.targets[target_name].classes = rendered_target["classes"]
                self.targets[target_name].applications = rendered_target["applications"]
                self.targets[target_name].exports = rendered_target["exports"]

        except ReclassException as e:
            if isinstance(e, NotFoundError):
                logger.error("Inventory reclass error: inventory not found")
            else:
                logger.error(f"Inventory reclass error: {e.message}")
            raise InventoryError(e.message)


def get_reclass_config(
    inventory_path: str,
    ignore_class_not_found: bool = False,
    compose_target_name: bool = False,
    normalise_nodes_classes: bool = True,
) -> dict:
    # set default values initially
    reclass_config = {
        "storage_type": "yaml_fs",
        "inventory_base_uri": inventory_path,
        "nodes_uri": "targets",
        "classes_uri": "classes",
        "compose_node_name": compose_target_name,
        "allow_none_override": True,
        "ignore_class_notfound": ignore_class_not_found,  # reclass has it mispelled
    }
    try:
        from yaml import CSafeLoader as YamlLoader
    except ImportError:
        from yaml import SafeLoader as YamlLoader

    # get reclass config from file 'inventory/reclass-config.yml'
    cfg_file = os.path.join(inventory_path, "reclass-config.yml")
    if os.path.isfile(cfg_file):
        with open(cfg_file, "r") as fp:
            config = yaml.load(fp.read(), Loader=YamlLoader)
            logger.debug(f"Using reclass inventory config at: {cfg_file}")
        if config:
            # set attributes, take default values if not present
            for key, value in config.items():
                reclass_config[key] = value
        else:
            logger.debug(
                f"Reclass config: Empty config file at {cfg_file}. Using reclass inventory config defaults"
            )
    else:
        logger.debug("Inventory reclass: No config file found. Using reclass inventory config defaults")

    # normalise relative nodes_uri and classes_uri paths
    if normalise_nodes_classes:
        for uri in ("nodes_uri", "classes_uri"):
            reclass_config[uri] = os.path.normpath(os.path.join(inventory_path, reclass_config[uri]))

    return reclass_config
