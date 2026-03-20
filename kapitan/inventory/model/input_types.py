import logging
from typing import Annotated, Any, Literal, Union

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
    KUSTOMIZE = "kustomize"
    CUELANG = "cuelang"


class OutputType(StrEnum):
    JSON = "json"
    YAML = "yaml"
    YML = "yml"
    PLAIN = "plain"
    TOML = "toml"
    AUTO = "auto"


class KapitanInputTypeBaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None)
    input_type: InputTypes
    input_paths: list[str]
    output_path: str
    input_params: dict = {}
    continue_on_compile_error: bool | None = False

    output_type: OutputType = OutputType.YAML
    ignore_missing: bool | None = False
    prune: bool | None = True


class KapitanInputTypeJsonnetConfig(KapitanInputTypeBaseConfig):
    input_type: Literal[InputTypes.JSONNET] = InputTypes.JSONNET
    prune: bool | None = False


class KapitanInputTypeExternalConfig(KapitanInputTypeBaseConfig):
    input_type: Literal[InputTypes.EXTERNAL] = InputTypes.EXTERNAL
    env_vars: dict[str, str] = {}
    args: list[str] = []


class KapitanInputTypeCopyConfig(KapitanInputTypeBaseConfig):
    input_type: Literal[InputTypes.COPY] = InputTypes.COPY
    ignore_missing: bool = False


class KapitanInputTypeJinja2Config(KapitanInputTypeBaseConfig):
    input_type: Literal[InputTypes.JINJA2] = InputTypes.JINJA2
    output_type: OutputType | None = OutputType.PLAIN
    ignore_missing: bool | None = True
    suffix_remove: bool | None = False
    suffix_stripped: str | None = ".j2"


class KapitanInputTypeHelmConfig(KapitanInputTypeBaseConfig):
    input_type: Literal[InputTypes.HELM] = InputTypes.HELM
    output_type: OutputType = OutputType.AUTO
    prune: bool | None = False
    helm_params: dict = {}
    helm_values: dict | None = {}
    helm_values_files: list[str] | None = []
    helm_path: str | None = None
    kube_version: str | None = None

    @field_validator("output_type")
    @classmethod
    def type_must_be_auto(cls, _: OutputType) -> OutputType:
        """Helm output type must be auto."""
        logger.debug(
            "field `output_type` for helm input type must be set to 'auto': enforcing."
        )
        return OutputType.AUTO


class KapitanInputTypeKadetConfig(KapitanInputTypeBaseConfig):
    input_type: Literal[InputTypes.KADET] = InputTypes.KADET
    output_type: OutputType = OutputType.YAML
    input_value: dict | None = None
    prune: bool | None = False


class KapitanInputTypeRemoveConfig(KapitanInputTypeBaseConfig):
    input_type: Literal[InputTypes.REMOVE] = InputTypes.REMOVE
    output_path: str | None = None


class KapitanInputTypeKustomizeConfig(KapitanInputTypeBaseConfig):
    input_type: Literal[InputTypes.KUSTOMIZE] = InputTypes.KUSTOMIZE
    output_type: OutputType = OutputType.YAML
    namespace: str | None = None
    prune: bool | None = False
    patches: dict[str, Any] | None = {}
    patches_strategic: dict[str, Any] | None = {}
    patches_json: dict[str, Any] | None = {}


class KapitanInputTypeCuelangConfig(KapitanInputTypeBaseConfig):
    input_type: Literal[InputTypes.CUELANG] = InputTypes.CUELANG
    output_type: OutputType = OutputType.YAML
    # optional value to pass to the CUE input
    input: dict[str, Any] | None = None
    # optional CUE path in which the input is injected. By default, the input
    # is injected at the root.
    input_fill_path: str | None = None
    # optional CUE path (e.g. metadata.name) that we want to yield in the output.
    # By default, the whole output is yielded
    output_yield_path: str | None = None
    output_filename: str | None = "output.yaml"


CompileInputTypeConfig = Annotated[
    Union[
        KapitanInputTypeJinja2Config,
        KapitanInputTypeExternalConfig,
        KapitanInputTypeCopyConfig,
        KapitanInputTypeKadetConfig,
        KapitanInputTypeJsonnetConfig,
        KapitanInputTypeHelmConfig,
        KapitanInputTypeRemoveConfig,
        KapitanInputTypeKustomizeConfig,
        KapitanInputTypeCuelangConfig,
    ],
    Field(discriminator="input_type"),
]
