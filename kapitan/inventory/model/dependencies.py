from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from kapitan.utils import StrEnum


class KapitanDependencyTypes(StrEnum):
    HELM = "helm"
    HTTP = "http"
    HTTPS = "https"
    GIT = "git"


class KapitanDependencyBaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: KapitanDependencyTypes
    source: str
    output_path: str
    force_fetch: bool | None = False


class KapitanDependencyHelmConfig(KapitanDependencyBaseConfig):
    type: Literal[KapitanDependencyTypes.HELM] = KapitanDependencyTypes.HELM
    chart_name: str
    version: str | None = None
    helm_path: str | None = None


class KapitanDependencyGitConfig(KapitanDependencyBaseConfig):
    type: Literal[KapitanDependencyTypes.GIT] = KapitanDependencyTypes.GIT
    ref: str | None = "master"
    subdir: str | None = None
    submodules: bool | None = False


class KapitanDependencyHttpsConfig(KapitanDependencyBaseConfig):
    type: Literal[KapitanDependencyTypes.HTTPS, KapitanDependencyTypes.HTTP]
    unpack: bool = False


DependencyTypeConfig = Annotated[
    Union[
        KapitanDependencyHelmConfig,
        KapitanDependencyHttpsConfig,
        KapitanDependencyGitConfig,
    ],
    Field(discriminator="type"),
]
