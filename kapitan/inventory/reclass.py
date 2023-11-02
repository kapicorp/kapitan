from kapitan.inventory.base import Inventory
import os
import yaml
import logging

import reclass
import reclass.core
from reclass.errors import NotFoundError, ReclassException

from kapitan.errors import InventoryError

logger = logging.getLogger(__name__)

class ReclassInventory(Inventory):
    
    def get_parameters(self, ignore_class_notfound=False) -> dict:
        """
        Runs a reclass inventory in inventory_path
        (same output as running ./reclass.py -b inv_base_uri/ --inventory)
        Will attempt to read reclass config from 'reclass-config.yml' otherwise
        it will failback to the default config.
        Returns a reclass style dictionary

        Does not throw errors if a class is not found while --fetch flag is enabled
        """
        reclass_config = self.get_config()
        reclass_config.setdefault("ignore_class_notfound", ignore_class_notfound)
        
        try:
            storage = reclass.get_storage(
                reclass_config["storage_type"],
                reclass_config["nodes_uri"],
                reclass_config["classes_uri"],
                reclass_config["compose_node_name"],
            )
            class_mappings = reclass_config.get("class_mappings")  # this defaults to None (disabled)
            _reclass = reclass.core.Core(storage, class_mappings, reclass.settings.Settings(reclass_config))

            return _reclass.inventory()
        except ReclassException as e:
            if isinstance(e, NotFoundError):
                logger.error("Inventory reclass error: inventory not found")
            else:
                logger.error(f"Inventory reclass error: {e.message}")
            raise InventoryError(e.message)
        
        
    def get_config(self) -> dict:
        # set default values initially
        reclass_config = {
            "storage_type": "yaml_fs",
            "inventory_base_uri": self.inventory_path,
            "nodes_uri": "targets",
            "classes_uri": "classes",
            "compose_node_name": False,
            "allow_none_override": True,
        }
        try:
            from yaml import CSafeLoader as YamlLoader
        except ImportError:
            from yaml import SafeLoader as YamlLoader
        
        # get reclass config from file 'inventory/reclass-config.yml'
        cfg_file = os.path.join(self.inventory_path, "reclass-config.yml")
        if os.path.isfile(cfg_file):
            with open(cfg_file, "r") as fp:
                config = yaml.load(fp.read(), Loader=YamlLoader)
                logger.debug("Using reclass inventory config at: {}".format(cfg_file))
            if config:
                # set attributes, take default values if not present
                for key, value in config.items():
                    reclass_config[key] = value
            else:
                logger.debug("{}: Empty config file. Using reclass inventory config defaults".format(cfg_file))
        else:
            logger.debug("Inventory reclass: No config file found. Using reclass inventory config defaults")
            
        # normalise relative nodes_uri and classes_uri paths
        for uri in ("nodes_uri", "classes_uri"):
            reclass_config[uri] = os.path.normpath(os.path.join(self.inventory_path, reclass_config[uri]))
            
        return reclass_config