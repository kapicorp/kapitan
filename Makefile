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

# Install external tools required for testing (kustomize, cue)
.PHONY: install_external_tools
install_external_tools: install_kustomize install_cue
	@echo "===== All External Tools Installed ====="

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

# Complete development environment setup
.PHONY: setup
setup: install_poetry install install_external_tools
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

# Run Python unit tests
.PHONY: test_python
test_python:
	@echo "===== Running Python Tests ====="
	poetry run pytest

# Run tests with coverage reporting
.PHONY: test_coverage
test_coverage:
	@echo "===== Running Tests with Coverage ====="
	poetry run coverage run --source=kapitan -m pytest
	poetry run coverage report --fail-under=65 -m

# Build and test Docker image
.PHONY: test_docker
test_docker:
	@echo "===== Testing Docker Image ====="
	docker build . --no-cache -t kapitan
	@echo "----- Testing Docker image functionality -----"
	docker run -ti --rm kapitan --help
	docker run -ti --rm kapitan lint

# Run all tests (comprehensive test suite)
.PHONY: test
test: install install_external_tools lint test_python test_docker test_coverage check_format
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

# Clean build artifacts
.PHONY: clean
clean:
	@echo "===== Cleaning Build Artifacts ====="
	rm -rf dist/ build/ kapitan.egg-info/ bindist/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true

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
	@echo "  make install_external_tools - Install kustomize and CUE"
	@echo ""
	@echo "Development Commands:"
	@echo "  make format             - Format code with ruff"
	@echo "  make lint               - Run code quality checks"
	@echo "  make test_quick         - Run quick tests (no Docker)"
	@echo "  make test_python        - Run Python unit tests"
	@echo "  make test               - Run comprehensive test suite"
	@echo "  make test_coverage      - Run tests with coverage report"
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
