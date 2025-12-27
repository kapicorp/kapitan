# Testing Best Practices for Kapitan

## Overview

This document describes best practices for writing tests in the Kapitan project to ensure they can run reliably in parallel and in any order.

## Key Problems Addressed

1. **Shared Directory Manipulation**: Tests were using `os.chdir()` to change to shared directories, causing conflicts when run in parallel
2. **In-place Compilation**: Tests were compiling to shared `compiled/` directories without isolation
3. **Order Dependencies**: Tests relied on side effects from previous tests
4. **Hardcoded Paths**: Tests used hardcoded paths that weren't portable

## Solution Architecture

### 1. Pytest Fixtures (`conftest.py`)

Created reusable pytest fixtures that provide isolated environments:

- `temp_dir`: Basic temporary directory with automatic cleanup
- `isolated_test_resources`: Isolated copy of test_resources directory
- `isolated_kubernetes_inventory`: Isolated copy of kubernetes example
- `isolated_terraform_inventory`: Isolated copy of terraform example
- `isolated_docker_inventory`: Isolated copy of docker example
- `refs_path`: Isolated refs directory for secret management
- `gnupg_home`: Isolated GNUPGHOME for GPG tests
- `reset_environment`: Auto-resets environment after each test

### 2. Test Helpers (`test_helpers.py`)

Created helper utilities for common test patterns:

- `CompileTestHelper`: Simplifies compilation testing with isolated environments
- `IsolatedTestEnvironment`: Context manager for test isolation
- `setup_gpg_key()`: Handles GPG key setup in isolated environment
- `create_test_inventory()`: Creates minimal test inventories
- `run_kapitan_command()`: Runs kapitan with captured output
- `assert_file_contains/not_contains()`: File content assertions

### 3. Refactored Tests (`test_compile.py`)

Demonstrates how to refactor existing tests to use the new patterns:

- Uses pytest fixtures instead of `setUp/tearDown`
- Each test gets its own isolated environment
- No shared state between tests
- Paths are computed dynamically, not hardcoded
- Tests can run in any order and in parallel

## Best Practices

### 1. Always Use Isolated Environments

**Bad:**
```python
from kapitan.cli import main as kapitan

def test_compile(self):
    os.chdir(TEST_RESOURCES_PATH)  # Shared directory!
    kapitan("compile")
```

**Good:**
```python
def test_compile(self, isolated_test_resources):
    helper = CompileTestHelper(isolated_test_resources)
    helper.compile_with_args(["compile"])
```

### 2. Never Rely on Test Order

**Bad:**
```python
def test_1_compile(self):
    # Compile and leave files for next test
    compile_target()

def test_2_verify(self):
    # Assumes test_1 ran first
    assert os.path.exists("compiled/output.json")
```

**Good:**
```python
def test_compile_and_verify(self, isolated_environment):
    helper = CompileTestHelper(isolated_environment)
    helper.compile_targets(["my-target"])
    assert helper.verify_compiled_output_exists("my-target/output.json")
```

### 3. Use Fixtures for Setup/Teardown

**Bad:**
```python
class TestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
```

**Good:**
```python
def test_something(self, temp_dir):
    # temp_dir is automatically created and cleaned up
    work_dir = os.path.join(temp_dir, "work")
```

### 4. Avoid Hardcoded Paths

**Bad:**
```python
reference_dir = os.path.join(os.getcwd(), "tests/test_compiled")
```

**Good:**
```python
original_cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
reference_dir = os.path.join(original_cwd, "tests/test_compiled")
```

### 5. Reset Cache Between Tests

Always call `reset_cache()` when setting up and tearing down test environments to ensure Kapitan's internal cache doesn't cause interference.

## Migration Guide

To migrate existing unittest-based tests to pytest:

1. **Replace Test Classes**:
   - Change `unittest.TestCase` to regular classes
   - Remove `setUp/tearDown` methods
   - Use pytest fixtures instead

2. **Update Assertions**:
   - Replace `self.assertEqual(a, b)` with `assert a == b`
   - Replace `self.assertTrue(x)` with `assert x`
   - Replace `self.assertRaises()` with `pytest.raises()`

3. **Use Fixtures**:
   - Replace manual temp directory creation with fixtures
   - Use `isolated_*` fixtures for inventory tests
   - Use helper classes for common operations

4. **Run Tests in Parallel**:
   ```bash
   # Install pytest-xdist
   pip install pytest-xdist

   # Run tests in parallel
   poetry run pytest -n auto
   ```

## Testing Checklist

Before committing test changes, ensure:

- [ ] Tests don't use `os.chdir()` to shared directories
- [ ] Tests don't modify shared resources
- [ ] Tests clean up after themselves (or use fixtures that do)
- [ ] Tests can run in any order
- [ ] Tests can run in parallel (`pytest -n auto`)
- [ ] Paths are computed dynamically, not hardcoded
- [ ] Cache is reset between test runs

## Running Tests

```bash
# Run all tests
poetry run pytest

# Run tests in parallel
poetry run pytest -n auto

# Run specific test class
poetry run pytest tests/test_compile_refactored.py::TestCompileResourcesObjs

# Run with verbose output
poetry run pytest -v

# Run with coverage
poetry run pytest --cov=kapitan
```

## Benefits

1. **Parallel Execution**: Tests run much faster with `-n auto`
2. **Reliability**: No more flaky tests due to shared state
3. **Isolation**: Each test runs in its own environment
4. **Maintainability**: Common patterns are extracted to helpers
5. **Debugging**: Easier to debug failing tests in isolation
