import logging
from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from kapitan.utils import StrEnum

logger = logging.getLogger(__name__)


class InputTypes(StrEnum):
    JSONNET = "jsonnet"
    JINJA2 = "jinja2"
    HELM = "helm"
    KADET = "kadet"
    COPY = "copy"
    REMOVE = "remove"
    EXTERNAL = "external"


class OutputType(StrEnum):
    JSON = "json"
    YAML = "yaml"
    YML = "yml"
    PLAIN = "plain"
    TOML = "toml"
    AUTO = "auto"


class KapitanInputTypeBaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(default=None)
    input_type: InputTypes
    input_paths: List[str]
    output_path: str
    input_params: dict = {}
    continue_on_compile_error: Optional[bool] = False

    output_type: OutputType = OutputType.YAML
    ignore_missing: Optional[bool] = False
    prune: Optional[bool] = True


class KapitanInputTypeJsonnetConfig(KapitanInputTypeBaseConfig):
    input_type: Literal[InputTypes.JSONNET] = InputTypes.JSONNET
    prune: Optional[bool] = False


class KapitanInputTypeExternalConfig(KapitanInputTypeBaseConfig):
    input_type: Literal[InputTypes.EXTERNAL] = InputTypes.EXTERNAL
    env_vars: dict[str, str] = {}
    args: List[str] = []


class KapitanInputTypeCopyConfig(KapitanInputTypeBaseConfig):
    input_type: Literal[InputTypes.COPY] = InputTypes.COPY
    ignore_missing: bool = False


class KapitanInputTypeJinja2Config(KapitanInputTypeBaseConfig):
    input_type: Literal[InputTypes.JINJA2] = InputTypes.JINJA2
    output_type: Optional[OutputType] = OutputType.PLAIN
    ignore_missing: Optional[bool] = True
    suffix_remove: Optional[bool] = False
    suffix_stripped: Optional[str] = ".j2"


class KapitanInputTypeHelmConfig(KapitanInputTypeBaseConfig):
    input_type: Literal[InputTypes.HELM] = InputTypes.HELM
    output_type: OutputType = OutputType.AUTO
    prune: Optional[bool] = False
    helm_params: dict = {}
    helm_values: Optional[dict] = {}
    helm_values_files: Optional[List[str]] = []
    helm_path: Optional[str] = None
    kube_version: Optional[str] = None

    @field_validator("output_type")
    @classmethod
    def type_must_be_auto(cls, _: OutputType) -> OutputType:
        """Helm output type must be auto."""
        logger.debug("field `output_type` for helm input type must be set to 'auto': enforcing.")
        return OutputType.AUTO


class KapitanInputTypeKadetConfig(KapitanInputTypeBaseConfig):
    input_type: Literal[InputTypes.KADET] = InputTypes.KADET
    output_type: OutputType = OutputType.YAML
    input_value: Optional[dict] = None
    prune: Optional[bool] = False


class KapitanInputTypeRemoveConfig(KapitanInputTypeBaseConfig):
    input_type: Literal[InputTypes.REMOVE] = InputTypes.REMOVE
    output_path: Optional[str] = None


CompileInputTypeConfig = Annotated[
    Union[
        KapitanInputTypeJinja2Config,
        KapitanInputTypeExternalConfig,
        KapitanInputTypeCopyConfig,
        KapitanInputTypeKadetConfig,
        KapitanInputTypeJsonnetConfig,
        KapitanInputTypeHelmConfig,
        KapitanInputTypeRemoveConfig,
    ],
    Field(discriminator="input_type"),
]
