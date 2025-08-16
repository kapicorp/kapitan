---
comments: true
tags:
  - community
---
# :kapitan-logo: **Kapitan** code

Many of our features come from contributions from external collaborators. Please help us improve **Kapitan** by extending it with your ideas, or help us squash bugs you discover.

It's simple, just send us a PR with your improvements!

## Submitting code

We would like ask you to [fork](https://help.github.com/en/articles/fork-a-repo)
Kapitan project and create a [Pull Request](https://help.github.com/articles/about-pull-requests/)
targeting master branch. All submissions, including submissions by project members, require review.

### Setup

We build Kapitan using `poetry` and provide a comprehensive Makefile for development tasks.

#### Quick Start

The easiest way to set up your development environment is using our Makefile:

```bash
# Complete development environment setup
make setup
```

This command will:
- Install Poetry package manager
- Install all Python dependencies (including dev, test, docs, and optional extras)
- Install external tools (kustomize and CUE)

#### Manual Setup

If you prefer to set up components individually:

1. **Install Poetry**

    ```bash
    make install_poetry
    # or manually:
    pip install poetry
    ```

2. **Install Python Dependencies**

    ```bash
    make install
    # or manually:
    poetry install --with dev --with test --with docs --extras "gojsonnet reclass-rs omegaconf"
    ```

3. **Install External Tools** (required for some tests)

    ```bash
    make install_external_tools
    # This installs:
    # - kustomize (Kubernetes manifest management)
    # - CUE (data validation and configuration)
    ```

4. **Initialize Git Submodules**

    Because we use a pinned version of reclass as a submodule:

    ```bash
    git submodule update --init
    ```

5. **Run Kapitan with your compiled code**

    ```bash
    poetry run kapitan <your command>
    ```

#### Makefile Commands Overview

Run `make help` to see all available commands:

- **Setup**: `make setup`, `make install`, `make install_poetry`
- **Development**: `make format`, `make lint`, `make test_quick`
- **Testing**: `make test`, `make test_python`, `make test_coverage`
- **Documentation**: `make docs_serve`, `make docs_deploy`

#### Troubleshooting

On macOS, ensure gcc is installed:

```bash
brew install gcc@5
```

### Testing

We provide several testing commands with different scopes:

#### Test Commands

- **`make test`** - Run the comprehensive test suite (includes linting, Python tests, Docker tests, coverage, and formatting checks)
- **`make test_quick`** - Run quick tests without Docker or external tools (ideal for rapid development)
- **`make test_python`** - Run only Python unit tests
- **`make test_coverage`** - Run tests with coverage reporting (minimum 65% required)
- **`make lint`** - Run code quality checks with ruff
- **`make check_format`** - Verify code formatting without making changes

#### Testing Guidelines

1. If you modify anything in the `examples/` folder, make sure you replicate the compiled result in `tests/test_kubernetes_compiled`.

2. When adding new features:
   - Run `make test_coverage` to ensure test coverage remains at current or better levels
   - Run `make format` to apply code formatting

3. To test your changes with your local Kapitan version:
   ```bash
   poetry run kapitan <your command>
   # or set an alias:
   alias kapitan='poetry run kapitan'
   ```

4. To run specific test files:
   ```bash
   poetry run pytest tests/test_vault_transit.py
   # or using unittest:
   python3 -m unittest tests/test_vault_transit.py
   ```

### Code Style

We use [Ruff](https://github.com/astral-sh/ruff) for both linting and formatting, which enforces the [Style Guide for Python (PEP8)](http://python.org/dev/peps/pep-0008/) and additional best practices.

#### Formatting Commands

- **`make format`** - Automatically format code and fix linting issues
- **`make lint`** - Check code quality without making changes
- **`make check_format`** - Verify formatting without making changes

#### Pre-commit Hooks

We use pre-commit hooks to automatically check code quality before commits:

1. Install pre-commit (included in dev dependencies):
   ```bash
   make install  # This includes pre-commit
   ```

2. Install the git hooks:
   ```bash
   pre-commit install
   ```

3. The hooks will now run automatically on `git commit`. To run manually:
   ```bash
   pre-commit run --all-files
   ```

#### Ruff Configuration

Our `ruff.toml` file contains comprehensive linting rules with priorities:
- **High Priority**: Critical issues that should be fixed immediately
- **Medium Priority**: Issues to fix during refactoring
- **Low Priority**: Style preferences that can be ignored

Run `make lint` to see current violations.

### Release process

* Create a branch named `release-v<NUMBER>`. Use `v0.*.*-rc.*` if you want pre-release versions to be uploaded.
* Update CHANGELOG.md with the release changes.
* Once reviewed and merged, Github Actions will auto-release.
* The merge has to happen with a merge commit not with squash/rebase so that the commit message still mentions `kapicorp/release-v*` inside.

### Packaging extra resources in python package

To package any extra resources/files in the pip package, make sure you modify both `MANIFEST.in`.

## Leave a comment
