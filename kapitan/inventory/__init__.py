from kapitan.errors import MissingOptionalDependencyError
from kapitan.utils import StrEnum

from .inventory import Inventory, InventoryError, InventoryTarget


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
    from .backends.reclass import ReclassInventory

    return ReclassInventory


def load_reclass_rs_backend():
    """
    Enable the reclass-rs inventory backend.
    """
    try:
        from .backends.reclass_rs import ReclassRsInventory
    except ImportError as exc:
        raise MissingOptionalDependencyError(
            "reclass-rs inventory backend", "reclass-rs"
        ) from exc

    return ReclassRsInventory


def load_omegaconf_backend():
    """
    Enable the omegaconf inventory backend.
    """
    try:
        from .backends.omegaconf import OmegaConfInventory
    except ImportError as exc:
        raise MissingOptionalDependencyError(
            "omegaconf inventory backend", "omegaconf"
        ) from exc

    return OmegaConfInventory


# Dict mapping values for command line flag `--inventory-backend` to the
# associated `Inventory` subclass.
AVAILABLE_BACKENDS: dict[str, type[Inventory]] = {
    InventoryBackends.RECLASS: load_reclass_backend,
    InventoryBackends.RECLASS_RS: load_reclass_rs_backend,
    InventoryBackends.OMEGACONF: load_omegaconf_backend,
}


def get_inventory_backend(backend_name: str) -> type[Inventory]:
    """
    Get the `Inventory` subclass associated with the given `backend_name`.
    """
    return AVAILABLE_BACKENDS.get(
        backend_name, AVAILABLE_BACKENDS[InventoryBackends.DEFAULT]
    )()
