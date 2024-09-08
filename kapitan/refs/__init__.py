# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

from enum import StrEnum, auto


class KapitanReferencesTypes(StrEnum):
    GPG = auto()
    VAULTKV = auto()
    VAULTTRANSIT = auto()
    AWSKMS = auto()
    GKMS = auto()
    AZKMS = auto()
    BASE64 = auto()
    PLAIN = auto()
    ENV = auto()
