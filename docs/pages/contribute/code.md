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

We build Kapitan using `uv` (for Python deps) and `mise` (for external toolchain), and provide a comprehensive Makefile for development tasks.

#### Quick Start

The easiest way to set up your development environment is using our Makefile:

```bash
# Complete development environment setup
make setup
```

This command will:
- Install pinned toolchain via `mise` (`uv`, Helm, Kustomize, CUE)
- Install all Python dependencies (including dev, test, docs, and optional extras)
- Configure pre-commit hooks

#### Manual Setup

If you prefer to set up components individually:

1. **Install `mise`**

    Follow the official installation instructions for your platform and shell:
    <https://mise.jdx.dev/getting-started.html#installing-mise-cli>

2. **Install Toolchain**

    ```bash
    make install_tools
    # or manually:
    mise install --locked
    ```

3. **Install Python Dependencies**

    ```bash
    make install
    # or manually:
    mise exec -- uv sync --locked --all-extras --dev
    ```

4. **Initialize Git Submodules**

    Because we use a pinned version of reclass as a submodule:

    ```bash
    git submodule update --init
    ```

5. **Run Kapitan with your compiled code**

    ```bash
    mise exec -- uv run kapitan <your command>
    ```

#### Makefile Commands Overview

Run `make help` or simply `make` to see all available commands:

**Setup Commands:**
- `make setup` - Complete development environment setup (recommended for first-time setup)
- `make install` - Install Python dependencies
- `make install_tools` - Install all pinned tools from `mise.toml`
- `make install_pre_commit` - Configure git pre-commit hooks

**Development Commands:**
- `make format` - Format code with ruff
- `make lint` - Run code quality checks on source code
- `make lint_tests` - Run code quality checks on tests
- `make lint_all` - Run code quality checks on everything
- `make fix` - Fix auto-fixable linting issues in source
- `make fix_tests` - Fix auto-fixable linting issues in tests

**Testing Commands:**
- `make tests_unit` - Run unit tests only, excluding `requires_network`
- `make tests_integration` - Run integration tests only, excluding `requires_network`
- `make tests` - Run the full Python test suite, excluding `requires_network`
- `make tests_network` - Run network-dependent tests explicitly
- `make test` - Run the full validation suite
- `make coverage_report` - Show the current coverage report
- `make build_docker` - Build and test the Docker image

**Documentation Commands:**
- `make docs_serve` - Serve documentation locally at `DOCS_DEV_ADDR` (default `localhost:8000`)
- `make docs_deploy` - Deploy documentation to GitHub Pages

**Other Commands:**
- `make clean` - Clean build artifacts and cache directories
- `make package` - Build Python packages
- `make release version=X.Y.Z` - Create a new release

#### Troubleshooting

On macOS, ensure gcc is installed:

```bash
brew install gcc@5
```

### Testing

We provide several testing commands with different scopes to support various development workflows.

#### Quick Development Workflow

For rapid development iteration:
```bash
make tests_unit  # Fast feedback for unit-only changes
```

#### Comprehensive Testing

Before submitting a PR:
```bash
make test  # Full test suite including Docker tests
```

#### Individual Test Commands

- `make tests_unit` - Run unit tests only, excluding `requires_network`
- `make tests_integration` - Run integration tests only, excluding `requires_network`
- `make tests` - Run the full Python test suite, excluding `requires_network`
- `make tests_network` - Run network-dependent tests explicitly
- `make coverage_report` - Show the current coverage report
- `make build_docker` - Build and test the Docker image
- `make lint_all` - Check both source and test code quality
- `make check_format` - Verify code formatting

#### Testing Guidelines

1. If you modify anything in the `examples/` folder, make sure you replicate the compiled result in `tests/test_kubernetes_compiled`.

2. When adding new features:
   - Run `make tests` and `make coverage_report` to ensure test coverage remains at current or better levels
   - Run `make format` to apply code formatting

3. To test your changes with your local Kapitan version:
   ```bash
   mise exec -- uv run kapitan <your command>
   # or set an alias:
   alias kapitan='mise exec -- uv run kapitan'
   ```

4. To run specific test files:
   ```bash
   mise exec -- uv run pytest --no-cov tests/unit/kapitan/refs/secrets/test_vaulttransit.py
   ```

### Code Style

We use [Ruff](https://github.com/astral-sh/ruff) for both linting and formatting, which enforces the [Style Guide for Python (PEP8)](http://python.org/dev/peps/pep-0008/) and additional best practices.

#### Code Quality Commands

**Checking Code:**
- `make lint` - Check source code for quality issues
- `make lint_tests` - Check test files for quality issues
- `make lint_all` - Check everything (source + tests)
- `make check_format` - Verify code formatting

**Fixing Code:**
- `make format` - Format code with ruff formatter
- `make fix` - Auto-fix linting issues in source code
- `make fix_tests` - Auto-fix linting issues in tests

#### Pre-commit Hooks

We use pre-commit hooks to automatically check code quality before commits. These are automatically configured when you run `make setup`.

**Manual Setup:**
If you didn't use `make setup`, you can configure pre-commit hooks manually:

```bash
make install_pre_commit
# or directly:
mise exec -- uv run pre-commit install
```

**Usage:**
- Hooks run automatically on `git commit`
- To run manually: `mise exec -- uv run pre-commit run --all-files`
- To skip hooks temporarily: `git commit --no-verify`

The pre-commit configuration includes:
- **Ruff**: Code linting and auto-fixing
- **Ruff-format**: Code formatting
- **End-of-file-fixer**: Ensures files end with a newline
- **Check-merge-conflict**: Prevents committing merge conflict markers

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
