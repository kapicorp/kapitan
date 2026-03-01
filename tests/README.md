# Kapitan tests

This directory is organized around one goal: keep the test suite fast,
deterministic, and easy to change while still enforcing strict correctness.

## What the current layout optimizes for

- `tests/unit/` mirrors the `kapitan/` package layout as closely as practical.
  When a production module changes, its focused tests should usually live in
  the matching path under `tests/unit/`.
- `tests/integration/` covers behavior that crosses module boundaries, depends
  on realistic fixture projects, or is easier to validate through the public
  surface than through isolated helpers.
- `tests/resources/` contains non-Python test data only. Treat it as read-only.
  Full fixture-project layout rules live in `tests/resources/README.md`.
- `tests/support/` contains shared test-only Python helpers, path constants,
  and lightweight infrastructure such as the local Vault test server.
- `tests/conftest.py` is the central place for cross-suite fixtures, marker
  registration, and isolation helpers.

The intent is to avoid a grab-bag test tree. Tests should be easy to find from
source paths, and shared assets should have one obvious home.

## Testing philosophy

### 1. Prefer deterministic tests

The suite is expected to run in randomized order and in parallel. Tests must
not rely on execution order, shared mutable global state, leftover files, or
leaked environment variables.

If a test needs setup, make it explicit through fixtures or helper functions.
If a test mutates fixture files, copy them to a temporary directory first.

### 2. Keep environment-coupled tests explicit

Some tests need Docker, network access, or external dependencies (tools like
Vault, Helm, GPG, etc). Those requirements should be visible in the test itself
through markers and fixtures, not implicit or "hidden" in the test setup.

This is why the default `make tests` lane excludes `requires_network`, while
`make tests_network` opts into those cases explicitly.

### 3. Unit tests should stay close to behavior, not implementation trivia

The unit tree mirrors source layout so refactors are easier to follow, but the
assertions should still focus on behavior and contracts. Helper-level tests are
fine when they protect important branching or error handling, but avoid testing
private structure unless that structure is the contract being stabilized by the
refactor.

### 4. Integration tests should justify their cost

Use integration tests when they validate real workflows, real fixture projects,
or boundaries between multiple subsystems. Do not move narrow logic checks into
integration tests just because fixtures already exist.

### 5. Coverage is strict on purpose

The test suite enforces `100%` coverage for `kapitan/`. That is intentionally
strict: it forces new branches, error paths, and refactors to carry their own
proof.

This does not mean chasing meaningless assertions. It means every production
branch introduced in a commit should have a clear test that explains why it
exists.

## Running tests

Common entry points:

```bash
# Unit tests only, excluding requires_network
make tests_unit

# Integration tests only, excluding requires_network
make tests_integration

# Full Python suite, excluding requires_network
make tests

# Network-only tests
make tests_network

# Full project validation: setup + lint + format + tests + docker
make test

# Coverage report after running pytest
make coverage_report
```

Useful overrides:

```bash
# Increase or reduce xdist workers
PYTEST_JOBS=4 make tests

# extra pytest flags, e.g. verbose and only run tests that match "inventory"
PYTEST_ARGS='-v -k inventory' make tests_unit

# Reproduce a randomized-order test run (useful after a failed test run)
PYTEST_RANDOM_SEED=123 make tests
```

For single-file debugging, it is often easier to bypass coverage and run pytest
against one file directly:

```bash
mise exec -- uv run pytest --no-cov tests/unit/kapitan/test_targets.py -q
```

## Markers and lanes

Markers are registered in `tests/conftest.py`.

Important ones:

- `requires_network`: excluded from the default Python lanes; run via
  `make tests_network`
- `requires_vault`: tests that need the local Vault test server
- `requires_gpg`, `requires_helm`, `requires_kustomize`, `requires_cue`: tests
  that depend on those tools being available
- `slow`: tests that are intentionally heavier than the normal fast path

Use markers to make requirements obvious. Do not rely on comments or tribal
knowledge.

## Adding or moving tests

When adding coverage for a module:

- prefer `tests/unit/...` in the matching source-mirrored path
- put shared filesystem fixtures under `tests/resources/`
- put reusable Python helpers under `tests/support/`
- keep fixture projects read-only and copy them into temp dirs before mutation
- make external requirements explicit with markers

When refactoring, update tests in the same commit that changes the behavior
they protect. A commit should be testable on its own whenever possible.
