# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"environment refs module"

import base64
import hashlib
import os

from kapitan.refs.base import PlainRef, PlainRefBackend

DEFAULT_ENV_REF_VAR_PREFIX = "KAPITAN_VAR_"


class EnvRef(PlainRef):
    def __init__(self, data, **kwargs):
        """
        writes plain data, which is the "default" value if the ref cannot be located in the KAPITAN_VAR_*
        environment vars prefix during the reveal phase.
        """
        super().__init__(data, kwargs=kwargs)
        self.type_name = "env"

    def reveal(self):
        """
        Attempt to locate the variable in the environment w/ the suffix.
        """
        path_part = self.path.split("/")[-1]
        var_key = "{}{}".format(DEFAULT_ENV_REF_VAR_PREFIX, path_part)
        return os.getenv(var_key, default=os.getenv(var_key.upper(), default=self.data))

    def compile(self):
        """
        Override the way an EnvRef is compiled, since we want to reveal it via the env later.
        """
        compiled = f"?{{{self.type_name}:{self.path}:{self.hash[:8]}}}"
        return compiled


class EnvRefBackend(PlainRefBackend):
    def __init__(self, path, ref_type=EnvRef, **ref_kwargs):
        "Get and create EnvRefs"
        super().__init__(path, ref_type, ref_kwargs=ref_kwargs)
        self.type_name = "env"
