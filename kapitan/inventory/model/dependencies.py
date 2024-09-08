from enum import auto
from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from kapitan.utils import StrEnum


class KapitanDependencyTypes(StrEnum):
    HELM = auto()
    HTTP = auto()
    HTTPS = auto()
    GIT = auto()


class KapitanDependencyBaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
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


DependencyTypeConfig = Union[
    KapitanDependencyHelmConfig, KapitanDependencyHttpsConfig, KapitanDependencyGitConfig
]
