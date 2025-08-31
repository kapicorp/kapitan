"""Configuration management system for Skipper.

Provides comprehensive configuration loading with multiple sources and precedence:
- Project configuration (skipper.toml)
- User configuration (~/.kapitan.toml) 
- CI overrides (skipper.ci.toml)
- Environment variables (KAPITAN_*)
- CLI argument overrides
"""

import os
import tomllib
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    """Available logging levels for application output."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class OutputFormat(str, Enum):
    """Available output formats for CLI commands.
    
    Attributes:
        CONSOLE: Rich terminal output with colors and formatting.
        PLAIN: Plain text output suitable for CI and piping.
        JSON: Structured JSON output for programmatic consumption.
    """
    CONSOLE = "console"  # Rich terminal output with colors and formatting
    PLAIN = "plain"      # Plain text output for CI/pipes
    JSON = "json"        # JSON output for programmatic use


class LoggingConfig(BaseModel):
    """Configuration for application logging behavior.
    
    Attributes:
        level: Minimum log level to output.
        show_time: Whether to include timestamps in log output.
        show_path: Whether to include file paths in log output.
        json_format: Whether to use JSON formatting for logs.
    """
    level: LogLevel = LogLevel.INFO
    show_time: bool = True
    show_path: bool = False
    json_format: bool = False

    class Config:
        use_enum_values = True


class GlobalConfig(BaseModel):
    """Global application configuration settings.
    
    Attributes:
        inventory_path: Default path to inventory directory.
        output_path: Default path for compilation output.
        cache_dir: Directory for caching compilation artifacts.
        parallel_jobs: Number of parallel compilation jobs.
        output_format: Default output format for commands.
        verbose: Whether to enable verbose output by default.
    """
    inventory_path: str = Field(default="inventory", description="Default inventory directory path")
    output_path: str = Field(default="compiled", description="Default output directory path")
    cache_dir: str | None = Field(default=None, description="Cache directory path")
    parallel_jobs: int = Field(default=4, description="Number of parallel jobs for compilation")
    output_format: OutputFormat = OutputFormat.CONSOLE
    verbose: bool = False

    @field_validator('inventory_path', 'output_path', 'cache_dir')
    @classmethod
    def expand_path(cls, v: str | None) -> str | None:
        """Expand user home directory and environment variables in path strings.
        
        Args:
            v: Path string that may contain ~ or environment variables.
            
        Returns:
            Expanded path string with ~ and variables resolved, or None.
        """
        if v is None:
            return None
        # Expand ~ to user home directory and environment variables
        expanded = os.path.expanduser(os.path.expandvars(v))
        return expanded

    class Config:
        use_enum_values = True


class KapitanConfig(BaseSettings):
    """Main configuration class with multi-source loading and environment integration.
    
    Supports loading from multiple configuration sources with proper precedence:
    1. CLI arguments (highest)
    2. Environment variables (KAPITAN_*)
    3. CI configuration (skipper.ci.toml)
    4. User configuration (~/.kapitan.toml)
    5. Project configuration (skipper.toml)
    6. Built-in defaults (lowest)
    """
    model_config = SettingsConfigDict(
        env_prefix="KAPITAN_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore"
    )

    global_: GlobalConfig = Field(default_factory=GlobalConfig, alias="global")
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def load_from_file(cls, config_path: Path | None = None) -> "KapitanConfig":
        """Load configuration from multiple sources with proper precedence.
        
        Loads configuration from TOML files and environment variables,
        applying proper precedence rules. Automatically discovers configuration
        files if not explicitly provided.
        
        Args:
            config_path: Explicit path to configuration file, or None for auto-discovery.
            
        Returns:
            Fully configured KapitanConfig instance.
            
        Raises:
            ValueError: If configuration files cannot be loaded or parsed.
        """
        config_data = {}

        # Determine config file path
        if config_path is None:
            # Look for kapitan.toml in current directory and parent directories
            current_dir = Path.cwd()
            for parent in [current_dir] + list(current_dir.parents):
                potential_config = parent / "skipper.toml"
                if potential_config.exists():
                    config_path = potential_config
                    break

        # Load base TOML configuration if file exists
        if config_path and config_path.exists():
            try:
                with open(config_path, "rb") as f:
                    config_data = tomllib.load(f)
            except (OSError, tomllib.TOMLDecodeError) as e:
                raise ValueError(f"Error loading configuration from {config_path}: {e}") from e

        # Load user configuration override from ~/.kapitan.toml
        user_config_path = Path.home() / ".kapitan.toml"
        if user_config_path.exists():
            try:
                with open(user_config_path, "rb") as f:
                    user_config_data = tomllib.load(f)
                    # Deep merge user config over base config
                    config_data = cls._deep_merge_config(config_data, user_config_data)
            except (OSError, tomllib.TOMLDecodeError) as e:
                raise ValueError(f"Error loading user configuration from {user_config_path}: {e}") from e

        # Load CI override configuration if it exists
        ci_config_path = None
        if config_path:
            # Look for kapitan.ci.toml in the same directory as main config
            ci_config_path = config_path.parent / "skipper.ci.toml"
        else:
            # Look for kapitan.ci.toml in current directory and parent directories
            current_dir = Path.cwd()
            for parent in [current_dir] + list(current_dir.parents):
                potential_ci_config = parent / "skipper.ci.toml"
                if potential_ci_config.exists():
                    ci_config_path = potential_ci_config
                    break

        # Override with CI configuration if it exists (highest precedence)
        if ci_config_path and ci_config_path.exists():
            try:
                with open(ci_config_path, "rb") as f:
                    ci_config_data = tomllib.load(f)
                    # Deep merge CI config over base+user config
                    config_data = cls._deep_merge_config(config_data, ci_config_data)
            except (OSError, tomllib.TOMLDecodeError) as e:
                raise ValueError(f"Error loading CI configuration from {ci_config_path}: {e}") from e

        # Create configuration instance with TOML data and environment variables
        config_instance = cls(**config_data)

        # Track configuration sources for debugging
        sources = []
        if config_path and config_path.exists():
            sources.append(f"project: {config_path}")
        if user_config_path.exists():
            sources.append(f"user: {user_config_path}")
        if ci_config_path and ci_config_path.exists():
            sources.append(f"CI: {ci_config_path}")
        if not sources:
            sources.append("defaults only")

        # Store source information for debugging
        config_instance._sources = sources

        return config_instance

    @staticmethod
    def _deep_merge_config(base: dict, override: dict) -> dict:
        """Recursively merge override dictionary into base dictionary.
        
        Args:
            base: Base configuration dictionary.
            override: Override configuration dictionary.
            
        Returns:
            Merged configuration dictionary.
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = KapitanConfig._deep_merge_config(result[key], value)
            else:
                result[key] = value

        return result

    def get_cache_dir(self) -> Path:
        """Get cache directory path, creating directories as needed.
        
        Returns:
            Path object for cache directory, guaranteed to exist.
        """
        if self.global_.cache_dir:
            cache_dir = Path(self.global_.cache_dir)
        else:
            cache_dir = Path.home() / ".kapitan" / "cache"

        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def get_inventory_path(self) -> Path:
        """Get configured inventory path as a Path object.
        
        Returns:
            Path object for inventory directory.
        """
        return Path(self.global_.inventory_path)

    def get_output_path(self) -> Path:
        """Get configured output path as a Path object.
        
        Returns:
            Path object for compilation output directory.
        """
        return Path(self.global_.output_path)


# Global configuration instance
_config: KapitanConfig | None = None


def get_config() -> KapitanConfig:
    """Get the global configuration instance, loading if necessary.
    
    Returns:
        Global KapitanConfig instance.
    """
    global _config
    if _config is None:
        _config = KapitanConfig.load_from_file()
    return _config


def reload_config(config_path: Path | None = None) -> KapitanConfig:
    """Force reload of configuration from file sources.
    
    Args:
        config_path: Optional explicit configuration file path.
        
    Returns:
        Newly loaded KapitanConfig instance.
    """
    global _config
    _config = KapitanConfig.load_from_file(config_path)
    return _config
