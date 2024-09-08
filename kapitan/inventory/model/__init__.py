from enum import StrEnum, auto
from typing import Annotated, List, Literal, Optional, Union

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


class InputTypes(StrEnum):
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
    HELM = "helm"
    HTTP = "http"
    HTTPS = "https"
    GIT = "git"


class KapitanCompileBaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(default=None)
    input_type: InputTypes
    output_path: str
    input_params: dict = {}
    continue_on_compile_error: Optional[bool] = False

    output_type: OutputType = OutputType.YAML
    ignore_missing: Optional[bool] = False
    prune: Optional[bool] = True


class KapitanCompileJsonnetConfig(KapitanCompileBaseConfig):
    input_type: Literal[InputTypes.JSONNET] = InputTypes.JSONNET
    output_type: OutputType = OutputType.JSON
    input_paths: List[str]
    prune: bool = False


class KapitanCompileExternalConfig(KapitanCompileBaseConfig):
    input_type: Literal[InputTypes.EXTERNAL] = InputTypes.EXTERNAL
    env_vars: dict[str, str] = {}
    args: List[str] = []
    input_paths: List[str]


class KapitanCompileCopy(KapitanCompileBaseConfig):
    input_type: Literal[InputTypes.COPY] = InputTypes.COPY
    input_paths: List[str]
    ignore_missing: bool = False


class KapitanCompileJinja2Config(KapitanCompileBaseConfig):
    input_type: Literal[InputTypes.JINJA2] = InputTypes.JINJA2
    input_paths: List[str]
    output_type: Optional[OutputType] = OutputType.PLAIN
    ignore_missing: Optional[bool] = True
    suffix_remove: Optional[bool] = False
    suffix_stripped: Optional[str] = ".j2"


class KapitanCompileHelmConfig(KapitanCompileBaseConfig):
    input_type: Literal[InputTypes.HELM] = InputTypes.HELM
    helm_params: dict = {}
    helm_values: Optional[dict] = {}
    helm_values_files: Optional[List[str]] = []
    helm_path: Optional[str] = None
    input_paths: List[str]
    kube_version: Optional[str] = None


class KapitanCompileKadetConfig(KapitanCompileBaseConfig):
    input_type: Literal[InputTypes.KADET] = InputTypes.KADET
    output_type: OutputType = OutputType.YAML
    input_paths: List[str]
    input_value: Optional[dict] = None


class KapitanCompileRemoveConfig(KapitanCompileBaseConfig):
    input_type: Literal[InputTypes.REMOVE]
    input_paths: List[str]


class KapitanEssentialVars(BaseModel):
    model_config = ConfigDict(extra="allow")
    target: str = "sss"


class KapitanDependencyBaseConfig(BaseModel):
    type: KapitanDependencyTypes
    source: str
    output_path: str


class KapitanDependencyHelmConfig(KapitanDependencyBaseConfig):
    type: Literal[KapitanDependencyTypes.HELM] = KapitanDependencyTypes.HELM
    chart_name: str
    version: Optional[str] = None
    helm_path: Optional[str] = None
    force_fetch: Optional[bool] = False


class KapitanDependencyGitConfig(KapitanDependencyBaseConfig):
    type: Literal[KapitanDependencyTypes.GIT] = KapitanDependencyTypes.GIT
    ref: Optional[str] = "master"
    subdir: Optional[str] = None
    submodules: Optional[bool] = False


class KapitanDependencyHttpsConfig(KapitanDependencyBaseConfig):
    type: Literal[KapitanDependencyTypes.HTTPS, KapitanDependencyTypes.HTTP]
    unpack: bool = False


CompileInputTypeConfig = Annotated[
    Union[
        KapitanCompileJinja2Config,
        KapitanCompileExternalConfig,
        KapitanCompileCopy,
        KapitanCompileKadetConfig,
        KapitanCompileJsonnetConfig,
        KapitanCompileHelmConfig,
        KapitanCompileRemoveConfig,
    ],
    Field(discriminator="input_type"),
]

DependencyTypeConfig = Union[
    KapitanDependencyHelmConfig, KapitanDependencyHttpsConfig, KapitanDependencyGitConfig
]


class KapitanInventorySettings(BaseModel):
    compile: List[CompileInputTypeConfig] = []
    vars: KapitanEssentialVars = KapitanEssentialVars()
    labels: dict[str, str] = {}
    dependencies: List[DependencyTypeConfig] = []
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
