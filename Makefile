## Build and Package Commands
all: clean package

################################################################################
# Setup and Installation
################################################################################

# Install poetry package manager using pipx
.PHONY: install_poetry
install_poetry:
	@echo "===== Installing Poetry Package Manager ====="
	@which poetry > /dev/null 2>&1 || pipx install poetry
	@poetry --version

# Install all Python dependencies including dev, test, docs, and optional extras
.PHONY: install
install:
	@echo "===== Installing Python Dependencies ====="
	poetry install --with dev --with docs --with test --extras "gojsonnet reclass-rs omegaconf"

# Install external tools required for testing (helm, kustomize, cue)
.PHONY: install_external_tools
install_external_tools: install_helm install_kustomize install_cue
	@echo "===== All External Tools Installed ====="

# Install Helm for Kubernetes package management
.PHONY: install_helm
install_helm:
	@echo "===== Installing Helm ====="
	@which helm > /dev/null 2>&1 || ( \
		curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash \
	)
	@helm version --short

# Install kustomize for Kubernetes manifest management
.PHONY: install_kustomize
install_kustomize:
	@echo "===== Installing Kustomize ====="
	@which kustomize > /dev/null 2>&1 || ( \
		curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash && \
		sudo mv kustomize /usr/local/bin/ \
	)
	@kustomize version

# Install CUE language for data validation and configuration
.PHONY: install_cue
install_cue:
	@echo "===== Installing CUE Language ====="
	@which cue > /dev/null 2>&1 || ( \
		CUE_VERSION=$$(curl -s "https://api.github.com/repos/cue-lang/cue/releases/latest" | grep -Po '"tag_name": "\K.*?(?=")') && \
		curl -L "https://github.com/cue-lang/cue/releases/download/$${CUE_VERSION}/cue_$${CUE_VERSION}_linux_amd64.tar.gz" | \
		sudo tar xz -C /usr/local/bin cue \
	)
	@cue version

# Configure pre-commit git hooks (pre-commit package installed via poetry)
.PHONY: install_pre_commit
install_pre_commit:
	@echo "===== Setting up Git Pre-commit Hooks ====="
	@poetry run pre-commit install
	@echo "Pre-commit hooks configured successfully!"
	@echo "Hooks will run automatically on 'git commit'"
	@echo "To run manually: 'poetry run pre-commit run --all-files'"

# Complete development environment setup
.PHONY: setup
setup: install_poetry install install_external_tools install_pre_commit
	@echo "===== Development Environment Ready ====="
	@echo "Run 'make test' to verify everything is working"

################################################################################
# Code Quality and Testing
################################################################################

# Run code quality checks with ruff
.PHONY: lint
lint:
	@echo "===== Running Code Quality Checks ====="
	poetry run ruff check kapitan

# Run code quality checks on test files
.PHONY: lint-tests
lint-tests:
	@echo "===== Running Code Quality Checks on Tests ====="
	poetry run ruff check tests scripts

# Run code quality checks on everything
.PHONY: lint-all
lint-all: lint lint-tests
	@echo "===== All Code Quality Checks Complete ====="

# Fix auto-fixable linting issues
.PHONY: fix
fix:
	@echo "===== Fixing Auto-fixable Issues ====="
	poetry run ruff check --fix kapitan
	@echo "Linting issues fixed!"

# Fix auto-fixable linting issues in tests
.PHONY: fix-tests
fix-tests:
	@echo "===== Fixing Auto-fixable Issues in Tests ====="
	poetry run ruff check --fix tests scripts
	@echo "Test linting issues fixed!"

# Format code using ruff
.PHONY: format
format:
	@echo "===== Formatting Code ====="
	poetry run ruff format .
	poetry run ruff check --fix .
	@echo "Code formatting complete!"

# Check if code formatting is correct (used in CI)
.PHONY: check_format
check_format:
	@echo "===== Checking Code Formatting ====="
	poetry run ruff format --check .

# Run Python unit tests with coverage
.PHONY: test_python
test_python:
	@echo "===== Running Python Tests with coverage ====="
	poetry run pytest -n auto

# Run tests coverage report
.PHONY: test_coverage
test_coverage: test_python
	@echo "===== Running Coverage Report ====="
	poetry run coverage report

# Build Docker image
.PHONY: build_docker
build_docker:
	@echo "===== Building Docker Image ====="
	docker pull kapicorp/kapitan:latest || true
	docker build . --cache-from kapicorp/kapitan:latest -t kapitan
	@echo "Docker image built successfully"

# Test Docker image
.PHONY: test_docker
test_docker: build_docker
	@echo "===== Testing Docker Image ====="
	docker run --rm kapitan --help
	docker run --rm kapitan lint
	@echo "Docker tests passed"

# Run all tests (comprehensive test suite)
.PHONY: test
test: install install_external_tools lint test_coverage test_docker check_format
	@echo "===== All Tests Passed! ====="

# Quick test without Docker or external tools
.PHONY: test_quick
test_quick: lint test_python check_format
	@echo "===== Quick Tests Passed! ====="

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

# Serve documentation locally for development
.PHONY: docs_serve
docs_serve:
	@echo "===== Serving Documentation Locally ====="
	@echo "Documentation will be available at http://localhost:8000"
	poetry run mike serve

# Deploy documentation to GitHub Pages
.PHONY: docs_deploy
docs_deploy:
	@echo "===== Deploying Documentation to GitHub Pages ====="
	poetry run mike deploy --push dev master

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
	@echo "  make install_poetry     - Install Poetry package manager"
	@echo "  make install_external_tools - Install Helm, Kustomize, and CUE"
	@echo "  make install_pre_commit - Configure git pre-commit hooks"
	@echo ""
	@echo "Development Commands:"
	@echo "  make format             - Format code with ruff"
	@echo "  make lint               - Run code quality checks on source code"
	@echo "  make lint-tests         - Run code quality checks on tests"
	@echo "  make lint-all           - Run code quality checks on everything"
	@echo "  make fix                - Fix auto-fixable linting issues in source"
	@echo "  make fix-tests          - Fix auto-fixable linting issues in tests"
	@echo "  make test_quick         - Run quick tests (no Docker)"
	@echo "  make test_python        - Run Python unit tests with coverage"
	@echo "  make test               - Run comprehensive test suite"
	@echo "  make test_coverage      - Run tests coverage report"
	@echo "  make build_docker       - Build Docker image"
	@echo "  make test_docker        - Build and test Docker image"
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
.PHONY: validate-commands
validate-commands:
	@command -v poetry >/dev/null 2>&1 || { echo "poetry is not installed. Run 'make install_poetry' first."; exit 1; }
	@command -v git >/dev/null 2>&1 || { echo "git is not installed."; exit 1; }
	@echo "All required commands are available"
