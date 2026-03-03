from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from kapitan.inventory.model.dependencies import DependencyTypeConfig
from kapitan.inventory.model.input_types import CompileInputTypeConfig
from kapitan.inventory.model.references import KapitanReferenceConfig


class KapitanEssentialVars(BaseModel):
    model_config = ConfigDict(extra="allow")
    target: str | None = None


class KapitanInventorySettings(BaseModel):
    compile: list[CompileInputTypeConfig] = []
    vars: KapitanEssentialVars = KapitanEssentialVars()
    labels: dict[str, str] = {}
    dependencies: list[DependencyTypeConfig] | None = []
    target_full_path: str = ""
    secrets: KapitanReferenceConfig | None = None
    validate_: list[dict] = Field(alias="validate", default=[])


class KapitanMetadataName(BaseModel):
    short: str
    full: str
    path: str
    parts: list[str]


class KapitanInventoryMetadata(BaseModel):
    model_config = ConfigDict(extra="allow", validate_assignment=True)
    name: KapitanMetadataName | None = None


class KapitanInventoryParameters(BaseModel):
    model_config = ConfigDict(extra="allow")

    kapitan: KapitanInventorySettings | None = KapitanInventorySettings()
    kapitan_metadata: KapitanInventoryMetadata | None = Field(
        alias="_kapitan_", default=None
    )
    reclass_metadata: KapitanInventoryMetadata | None = Field(
        alias="_reclass_", default=None
    )
