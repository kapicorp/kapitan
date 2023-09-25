# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"environment refs module"

import os

from kapitan.errors import KapitanError
from kapitan.refs.base64 import Base64Ref, Base64RefBackend

DEFAULT_ENV_REF_VAR_PREFIX = "KAPITAN_ENV_"


class EnvError(KapitanError):
    """Generic Env errors"""

    pass


class EnvRef(Base64Ref):
    def __init__(self, data, **kwargs):
        """
        looks up KAPITAN_ENV_* when revealing
        """
        super().__init__(data, from_base64=True, **kwargs)
        self.type_name = "env"

    def reveal(self):
        """
        Attempt to locate the variable in the environment w/ the suffix.
        """
        env_var_key = self.path
        env_var = f"{DEFAULT_ENV_REF_VAR_PREFIX}{env_var_key}"
        value = os.getenv(env_var, default=os.getenv(env_var.upper()))
        if value is None:
            raise EnvError(f"env: variable {env_var} is not defined")
        return value

    def compile(self):
        return f"?{{env:{self.path}}}"

    @classmethod
    def from_path(cls, ref_full_path, **kwargs):
        return cls(ref_full_path, **kwargs)


class EnvRefBackend(Base64RefBackend):
    def __init__(self, path, ref_type=EnvRef, **ref_kwargs):
        "Get and create EnvRefs"
        super().__init__(path, ref_type, ref_kwargs=ref_kwargs)
        self.type_name = "env"
