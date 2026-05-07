from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from kapitan.utils import StrEnum


class KapitanDependencyTypes(StrEnum):
    HELM = "helm"
    HTTP = "http"
    HTTPS = "https"
    GIT = "git"
    OCI = "oci"


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


class KapitanDependencyOciConfig(KapitanDependencyBaseConfig):
    """Pull an artifact from an OCI-compliant registry."""

    type: Literal[KapitanDependencyTypes.OCI] = KapitanDependencyTypes.OCI
    subpath: str | None = None
    media_type: str | None = None
    insecure: bool = False
    tls_verify: bool | str = True

    @field_validator("source")
    @classmethod
    def source_must_not_have_url_scheme(cls, v: str) -> str:
        for prefix in ("https://", "http://", "oci://"):
            if v.startswith(prefix):
                raise ValueError(
                    f"OCI source must be a bare registry reference "
                    f"(e.g. 'ghcr.io/org/repo:tag'), not a URL. "
                    f"Remove the '{prefix}' prefix."
                )
        return v

    @field_validator("media_type")
    @classmethod
    def media_type_must_be_valid_mime(cls, v: str | None) -> str | None:
        if v is not None and "/" not in v:
            raise ValueError(
                f"media_type '{v}' is not a valid MIME type. "
                f"Expected format: 'type/subtype' "
                f"(e.g. 'application/vnd.oci.image.layer.v1.tar+gzip')."
            )
        return v


DependencyTypeConfig = Annotated[
    Union[
        KapitanDependencyHelmConfig,
        KapitanDependencyHttpsConfig,
        KapitanDependencyGitConfig,
        KapitanDependencyOciConfig,
    ],
    Field(discriminator="type"),
]
