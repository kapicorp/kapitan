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

We build kapitan using `poetry`.

1. Install poetry

    ```bash
    pip install poetry
    ```

2. Install dependencies

    ```bash
    poetry install --all-extras --with dev --with test --with docs
    ```

    Poetry creates a virtual environment with the required dependencies installed.

3. Run kapitan with the own compiled code

    ```bash
    poetry run kapitan <your command>
    ```

Because we are using a pinned version of reclass which is added as a submodule into Kapitan's
repository, you need to pull it separately by executing the command below:

```shell
git submodule update --init
```

#### Troubleshoot

Check if gcc is installed:

```shell
brew install gcc@5
```

### Testing

Run `make test` to run all tests. If you modify anything in the `examples/` folder
make sure you replicate the compiled result of that in `tests/test_kubernetes_compiled`.
If you add new features, run `make test_coverage && make test_formatting` to make sure the
test coverage remains at current or better levels and that code formatting is applied.

If you would like to evaluate your changes by running your version of Kapitan, you can do
that by running `bin/kapitan` from this repository or even setting an alias to it.

```shell
python3 -m unittest tests/test_vault_transit.py
```

### Code Style

To make sure you adhere to the [Style Guide for Python (PEP8)](http://python.org/dev/peps/pep-0008/)
Python Black is used to apply the formatting so make sure you have it installed with `pip3 install black`.

#### Apply via Git hook

* Run `pip3 install pre-commit` to install precommit framework.
* In the Kapitan root directory, run `pre-commit install`
* Git add/commit any changed files you want.

#### Apply manually

Run `make format_codestyle` before submitting.

### Release process

* Create a branch named `release-v<NUMBER>`. Use `v0.*.*-rc.*` if you want pre-release versions to be uploaded.
* Update CHANGELOG.md with the release changes.
* Once reviewed and merged, Github Actions will auto-release.
* The merge has to happen with a merge commit not with squash/rebase so that the commit message still mentions `kapicorp/release-v*` inside.

### Packaging extra resources in python package

To package any extra resources/files in the pip package, make sure you modify both `MANIFEST.in`.

## Leave a comment
