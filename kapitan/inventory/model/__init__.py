from enum import StrEnum, auto
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


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


class KapitanCompileBaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    output_path: str
    input_paths: List[str]
    input_type: InputType
    output_type: OutputType = OutputType.YAML
    ignore_missing: bool = False
    prune: bool = False


class KapitanCompileExternalConfig(KapitanCompileBaseConfig):
    model_config = ConfigDict(extra="forbid")
    env_vars: dict[str, str] = {}
    input_type: InputType = InputType.EXTERNAL


class KapitanCompileJinja2Config(KapitanCompileBaseConfig):
    model_config = ConfigDict(extra="forbid")
    input_type: InputType = InputType.JINJA2
    output_type: OutputType = OutputType.PLAIN
    input_params: dict = {}


class KapitanCompileHelmConfig(KapitanCompileBaseConfig):
    model_config = ConfigDict(extra="forbid")
    input_type: InputType = InputType.HELM
    output_type: OutputType = OutputType.YAML
    input_params: dict = {}
    helm_values: dict = {}
    helm_params: dict = {}


class KapitanCompileJsonnetConfig(KapitanCompileBaseConfig):
    model_config = ConfigDict(extra="forbid")
    input_type: InputType = InputType.JSONNET
    output_type: OutputType = OutputType.JSON
    input_params: dict = {}


class KapitanCompileKadetConfig(KapitanCompileBaseConfig):
    model_config = ConfigDict(extra="forbid")
    input_type: InputType = InputType.KADET
    output_type: OutputType = OutputType.YAML
    input_params: dict = {}


class KapitanInventorySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    compile: List[
        KapitanCompileJinja2Config
        | KapitanCompileExternalConfig
        | KapitanCompileKadetConfig
        | KapitanCompileJsonnetConfig
        | KapitanCompileHelmConfig
    ] = []
    vars: dict[str, str] = {}
    labels: dict[str, str] = {}
    dependencies: List[dict] = []
    target_full_path: str


class KapitanInventoryParameters(BaseModel):
    model_config = ConfigDict(extra="allow")

    kapitan: Optional[KapitanInventorySettings] = None
    _kapitan_: dict = {}
    _reclass_: dict = {}
