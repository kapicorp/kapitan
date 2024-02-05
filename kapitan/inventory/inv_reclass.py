import logging
import os

import reclass
import reclass.core
import yaml
from reclass.errors import NotFoundError, ReclassException

from kapitan.errors import InventoryError

from .inventory import Inventory

logger = logging.getLogger(__name__)


class ReclassInventory(Inventory):

    def __init__(self, inventory_path, compose_target_name=False):
        super().__init__(inventory_path, compose_target_name=compose_target_name)
        
        self.reclass_config = get_reclass_config(inventory_path)

        compose_node_name = self.reclass_config.get("compose_node_name", self.compose_target_name)
        if compose_node_name != self.compose_target_name:
            logger.warning(
                f"reclass-config.yml has compose_node_name={compose_node_name} but kapitan has --compose-node-name={self.compose_target_name}."
            )
            logger.warning(
                f"Using --compose-node-name={self.compose_target_name}: Please update reclass-config.yml to remove this warning."
            )
            compose_node_name = self.compose_target_name

        self.reclass_config.setdefault("ignore_class_notfound", True)

        try:
            storage = reclass.get_storage(
                self.reclass_config["storage_type"],
                self.reclass_config["nodes_uri"],
                self.reclass_config["classes_uri"],
                compose_node_name,
            )
            class_mappings = self.reclass_config.get("class_mappings")  # this defaults to None (disabled)
            _reclass = reclass.core.Core(
                storage, class_mappings, reclass.settings.Settings(self.reclass_config)
            )
            self.rendered_inventory = _reclass.inventory()

        except ReclassException as e:
            if isinstance(e, NotFoundError):
                logger.error("Inventory reclass error: inventory not found")
            else:
                logger.error(f"Inventory reclass error: {e.message}")
            raise InventoryError(e.message)


    def render_targets(
        self,
        targets: list = None,
        ignore_class_notfound: bool = False,
    ):
        """
        Runs a reclass inventory in inventory_path
        (same output as running ./reclass.py -b inv_base_uri/ --inventory)
        Will attempt to read reclass config from 'reclass-config.yml' otherwise
        it will fall back to the default config.
        Returns a reclass style dictionary

        Does not throw errors if a class is not found while ignore_class_notfound is specified
        """
        # store parameters and classes
        for target_name, rendered_target in self.rendered_inventory["nodes"].items():
            self.targets[target_name].parameters = rendered_target["parameters"]
            self.targets[target_name].classes = rendered_target["classes"]


def get_reclass_config(inventory_path: str) -> dict:
    # set default values initially
    reclass_config = {
        "storage_type": "yaml_fs",
        "inventory_base_uri": inventory_path,
        "nodes_uri": "targets",
        "classes_uri": "classes",
        "allow_none_override": True,
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
    for uri in ("nodes_uri", "classes_uri"):
        reclass_config[uri] = os.path.normpath(os.path.join(inventory_path, reclass_config[uri]))

    return reclass_config
