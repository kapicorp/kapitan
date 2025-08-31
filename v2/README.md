# Kapitan

Generic templated configuration management for Kubernetes, Terraform and other things.

## Development Setup

This project uses [uv](https://github.com/astral-sh/uv) for dependency management and packaging.

### Prerequisites

- Python 3.13+
- uv

### Installation

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync

# Install development dependencies
uv sync --group dev

# Install pre-commit hooks
uv run pre-commit install
```

### Development Commands

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov

# Lint and format code
uv run ruff check .
uv run ruff format .

# Type checking
uv run mypy src/

# Run the CLI
uv run kapitan --help

# Run with JSON output
uv run kapitan compile --json

# Run with verbose logging
uv run kapitan compile --verbose

# Use custom configuration file
uv run kapitan --config my-config.toml compile
```

## Configuration

Kapitan v2 supports configuration through TOML files and environment variables.

### Configuration File

Create a `kapitan.toml` file in your project directory:

```toml
[global]
inventory_path = "inventory"
output_path = "compiled"
parallel_jobs = 8
output_format = "console"  # "console", "plain", or "json"
verbose = false

[logging]
level = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
show_time = true
show_path = false
json_format = false
```

### Environment Variables

Override any configuration with environment variables:

```bash
export KAPITAN_GLOBAL__VERBOSE=true
export KAPITAN_LOGGING__LEVEL=DEBUG
export KAPITAN_GLOBAL__PARALLEL_JOBS=8
```

### CI Configuration Override

Create a `kapitan.ci.toml` file for CI-specific settings that override `kapitan.toml`:

```toml
[global]
output_format = "plain"  # Plain text output for CI
verbose = true           # Enable verbose output for CI debugging
parallel_jobs = 8        # More parallel jobs for faster builds

[logging]
level = "INFO"
show_time = true
show_path = true
```

### Output Formats

- **`console`**: Rich terminal output with colors, panels, and progress bars (default)
- **`plain`**: Plain text output ideal for CI/CD pipelines and log files
- **`json`**: Structured JSON output for programmatic use and automation

### Configuration Precedence

1. CLI arguments (highest priority)
2. Environment variables
3. CI configuration file (`kapitan.ci.toml`)
4. Configuration file (`kapitan.toml`)
5. Default values (lowest priority)

### Project Structure

```
v2/
├── src/kapitan/              # Main package
│   ├── cli/                  # Command line interface
│   ├── core/                 # Core functionality
│   │   ├── config.py         # Configuration management
│   │   └── exceptions.py     # Exception classes
│   ├── inputs/               # Input processors
│   ├── inventory/            # Inventory management
│   └── refs/                 # Reference handling
├── tests/                    # Test suite
├── docs/                     # Documentation
├── scripts/                  # Utility scripts
├── kapitan.toml             # Main configuration file
└── kapitan.ci.toml          # CI override configuration
```

## Features

This is a complete rewrite of Kapitan with modern Python practices:

- **Type Safety**: Full type hints with mypy checking
- **Modern Dependencies**: Pydantic v2, Typer for CLI, Rich for beautiful terminal output and logging
- **Developer Experience**: Ruff for linting/formatting, uv for package management
- **Testing**: Comprehensive test suite with pytest
- **Documentation**: MkDocs with Material theme

## License

Apache License 2.0