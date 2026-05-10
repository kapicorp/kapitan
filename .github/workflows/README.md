# GitHub Actions Workflows

This directory contains GitHub Actions workflows for the Kapitan project.

## Workflows

### 1. Test, Build and Publish (`test-build-publish.yml`)
Main CI/CD workflow that:
- Runs pre-commit checks with cached environments
- Executes tests on Python 3.11, 3.12, 3.13 and 3.14 **in parallel** using pytest-xdist
- Generates comprehensive test coverage reports (XML, JSON, HTML)
- Provides detailed test metrics and performance analysis
- Posts coverage comments on pull requests
- Builds Docker images for linux/amd64 and linux/arm64
- Publishes Docker images to DockerHub (on master/main branch and releases)
- Attaches per-Python-version Docker image SBOMs to GitHub releases
- Uploads coverage to Codecov

**Key Features:**
- ✅ Parallel test execution with `-n auto` for faster CI
- ✅ Cached dependencies (uv, Helm, CUE, pre-commit)
- ✅ Coverage tracking with branch coverage enabled
- ✅ Test performance metrics and slowest test identification
- ✅ GitHub Actions summaries with coverage badges
- ✅ SBOM attached to every release (SPDX JSON, one per Python version)

### 2. Security Audit (`security-audit.yml`)
Supply-chain security workflow that runs on every PR, every push to main/master, every release, and weekly:
- **`pip-audit`**: scans the locked `uv.lock` dependency graph for known CVEs; fails the job on any unfixed vulnerability
- **`python-sbom`**: generates an SPDX JSON SBOM for the Python package using `anchore/sbom-action`; attaches the SBOM to GitHub releases as a download artifact

**Key Features:**
- ✅ Audits the exact locked dependency graph (not just declared ranges)
- ✅ SBOM uploaded as workflow artifact on every run
- ✅ SBOM attached to GitHub releases automatically
- ✅ Weekly scheduled scans catch newly-published CVEs between releases

### 3. Documentation (`documentation.yml`)
Builds and publishes documentation to GitHub Pages using MkDocs + mike for versioned docs.

### 4. Python Package Publishing (`python-pypi-publish.yml`)
Publishes Python packages to PyPI on release using `uv build` + Twine.

### 5. PEX Build and Upload (`pex-build-upload.yml`)
Builds standalone PEX executables for distribution and attaches them to GitHub releases.

### 6. Development Environment Setup Test (`makefile-test.yml`)
Validates that all `make` setup targets (`install_uv`, `install`, `install_external_tools`, `install_pre_commit`, `setup`) work correctly. Triggers only when Makefile, pyproject.toml, uv.lock, or related config files change.

### 7. Housekeeping (`housekeeping.yml`)
Daily automated maintenance: marks GitHub issues as stale after 1 year of inactivity.

## Digest Pinning

All GitHub Actions `uses:` references in this directory are pinned to a commit SHA (with the version tag in a comment, e.g. `# v6.0.2`). Dockerfile base images are similarly pinned to a specific version tag.

Automated updates are managed by **Renovate** (`.github/renovate.json`):
- GitHub Actions digests are grouped into a single "GitHub Actions" PR
- Dockerfile base images are grouped into a single "Dockerfile base images" PR
- Python dependency updates from `uv.lock` appear as "Python dependencies (uv)" PRs

## Test Coverage

The project uses comprehensive coverage tracking integrated into the main workflow:

### Coverage Providers
- **Codecov**: Primary coverage tracking with PR comments
- **GitHub Actions Artifacts**: Coverage reports stored as artifacts
- **Job Summaries**: Coverage displayed in GitHub Actions UI with badges
- **PR Comments**: Automatic coverage analysis via py-cov-action

### Coverage Metrics
- **Overall Coverage**: Target 70% for the project
- **Patch Coverage**: Target 80% for new/modified code
- **Branch Coverage**: Enabled for comprehensive testing

- **Parallel Coverage**: Properly configured for pytest-xdist with `COVERAGE_CORE=sysmon`

### Coverage Reports
- `coverage.xml`: Machine-readable XML format
- `coverage.json`: JSON format with detailed metrics
- `htmlcov/`: Interactive HTML coverage reports
- `junit.xml`: JUnit test results for visualization

## Test Statistics

### Visualizations
- **Test Results**: Pass/fail/skip counts
- **Duration Tracking**: Total and per-test timing
- **Slowest Tests**: Top 10 slowest tests highlighted
- **Parallel Execution**: Performance comparison

### Report Formats
- **JUnit XML**: Standard test result format
- **JSON Reports**: Detailed test metadata
- **GitHub Summaries**: Markdown summaries in PR/workflow UI

## Running Tests Locally

### Basic Test Run
```bash
uv run pytest
```

### With Coverage
```bash
uv run pytest --cov=kapitan --cov-report=html --cov-report=term
```

### Parallel Execution (Recommended)
```bash
# Use all available CPU cores
uv run pytest -n auto

# With coverage in parallel
uv run pytest -n auto --cov=kapitan --cov-branch
```

### Generate All Reports (CI-style)
```bash
# Clean previous coverage data
rm -f .coverage* coverage.xml coverage.json

# Run tests with parallel execution and coverage
# Note: Direct report generation is more reliable with pytest-xdist
uv run pytest \
  -n auto \
  --cov=kapitan \
  --cov-branch \
  --cov-report=term-missing \
  --cov-report=xml:coverage.xml \
  --cov-report=json:coverage.json \
  --cov-report=html:htmlcov \
  --junit-xml=junit.xml \
  --json-report \
  --json-report-file=test-results.json \
  --durations=20 \
  -v
```

## Configuration Files

### `codecov.yml`
Configures Codecov integration:
- Coverage targets and thresholds
- Comment behavior on PRs
- Files to ignore

### `pyproject.toml`
Contains pytest and coverage configuration:
- Test discovery patterns
- Coverage source and omit patterns
- Report settings

## Badges

Add these badges to your README:

```markdown
[![codecov](https://codecov.io/gh/kapicorp/kapitan/branch/master/graph/badge.svg)](https://codecov.io/gh/kapicorp/kapitan)
[![Tests](https://github.com/kapicorp/kapitan/actions/workflows/test-build-publish.yml/badge.svg)](https://github.com/kapicorp/kapitan/actions/workflows/test-build-publish.yml)
```

## Environment Variables

### Required Secrets
- `CODECOV_TOKEN`: Token for Codecov integration
- `DOCKERHUB_USERNAME`: DockerHub username
- `DOCKERHUB_TOKEN`: DockerHub access token

### Optional Variables
- `DOCKERHUB_REPOSITORY`: Custom DockerHub repository

## Troubleshooting

### Coverage Not Updating
1. Check if `CODECOV_TOKEN` is set in repository secrets
2. Verify coverage files are generated correctly
3. Check Codecov webhook status
4. Ensure `COVERAGE_CORE=sysmon` is set for parallel tests

### Tests Failing in CI but Passing Locally
1. Check for missing system dependencies (Helm, CUE)
2. Verify test isolation (no shared state)
3. Check for race conditions in parallel tests
4. Ensure paths are relative, not absolute (e.g., GPG key paths)

### Parallel Test Issues
1. Coverage data combination errors: Ensure branch coverage is consistent
2. Set `COVERAGE_CORE=sysmon` environment variable
3. Use `--cov-report=` and combine manually if needed
4. Check `concurrency` setting in pyproject.toml

### Slow Test Execution
1. Use parallel execution with `-n auto` (already enabled in CI)
2. Check cache hit rates in GitHub Actions logs
3. Consider marking slow tests with `@pytest.mark.slow`
4. Review test fixtures for unnecessary setup

### Cache Issues
1. Check cache keys in workflow logs
2. Clear caches from Settings → Actions → Caches if corrupted
3. Update cache keys when dependencies change significantly
