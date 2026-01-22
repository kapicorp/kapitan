from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings

from kapitan.utils import StrEnum


class KapitanReferenceBaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KapitanReferenceGPGConfig(KapitanReferenceBaseConfig):
    recipients: list[dict[str, str]] = []


# Must be pydantic_settings.BaseSettings so that environment variables are actually used to
# populate the object. Any of the validation alias choices can be used as environment variable
# names.
# Note that this will break if both alias choices are set for a field (either through envvar or
# initializer).
class KapitanReferenceVaultEnv(BaseSettings):
    addr: str | None = Field(
        None, validation_alias=AliasChoices("addr", "VAULT_ADDR")
    )
    skip_verify: bool | None = Field(
        True, validation_alias=AliasChoices("skip_verify", "VAULT_SKIP_VERIFY")
    )
    client_key: str | None = Field(
        None, validation_alias=AliasChoices("client_key", "VAULT_CLIENT_KEY")
    )
    client_cert: str | None = Field(
        None, validation_alias=AliasChoices("client_cert", "VAULT_CLIENT_CERT")
    )
    cacert: str | None = Field(
        None, validation_alias=AliasChoices("cacert", "VAULT_CACERT")
    )
    capath: str | None = Field(
        None, validation_alias=AliasChoices("capath", "VAULT_CAPATH")
    )
    namespace: str | None = Field(
        None, validation_alias=AliasChoices("namespace", "VAULT_NAMESPACE")
    )


class VaultEngineTypes(StrEnum):
    KV = "kv"
    KV_V2 = "kv-v2"
    TRANSIT = "transit"


class KapitanReferenceVaultCommon(KapitanReferenceVaultEnv):
    model_config = ConfigDict(use_enum_values=True)
    engine: VaultEngineTypes | None = None
    auth: str | None = None
    crypto_key: str | None = None
    always_latest: bool | None = False
    mount: str | None = None
    key: str | None = None


class KapitanReferenceVaultKVConfig(KapitanReferenceVaultCommon):
    engine: Literal[VaultEngineTypes.KV, VaultEngineTypes.KV_V2] = (
        VaultEngineTypes.KV_V2
    )
    mount: str | None = "secret"


class KapitanReferenceVaultTransitConfig(KapitanReferenceVaultCommon):
    engine: Literal[VaultEngineTypes.TRANSIT] = VaultEngineTypes.TRANSIT
    key: str | None = None
    mount: str | None = "transit"


class KapitanReferenceAWKMSConfig(KapitanReferenceBaseConfig):
    key: str


class KapitanReferenceGKMSConfig(KapitanReferenceBaseConfig):
    key: str


class KapitanReferenceAZKMSConfig(KapitanReferenceBaseConfig):
    key: str


class KapitanReferenceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gpg: KapitanReferenceGPGConfig | None = None
    awskms: KapitanReferenceAWKMSConfig | None = None
    vaultkv: KapitanReferenceVaultKVConfig | None = None
    gkms: KapitanReferenceGKMSConfig | None = None
    vaulttransit: KapitanReferenceVaultTransitConfig | None = None
    azkms: KapitanReferenceAZKMSConfig | None = None
