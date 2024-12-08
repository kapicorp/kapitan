# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import functools  # Import functools for caching
import importlib
from typing import Type

from kapitan.inventory.model.input_types import InputTypes

from .base import InputType


@functools.lru_cache(maxsize=None)  # Use lru_cache for caching
def get_compiler(input_type: InputType) -> Type[InputType]:
    """Dynamically imports and returns the compiler class based on input_type."""

    module_map = {
        InputTypes.JINJA2: "jinja2",
        InputTypes.HELM: "helm",
        InputTypes.JSONNET: "jsonnet",
        InputTypes.KADET: "kadet",
        InputTypes.COPY: "copy",
        InputTypes.EXTERNAL: "external",
        InputTypes.REMOVE: "remove",
    }

    module_name = module_map.get(input_type)
    if module_name:
        try:
            module = importlib.import_module(f".{module_name}", package=__name__)
            return getattr(module, module_name.capitalize())  # Capitalize to get class name
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Could not import module or class for {input_type}: {e}") from e
    else:
        return None  # Or raise an appropriate error for unknown input_type
