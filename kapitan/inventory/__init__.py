from typing import Type

from .inv_reclass import ReclassInventory
from .inv_reclass_rs import ReclassRsInventory
from .inv_omegaconf.inv_omegaconf import OmegaConfInventory
from .inventory import Inventory

# Dict mapping values for command line flag `--inventory-backend` to the
# associated `Inventory` subclass.
AVAILABLE_BACKENDS: dict[str, Type[Inventory]] = {
    "reclass": ReclassInventory,
    "reclass-rs": ReclassRsInventory,
    "omegaconf": OmegaConfInventory,
}
