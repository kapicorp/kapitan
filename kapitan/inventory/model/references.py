from typing import List, Literal, Optional, Union

from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings

from kapitan.utils import StrEnum


class KapitanReferenceBaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KapitanReferenceGPGConfig(KapitanReferenceBaseConfig):
    recipients: List[dict[str, str]] = []


# Must be pydantic_settings.BaseSettings so that environment variables are actually used to
# populate the object. Any of the validation alias choices can be used as environment variable
# names.
# Note that this will break if both alias choices are set for a field (either through envvar or
# initializer).
class KapitanReferenceVaultEnv(BaseSettings):
    addr: Optional[str] = Field(None, validation_alias=AliasChoices("addr", "VAULT_ADDR"))
    skip_verify: Optional[bool] = Field(
        True, validation_alias=AliasChoices("skip_verify", "VAULT_SKIP_VERIFY")
    )
    client_key: Optional[str] = Field(None, validation_alias=AliasChoices("client_key", "VAULT_CLIENT_KEY"))
    client_cert: Optional[str] = Field(
        None, validation_alias=AliasChoices("client_cert", "VAULT_CLIENT_CERT")
    )
    cacert: Optional[str] = Field(None, validation_alias=AliasChoices("cacert", "VAULT_CACERT"))
    capath: Optional[str] = Field(None, validation_alias=AliasChoices("capath", "VAULT_CAPATH"))
    namespace: Optional[str] = Field(None, validation_alias=AliasChoices("namespace", "VAULT_NAMESPACE"))


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
