# GitHub Actions Workflows

This directory contains GitHub Actions workflows for the Kapitan project.

## Workflows

### 1. Test, Build and Publish (`test-build-publish.yml`)
Main CI/CD workflow that:
- Runs pre-commit checks
- Executes tests on Python 3.10, 3.11, and 3.12
- Generates test coverage reports
- Builds Docker images for linux/amd64 and linux/arm64
- Publishes Docker images to DockerHub (on master/main branch)
- Uploads coverage to Codecov

### 2. Test Coverage and Analysis (`test-coverage.yml`)
Enhanced testing workflow with detailed coverage analysis:
- **Coverage Reports**: XML, JSON, and HTML formats
- **Test Metrics**:
  - Pass/fail statistics
  - Test duration tracking
  - Slowest tests identification
- **Parallel Testing**: Validates tests can run concurrently
- **PR Comments**: Automatic coverage comments on pull requests
- **Job Summaries**: Detailed summaries in GitHub UI

### 3. Documentation (`documentation.yml`)
Builds and publishes documentation to GitHub Pages.

### 4. Python Package Publishing (`python-pip-publish.yml`)
Publishes Python packages to PyPI on release.

### 5. PEX Build and Upload (`pex-build-upload.yml`)
Builds standalone PEX executables for distribution.

### 6. Housekeeping (`housekeeping.yml`)
Automated maintenance tasks like dependency updates.

## Test Coverage

The project uses multiple coverage tracking mechanisms:

### Coverage Providers
- **Codecov**: Primary coverage tracking with PR comments
- **GitHub Actions Artifacts**: Coverage reports stored as artifacts
- **Job Summaries**: Coverage displayed in GitHub Actions UI

### Coverage Metrics
- **Overall Coverage**: Target 70% for the project
- **Patch Coverage**: Target 80% for new/modified code
- **Branch Coverage**: Enabled for comprehensive testing

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
poetry run pytest tests/
```

### With Coverage
```bash
poetry run pytest tests/ --cov=kapitan --cov-report=html --cov-report=term
```

### Parallel Execution
```bash
poetry run pytest tests/ -n auto
```

### Generate Reports
```bash
# Generate all report types
poetry run pytest tests/ \
  --cov=kapitan \
  --cov-report=xml \
  --cov-report=html \
  --cov-report=json \
  --junit-xml=junit.xml \
  --durations=20
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
[![Coverage](https://github.com/kapicorp/kapitan/actions/workflows/test-coverage.yml/badge.svg)](https://github.com/kapicorp/kapitan/actions/workflows/test-coverage.yml)
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

### Tests Failing in CI but Passing Locally
1. Check for missing system dependencies
2. Verify test isolation (no shared state)
3. Check for race conditions in parallel tests

### Slow Test Execution
1. Use parallel execution with `-n auto`
2. Check for expensive test fixtures
3. Consider marking slow tests with `@pytest.mark.slow`
