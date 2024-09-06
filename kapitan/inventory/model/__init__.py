from enum import StrEnum, auto
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class KapitanSecretsTypes(StrEnum):
    GPG = auto()
    VAULTKV = auto()
    VAULTTRANSIT = auto()
    AWKMS = auto()
    GKMS = auto()


class KapitanSecretsGPGConfig(BaseModel):
    recipients: List[dict[str, str]] = []


class KapitanSecretsVaultKVConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    auth: str


class KapitanSecretsVaultTransitConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    auth: str


class KapitanSecretsAWKMSConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str


class KapitanSecretsGKMSConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str


class KapitanSecretsAZKMSConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str


class KapitanSecretsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gpg: Optional[KapitanSecretsGPGConfig] = None
    awskms: Optional[KapitanSecretsAWKMSConfig] = None
    vaultkv: Optional[KapitanSecretsVaultKVConfig] = None
    gkms: Optional[KapitanSecretsGKMSConfig] = None
    vaulttransit: Optional[KapitanSecretsVaultTransitConfig] = None
    azkms: Optional[KapitanSecretsAZKMSConfig] = None


class InputType(StrEnum):
    JSONNET = auto()
    JINJA2 = auto()
    HELM = auto()
    KADET = auto()
    COPY = auto()
    REMOVE = auto()
    EXTERNAL = auto()


class OutputType(StrEnum):
    JSON = auto()
    YAML = auto()
    YML = auto()
    PLAIN = auto()
    TOML = auto()


class KapitanDependencyTypes(StrEnum):
    HELM = auto()
    HTTP = auto()
    HTTPS = auto()
    GIT = auto()


class KapitanCompileBaseConfig(BaseModel):
    output_path: str
    input_paths: List[str]
    input_type: InputType
    output_type: OutputType = OutputType.YAML
    ignore_missing: bool = False
    prune: bool = True
    continue_on_compile_error: bool = False


class KapitanCompileExternalConfig(KapitanCompileBaseConfig):
    env_vars: dict[str, str] = {}
    input_type: InputType = InputType.EXTERNAL
    input_params: dict = {}


class KapitanCompileCopy(KapitanCompileBaseConfig):
    input_type: InputType = InputType.COPY
    ignore_missing: bool = False


class KapitanCompileJinja2Config(KapitanCompileBaseConfig):
    input_type: InputType = InputType.JINJA2
    output_type: OutputType = OutputType.PLAIN
    input_params: dict = {}
    ignore_missing: bool = True
    suffix_remove: bool = False
    suffix_stripped: str = ".j2"


class KapitanCompileHelmConfig(KapitanCompileBaseConfig):
    input_type: InputType = InputType.HELM
    output_type: OutputType = OutputType.YAML
    input_params: dict = {}
    helm_values: dict = {}
    helm_params: dict = {}


class KapitanCompileJsonnetConfig(KapitanCompileBaseConfig):
    input_type: InputType = InputType.JSONNET
    output_type: OutputType = OutputType.JSON
    input_params: dict = {}


class KapitanCompileKadetConfig(KapitanCompileBaseConfig):
    input_type: InputType = InputType.KADET
    output_type: OutputType = OutputType.YAML
    input_params: dict = {}


class KapitanEssentialVars(BaseModel):
    model_config = ConfigDict(extra="allow")
    target: str = "sss"


class KapitanDependencyBaseConfig(BaseModel):
    type: KapitanDependencyTypes
    source: str
    output_path: str


class KapitanDependendencyHelmConfig(KapitanDependencyBaseConfig):
    type: KapitanDependencyTypes = KapitanDependencyTypes.HELM
    version: str
    chart_name: str
    helm_path: Optional[str] = None


class KapitanDependendencyGitConfig(KapitanDependencyBaseConfig):
    type: KapitanDependencyTypes = KapitanDependencyTypes.GIT
    ref: Optional[str] = "master"
    subdir: Optional[str] = None
    submodules: Optional[bool] = False


class KapitanDependendencyHttpConfig(KapitanDependencyBaseConfig):
    type: KapitanDependencyTypes = KapitanDependencyTypes.HTTP
    unpack: bool = False


class KapitanDependendencyHttpsConfig(KapitanDependendencyHttpConfig):
    type: KapitanDependencyTypes = KapitanDependencyTypes.HTTPS


class KapitanInventorySettings(BaseModel):

    compile: List[
        KapitanCompileJinja2Config
        | KapitanCompileExternalConfig
        | KapitanCompileKadetConfig
        | KapitanCompileJsonnetConfig
        | KapitanCompileHelmConfig
    ] = []
    vars: KapitanEssentialVars = KapitanEssentialVars()
    labels: dict[str, str] = {}
    dependencies: List[
        KapitanDependendencyHelmConfig
        | KapitanDependendencyHttpConfig
        | KapitanDependendencyHttpsConfig
        | KapitanDependendencyGitConfig
    ] = []
    target_full_path: str = ""
    secrets: Optional[KapitanSecretsConfig] = None
    validate_: list[dict] = Field(alias="validate", default=[])


class KapitanMetadataName(BaseModel):
    short: str
    full: str
    path: str
    parts: List[str]


class KapitanInventoryMetadata(BaseModel):
    model_config = ConfigDict(extra="allow", validate_assignment=True)
    name: Optional[KapitanMetadataName] = None


class KapitanInventoryParameters(BaseModel):
    model_config = ConfigDict(extra="allow")

    kapitan: Optional[KapitanInventorySettings] = KapitanInventorySettings()
    kapitan_metadata: Optional[KapitanInventoryMetadata] = Field(alias="_kapitan_", default=None)
    reclass_metadata: Optional[KapitanInventoryMetadata] = Field(alias="_reclass_", default=None)
