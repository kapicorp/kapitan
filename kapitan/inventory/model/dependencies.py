from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict

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
    force_fetch: Optional[bool] = False


class KapitanDependencyHelmConfig(KapitanDependencyBaseConfig):
    type: Literal[KapitanDependencyTypes.HELM] = KapitanDependencyTypes.HELM
    chart_name: str
    version: Optional[str] = None
    helm_path: Optional[str] = None


class KapitanDependencyGitConfig(KapitanDependencyBaseConfig):
    type: Literal[KapitanDependencyTypes.GIT] = KapitanDependencyTypes.GIT
    ref: Optional[str] = "master"
    subdir: Optional[str] = None
    submodules: Optional[bool] = False


class KapitanDependencyHttpsConfig(KapitanDependencyBaseConfig):
    type: Literal[KapitanDependencyTypes.HTTPS, KapitanDependencyTypes.HTTP]
    unpack: bool = False


DependencyTypeConfig = Union[
    KapitanDependencyHelmConfig, KapitanDependencyHttpsConfig, KapitanDependencyGitConfig
]
