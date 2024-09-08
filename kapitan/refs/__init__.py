# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

from kapitan.utils import StrEnum


class KapitanReferencesTypes(StrEnum):
    GPG = "gpg"
    VAULTKV = "vaultkv"
    VAULTTRANSIT = "vaulttransit"
    AWSKMS = "awskms"
    GKMS = "gkms"
    AZKMS = "azkms"
    BASE64 = "base64"
    PLAIN = "plain"
    ENV = "env"
