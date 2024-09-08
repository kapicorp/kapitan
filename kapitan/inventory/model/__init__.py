from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from kapitan.inventory.model.dependencies import DependencyTypeConfig
from kapitan.inventory.model.input_types import CompileInputTypeConfig
from kapitan.inventory.model.references import KapitanReferenceConfig


class KapitanEssentialVars(BaseModel):
    model_config = ConfigDict(extra="allow")
    target: Optional[str] = None


class KapitanInventorySettings(BaseModel):
    compile: List[CompileInputTypeConfig] = []
    vars: KapitanEssentialVars = KapitanEssentialVars()
    labels: dict[str, str] = {}
    dependencies: Optional[List[DependencyTypeConfig]] = []
    target_full_path: str = ""
    secrets: Optional[KapitanReferenceConfig] = None
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
