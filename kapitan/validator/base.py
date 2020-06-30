# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import logging

logger = logging.getLogger(__name__)


class Validator(object):
    def __init__(self, cache_dir, **kwargs):
        self.cache_dir = cache_dir

    def validate(self, validate_obj, **kwargs):
        raise NotImplementedError
