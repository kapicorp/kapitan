# Contributing to Kapitan

Thanks for your interest in contributing. This document covers bugs, features, documentation, and code contributions.

## Quick orientation

- **Questions** → [`#kapitan`](https://kubernetes.slack.com/archives/C981W2HD3) on Kubernetes Slack or [GitHub Discussions](https://github.com/kapicorp/kapitan/discussions)
- **Bug reports** → [Open an issue](https://github.com/kapicorp/kapitan/issues/new?template=bug_report.yml)
- **Feature requests** → [Open an issue](https://github.com/kapicorp/kapitan/issues/new?template=feature_request.yml)
- **Documentation fixes** → [Open an issue](https://github.com/kapicorp/kapitan/issues/new?template=documentation.yml) or send a PR directly
- **Security issues** → See [SECURITY.md](SECURITY.md)

## Development setup

Kapitan uses **uv** for dependency management and **make** for task orchestration.

```shell
# Full setup (dependencies, external tools, pre-commit)
make setup

# Install only Python dependencies
make install
```

## Running tests

```shell
# Run all tests with coverage
uv run pytest -n auto

# Run a specific test file
uv run pytest tests/test_compile.py

# Run a specific test class or method
uv run pytest tests/test_class_wildcards.py::DiscoverClassesTest::test_discovers_yml_and_yaml

# Skip slow tests
uv run pytest -m "not slow"
```

Before declaring a feature or fix done, run both the focused subset **and** the full suite:

```shell
uv run pytest tests/ --no-cov
```

## Code style

We use **Ruff** for linting and formatting. Target Python version is 3.10. Line length is 88.

```shell
# Check and auto-fix
make fix
make fix-tests

# Verify formatting
make check_format
```

Pre-commit hooks run on commit. If a hook fails, fix the issue and commit again.

## Submitting a pull request

1. Branch from `master`.
2. Make focused, reviewable changes.
3. Add or update tests for code changes.
4. Update documentation if user-facing behavior changes.
5. Ensure `make format` and `make lint` pass.
6. Open a PR using the provided template.

## Testing unmerged changes on `next`

The `next` branch is `master` plus every open pull request labelled `next` whose
author has write access, merged in PR number order. The `next` workflow rebuilds
it every 15 minutes when `master` or one of those PRs changed, and, once the
inventory and compile tests pass on it, publishes:

- the image `ghcr.io/kapicorp/kapitan:next`, and `next-<commit>` for pinning;
- the wheel as the workflow artifact `kapitan-next-wheel`.

The issue titled "next: integration status" is updated on every rebuild. It
lists the PRs in `next` with the head commit that was merged, the PRs left out
because they conflict with `master` or an earlier PR, the image digest and the
test result.

A fork can build its own `next` from kapicorp/kapitan without waiting for a
label: set the repository variables `NEXT_SOURCE` to `kapicorp/kapitan` and
`NEXT_AUTHOR` to the login whose open PRs to merge, optionally
`NEXT_GREEN_AUTHORS` to logins such as `dependabot[bot]` whose PRs are merged
once all their checks passed, install a GitHub App with
Contents and Workflows write access on the fork and store its client ID in the
variable `NEXT_APP_CLIENT_ID` and its private key in the secret
`NEXT_APP_PRIVATE_KEY`, enable issues, and make
`next` the fork's default branch so the schedule runs. The image then goes to
`ghcr.io/<owner>/kapitan`.

`next` contains changes nobody has reviewed yet. Use it to test PRs together
before they are merged, not in production. Only PRs whose author has write
access are taken, whoever set the label, because later pushes to a labelled PR
reach `next` without another review.

## What we value

- Accuracy over marketing: do not exaggerate capabilities.
- Concrete examples over generic descriptions.
- Small, reviewable PRs over monolithic changes.
- Tests that hit real behavior over mocks where possible.

## Maintainers

Current maintainers are listed in [MAINTAINERS.md](MAINTAINERS.md).
