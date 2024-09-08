from enum import StrEnum, auto
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class KapitanReferenceBaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KapitanReferenceGPGConfig(KapitanReferenceBaseConfig):
    recipients: List[dict[str, str]] = []


class KapitanReferenceVaultKVConfig(KapitanReferenceBaseConfig):
    auth: str


class KapitanReferenceVaultTransitConfig(KapitanReferenceBaseConfig):
    key: str
    auth: str


class KapitanReferenceAWKMSConfig(KapitanReferenceBaseConfig):
    key: str


class KapitanReferenceGKMSConfig(KapitanReferenceBaseConfig):
    key: str


class KapitanReferenceAZKMSConfig(KapitanReferenceBaseConfig):
    key: str


class KapitanReferenceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gpg: Optional[KapitanReferenceGPGConfig] = None
    awskms: Optional[KapitanReferenceAWKMSConfig] = None
    vaultkv: Optional[KapitanReferenceVaultKVConfig] = None
    gkms: Optional[KapitanReferenceGKMSConfig] = None
    vaulttransit: Optional[KapitanReferenceVaultTransitConfig] = None
    azkms: Optional[KapitanReferenceAZKMSConfig] = None
