# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Type

from kapitan.inventory.model.input_types import InputTypes

from .base import InputType
from .copy import Copy
from .external import External
from .helm import Helm
from .jinja2 import Jinja2
from .jsonnet import Jsonnet
from .kadet import Kadet
from .remove import Remove

# Dict mapping values for command line flag `--inventory-backend` to the
# associated `Inventory` subclass.
AVAILABLE_INPUT_TYPES: dict[str, Type[InputType]] = {
    InputTypes.JINJA2: Jinja2,
    InputTypes.HELM: Helm,
    InputTypes.JSONNET: Jsonnet,
    InputTypes.KADET: Kadet,
    InputTypes.COPY: Copy,
    InputTypes.EXTERNAL: External,
    InputTypes.REMOVE: Remove,
}


def get_compiler(input_type: InputType) -> Type[InputType]:
    """
    Get the `Inventory` subclass associated with the given `backend_name`.
    """
    return AVAILABLE_INPUT_TYPES.get(input_type)
