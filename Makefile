## Build and Package Commands
all: clean package

MISE ?= mise
UV ?= $(MISE) exec -- uv
UV_RUN ?= $(UV) run

################################################################################
# Setup and Installation
################################################################################

# Ensure mise runtime manager is installed
.PHONY: check_mise
check_mise:
	@command -v $(MISE) >/dev/null 2>&1 || { \
		echo "mise is not installed. Install it from https://mise.jdx.dev/getting-started.html"; \
		exit 1; \
	}

# Install all Python dependencies including dev, test, docs, and optional extras
.PHONY: install
install: install_tools
	@echo "===== Installing Python Dependencies ====="
	$(UV) sync --locked --all-extras --dev

# Install full development toolchain defined in mise.toml
.PHONY: install_tools
install_tools: check_mise
	@echo "===== Installing Development Toolchain via mise ====="
	@$(MISE) install --locked
	@$(MISE) exec -- uv --version
	@$(MISE) exec -- helm version --short
	@$(MISE) exec -- kustomize version
	@$(MISE) exec -- cue version

# Configure pre-commit git hooks (pre-commit package installed via uv)
.PHONY: install_pre_commit
install_pre_commit:
	@echo "===== Setting up Git Pre-commit Hooks ====="
	@$(UV_RUN) pre-commit install
	@echo "Pre-commit hooks configured successfully!"
	@echo "Hooks will run automatically on 'git commit'"
	@echo "To run manually: '$(UV_RUN) pre-commit run --all-files'"

# Complete development environment setup
.PHONY: setup
setup: install install_pre_commit
	@echo "===== Development Environment Ready ====="
	@echo "Run 'make test' to verify everything is working"

# Pytest command defaults (override from CLI, e.g. `make tests_unit PYTEST_JOBS=4 PYTEST_ARGS="--durations=20"`)
PYTEST ?= $(UV_RUN) pytest
PYTEST_JOBS ?= auto
PYTEST_ARGS ?=
# rand_uint32 from /dev/urandom
PYTEST_RANDOM_SEED ?= $(shell od -An -N4 -D /dev/urandom | tr -d ' ')
PYTEST_BASE := $(PYTEST) -n $(PYTEST_JOBS) --random-order-seed=$(PYTEST_RANDOM_SEED) $(PYTEST_ARGS)

################################################################################
# Code Quality and Testing
################################################################################

# Run code quality checks with ruff
.PHONY: lint
lint:
	@echo "===== Running Code Quality Checks ====="
	$(UV_RUN) ruff check kapitan

# Run code quality checks on test files
.PHONY: lint_tests
lint_tests:
	@echo "===== Running Code Quality Checks on Tests ====="
	$(UV_RUN) ruff check tests scripts

# Run code quality checks on everything
.PHONY: lint_all
lint_all: lint lint_tests
	@echo "===== All Code Quality Checks Complete ====="

# Fix auto-fixable linting issues
.PHONY: fix
fix:
	@echo "===== Fixing Auto-fixable Issues ====="
	$(UV_RUN) ruff check --fix kapitan
	@echo "Linting issues fixed!"

# Fix auto-fixable linting issues in tests
.PHONY: fix_tests
fix_tests:
	@echo "===== Fixing Auto-fixable Issues in Tests ====="
	$(UV_RUN) ruff check --fix tests scripts
	@echo "Test linting issues fixed!"

# Format code using ruff
.PHONY: format
format:
	@echo "===== Formatting Code ====="
	$(UV_RUN) ruff format .
	$(UV_RUN) ruff check --fix .
	@echo "Code formatting complete!"

# Check if code formatting is correct (used in CI)
.PHONY: check_format
check_format:
	@echo "===== Checking Code Formatting ====="
	$(UV_RUN) ruff format --check .

# Validate Docker daemon availability for Docker-backed tests
.PHONY: check_docker
check_docker:
	@command -v docker >/dev/null 2>&1 || { echo "docker is not installed."; exit 1; }
	@docker info >/dev/null 2>&1 || { echo "docker daemon is not running."; exit 1; }

# Run unit tests only, excluding network-dependent cases
.PHONY: tests_unit
tests_unit:
	@echo "===== Running Unit Tests (except requires_network) ====="
	$(PYTEST_BASE) tests/unit -m "not requires_network"

# Run integration tests only, excluding network-dependent cases
.PHONY: tests_integration
tests_integration:
	@echo "===== Running Integration Tests (except requires_network) ====="
	$(PYTEST_BASE) tests/integration -m "not requires_network"

# Run all tests, excluding network-dependent cases
.PHONY: tests
tests: check_docker
	@echo "===== Running Full Python Test Suite (except requires_network) ====="
	$(PYTEST_BASE) -m "not requires_network"

# Run network-dependent tests explicitly
.PHONY: tests_network
tests_network:
	@echo "===== Running Network-Dependent Tests ====="
	KAPITAN_ENABLE_NETWORK_TESTS=1 $(PYTEST_BASE) -m "requires_network"

# Run the full Python test suite, including network-dependent cases
.PHONY: test_python
test_python: setup lint check_format check_docker
	@echo "===== Running Full Python Test Suite ====="
	KAPITAN_ENABLE_NETWORK_TESTS=1 $(PYTEST_BASE)

# Build and test Docker image
.PHONY: build_docker
build_docker: check_docker
	@echo "===== Building Docker Image ====="
	docker pull kapicorp/kapitan:latest || true
	docker build . --cache-from kapicorp/kapitan:latest -t kapitan
	@echo "Docker image built successfully"
	@echo
	@echo "===== Testing Docker Image ====="
	docker run --rm kapitan --help
	docker run --rm kapitan lint
	@echo "Docker tests passed"

# Run the full test suite, including Docker image checks
.PHONY: test
test: test_python build_docker
	@echo "===== All Tests Passed! ====="

.PHONY: coverage_report
coverage_report:
	@echo "===== Running Coverage Report ====="
	$(UV_RUN) coverage report

################################################################################
# Release and Packaging
################################################################################

# Create a new release with specified version
.PHONY: release
release:
ifeq ($(version),)
	@echo "Please pass version to release e.g. make release version=0.16.5"
else
	scripts/inc_version.sh $(version)
endif

# Build Python package distributions
.PHONY: package
package:
	@echo "===== Building Python Package ====="
	python3 setup.py sdist bdist_wheel

# Clean all git ignored artifacts
.PHONY: clean
clean:
	@echo "===== Cleaning git ignored Artifacts ====="
	git clean -Xdf

################################################################################
# Documentation
################################################################################

# Mike development server address (override with `make docs_serve DOCS_DEV_ADDR=localhost:8001`)
DOCS_DEV_ADDR ?= localhost:8000

# Serve documentation locally for development
.PHONY: docs_serve
docs_serve:
	@echo "===== Serving Documentation Locally ====="
	@echo "Documentation will be available at http://$(DOCS_DEV_ADDR)"
	$(UV_RUN) mike deploy -u -b local/preview-docs dev master
	@git rev-parse --verify local/preview-docs:index.html >/dev/null 2>&1 || \
		$(UV_RUN) mike set-default -b local/preview-docs master
	$(UV_RUN) mike serve -b local/preview-docs -a $(DOCS_DEV_ADDR)

# Deploy documentation to GitHub Pages
.PHONY: docs_deploy
docs_deploy:
	@echo "===== Deploying Documentation to GitHub Pages ====="
	$(UV_RUN) mike deploy --push dev master
	$(UV_RUN) mike set-default --push master

################################################################################
# Help
################################################################################

# Display help information
.PHONY: help
help:
	@echo "Kapitan Development Makefile"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make setup              - Complete development environment setup"
	@echo "  make install            - Install Python dependencies"
	@echo "  make install_tools      - Install all pinned tools from mise.toml"
	@echo "  make install_pre_commit - Configure git pre-commit hooks"
	@echo ""
	@echo "Development Commands:"
	@echo "  make format             - Format code with ruff"
	@echo "  make lint               - Run code quality checks on source code"
	@echo "  make lint_tests         - Run code quality checks on tests"
	@echo "  make lint_all           - Run code quality checks on everything"
	@echo "  make fix                - Fix auto-fixable linting issues in source"
	@echo "  make fix_tests          - Fix auto-fixable linting issues in tests"
	@echo "  make tests_unit         - Run tests/unit only (except requires_network)"
	@echo "  make tests_integration  - Run tests/integration (except requires_network)"
	@echo "  make tests              - Run full Python test suite (except requires_network)"
	@echo "  make tests_network      - Run only network-dependent tests"
	@echo "  make test_python        - Run full Python test suite (no image build)"
	@echo "  make test               - Run full Kapitan test suite"
	@echo "  make coverage_report    - Run tests coverage report"
	@echo "  make build_docker       - Build and test Docker image"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs_serve         - Serve documentation locally"
	@echo "  make docs_deploy        - Deploy docs to GitHub Pages"
	@echo ""
	@echo "Release Commands:"
	@echo "  make release version=X.Y.Z - Create a new release"
	@echo "  make package            - Build Python packages"
	@echo "  make clean              - Clean build artifacts"
	@echo ""
	@echo "Run 'make setup' to get started with development"

# Set help as the default target when running just 'make'
.DEFAULT_GOAL := help

# Validate that required commands exist
.PHONY: validate_commands
validate_commands: check_mise
	@$(MISE) exec -- uv --version >/dev/null 2>&1 || { echo "uv is not installed. Run 'make install_tools' first."; exit 1; }
	@command -v git >/dev/null 2>&1 || { echo "git is not installed."; exit 1; }
	@echo "All required commands are available"
