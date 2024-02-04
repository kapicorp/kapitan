from typing import Type

from .inv_reclass import ReclassInventory
from .inventory import Inventory

# Dict mapping values for command line flag `--inventory-backend` to the
# associated `Inventory` subclass.
AVAILABLE_BACKENDS: dict[str, Type[Inventory]] = {
    "reclass": ReclassInventory,
}
