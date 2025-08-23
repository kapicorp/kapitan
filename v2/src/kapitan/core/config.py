"""Configuration management for Kapitan."""

import os
from enum import Enum
from pathlib import Path
from typing import Optional

import tomllib
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class OutputFormat(str, Enum):
    """Output formats."""
    CONSOLE = "console"  # Rich terminal output with colors and formatting
    PLAIN = "plain"      # Plain text output for CI/pipes
    JSON = "json"        # JSON output for programmatic use


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: LogLevel = LogLevel.INFO
    show_time: bool = True
    show_path: bool = False
    json_format: bool = False
    
    class Config:
        use_enum_values = True


class GlobalConfig(BaseModel):
    """Global configuration."""
    inventory_path: str = Field(default="inventory", description="Default inventory directory path")
    output_path: str = Field(default="compiled", description="Default output directory path")
    cache_dir: Optional[str] = Field(default=None, description="Cache directory path")
    parallel_jobs: int = Field(default=4, description="Number of parallel jobs for compilation")
    output_format: OutputFormat = OutputFormat.CONSOLE
    verbose: bool = False
    
    class Config:
        use_enum_values = True


class KapitanConfig(BaseSettings):
    """Main Kapitan configuration."""
    model_config = SettingsConfigDict(
        env_prefix="KAPITAN_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore"
    )
    
    global_: GlobalConfig = Field(default_factory=GlobalConfig, alias="global")
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    @classmethod
    def load_from_file(cls, config_path: Optional[Path] = None) -> "KapitanConfig":
        """Load configuration from TOML file and environment variables."""
        config_data = {}
        
        # Determine config file path
        if config_path is None:
            # Look for kapitan.toml in current directory and parent directories
            current_dir = Path.cwd()
            for parent in [current_dir] + list(current_dir.parents):
                potential_config = parent / "kapitan.toml"
                if potential_config.exists():
                    config_path = potential_config
                    break
        
        # Load base TOML configuration if file exists
        if config_path and config_path.exists():
            try:
                with open(config_path, "rb") as f:
                    config_data = tomllib.load(f)
            except (OSError, tomllib.TOMLDecodeError) as e:
                raise ValueError(f"Error loading configuration from {config_path}: {e}")
        
        # Load CI override configuration if it exists
        ci_config_path = None
        if config_path:
            # Look for kapitan.ci.toml in the same directory as main config
            ci_config_path = config_path.parent / "kapitan.ci.toml"
        else:
            # Look for kapitan.ci.toml in current directory and parent directories
            current_dir = Path.cwd()
            for parent in [current_dir] + list(current_dir.parents):
                potential_ci_config = parent / "kapitan.ci.toml"
                if potential_ci_config.exists():
                    ci_config_path = potential_ci_config
                    break
        
        # Override with CI configuration if it exists
        if ci_config_path and ci_config_path.exists():
            try:
                with open(ci_config_path, "rb") as f:
                    ci_config_data = tomllib.load(f)
                    # Deep merge CI config over base config
                    config_data = cls._deep_merge_config(config_data, ci_config_data)
            except (OSError, tomllib.TOMLDecodeError) as e:
                raise ValueError(f"Error loading CI configuration from {ci_config_path}: {e}")
        
        # Create configuration instance with TOML data and environment variables
        return cls(**config_data)
    
    @staticmethod
    def _deep_merge_config(base: dict, override: dict) -> dict:
        """Deep merge override configuration into base configuration."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = KapitanConfig._deep_merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get_cache_dir(self) -> Path:
        """Get cache directory path, creating if necessary."""
        if self.global_.cache_dir:
            cache_dir = Path(self.global_.cache_dir)
        else:
            cache_dir = Path.home() / ".kapitan" / "cache"
        
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
    
    def get_inventory_path(self) -> Path:
        """Get inventory path as Path object."""
        return Path(self.global_.inventory_path)
    
    def get_output_path(self) -> Path:
        """Get output path as Path object."""
        return Path(self.global_.output_path)


# Global configuration instance
_config: Optional[KapitanConfig] = None


def get_config() -> KapitanConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = KapitanConfig.load_from_file()
    return _config


def reload_config(config_path: Optional[Path] = None) -> KapitanConfig:
    """Reload configuration from file."""
    global _config
    _config = KapitanConfig.load_from_file(config_path)
    return _config