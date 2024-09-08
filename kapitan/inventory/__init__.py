from typing import Type

from kapitan.utils import StrEnum

from .inventory import Inventory


class InventoryBackends(StrEnum):
    """
    Enumeration of available inventory backends.
    """

    RECLASS = "reclass"
    RECLASS_RS = "reclass-rs"
    OMEGACONF = "omegaconf"
    DEFAULT = RECLASS


def load_reclass_backend():
    """
    Enable the reclass inventory backend.
    """
    from .inv_reclass import ReclassInventory

    return ReclassInventory


def load_reclass_rs_backend():
    """
    Enable the reclass-rs inventory backend.
    """
    from .inv_reclass_rs import ReclassRsInventory

    return ReclassRsInventory


def load_omegaconf_backend():
    """
    Enable the omegaconf inventory backend.
    """
    from .inv_omegaconf.inv_omegaconf import OmegaConfInventory

    return OmegaConfInventory


# Dict mapping values for command line flag `--inventory-backend` to the
# associated `Inventory` subclass.
AVAILABLE_BACKENDS: dict[str, Type[Inventory]] = {
    InventoryBackends.RECLASS: load_reclass_backend,
    InventoryBackends.RECLASS_RS: load_reclass_rs_backend,
    InventoryBackends.OMEGACONF: load_omegaconf_backend,
}


def get_inventory_backend(backend_name: str) -> Type[Inventory]:
    """
    Get the `Inventory` subclass associated with the given `backend_name`.
    """
    return AVAILABLE_BACKENDS.get(backend_name, AVAILABLE_BACKENDS[InventoryBackends.DEFAULT])()
