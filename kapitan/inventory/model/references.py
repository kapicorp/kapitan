from typing import List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict

from kapitan.utils import StrEnum


class KapitanReferenceBaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KapitanReferenceGPGConfig(KapitanReferenceBaseConfig):
    recipients: List[dict[str, str]] = []


class KapitanReferenceVaultEnv(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VAULT_",
    )
    addr: Optional[str] = None
    skip_verify: Optional[bool] = True
    client_key: Optional[str] = None
    client_cert: Optional[str] = None
    cacert: Optional[str] = None
    capath: Optional[str] = None
    namespace: Optional[str] = None


class VaultEngineTypes(StrEnum):
    KV = "kv"
    KV_V2 = "kv-v2"
    TRANSIT = "transit"


class KapitanReferenceVaultCommon(KapitanReferenceVaultEnv):
    model_config = ConfigDict(use_enum_values=True)
    engine: Optional[VaultEngineTypes] = None
    auth: Optional[str] = None
    crypto_key: Optional[str] = None
    always_latest: Optional[bool] = False
    mount: Optional[str] = None
    key: Optional[str] = None


class KapitanReferenceVaultKVConfig(KapitanReferenceVaultCommon):
    engine: Literal[VaultEngineTypes.KV, VaultEngineTypes.KV_V2] = VaultEngineTypes.KV_V2
    mount: Optional[str] = "secret"


class KapitanReferenceVaultTransitConfig(KapitanReferenceVaultCommon):
    engine: Literal[VaultEngineTypes.TRANSIT] = VaultEngineTypes.TRANSIT
    key: Optional[str] = None
    mount: Optional[str] = "transit"


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
