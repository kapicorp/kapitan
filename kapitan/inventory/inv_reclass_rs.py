import logging
from datetime import datetime

import reclass_rs

from kapitan.errors import InventoryError

from .inv_reclass import get_reclass_config
from .inventory import Inventory, InventoryTarget

logger = logging.getLogger(__name__)


class ReclassRsInventory(Inventory):
    def _make_reclass_rs(self, ignore_class_not_found: bool):
        # Get Reclass config options with the same method that's used for `ReclassInventory`, but
        # disable the logic to normalise the `nodes_uri` and `classes_uri` options, since reclass-rs
        # expects those fields to be relative to the inventory path.
        config_dict = get_reclass_config(
            self.inventory_path, ignore_class_not_found, self.compose_target_name, False
        )

        # Turn on verbose config loading only if Kapitan loglevel is set to at least DEBUG.
        config = reclass_rs.Config.from_dict(
            self.inventory_path, config_dict, logger.isEnabledFor(logging.DEBUG)
        )
        return reclass_rs.Reclass.from_config(config)

    def render_targets(self, targets: list = None, ignore_class_not_found: bool = False):
        try:
            r = self._make_reclass_rs(ignore_class_not_found)
            start = datetime.now()
            inv = r.inventory()
            elapsed = datetime.now() - start
            logger.debug(f"Inventory rendering with reclass-rs took {elapsed}")

            for target_name, nodeinfo in inv.nodes.items():
                self.targets[target_name].parameters = nodeinfo.parameters
                self.targets[target_name].classes = nodeinfo.classes
                self.targets[target_name].applications = nodeinfo.applications
                self.targets[target_name].exports = nodeinfo.exports

        except ValueError as e:
            logger.error(f"Reclass-rs error: {e}")
            raise InventoryError(f"{e}")
