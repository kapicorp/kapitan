# How to Contribute

We'd love to accept your patches and contributions to this project. There are
just a few small guidelines you need to follow.

## Submitting changes

We would like ask you to [fork](https://help.github.com/en/articles/fork-a-repo)
Kapitan project and create a [Pull Request](https://help.github.com/articles/about-pull-requests/)
targeting master branch. All submissions, including submissions by project members, require review.

## Setting up environment

We highly recommend that you create a dedicated Python environment for Kapitan.
There are multiple solutions:

- [pyenv](https://github.com/pyenv/pyenv)
- [virtualenv](https://virtualenv.pypa.io/en/latest/)
- [venv](https://docs.python.org/3/library/venv.html)

Once you've done it, please install all Kapitan's dependencies:

```shell
pip3 install -r requirements.txt
```

Because we are using a pinned version of reclass which is added as a submodule into Kapitan's
repository, you need to pull it separately by executing the command below:

```shell
git submodule update --init
```

## Testing

Run `make test` to run all tests. If you modify anything in the `examples/` folder
make sure you replicate the compiled result of that in `tests/test_kubernetes_compiled`.
If you add new features, run `make test_coverage` to make sure the test coverage remains
at current or better levels.

If you would like to evaluate your changes by running your version of Kapitan, you can do
that by running `bin/kapitan` from this repository or even setting an alias to it.

## Code Style

Try to fix warnings from `make codestyle` before submitting to make sure you adhere to the
[Style Guide for Python (PEP8)](http://python.org/dev/peps/pep-0008/).

## Releasing

- Create a branch named `release-v<NUMBER>`. Use `v0.*.*-rc.*` if you want pre-release versions to be uploaded.
- Update CHANGELOG.md with the release changes.
- Once reviewed and merged, Travis will auto-release.
- The merge has to happen with a merge commit not with squash/rebase so that the commit message still mentions `deepmind/release-v*` inside.

## Updating gh-pages docs

We use [mkdocs](https://www.mkdocs.org/) to generate our gh-pages from `.md` files under docs/ folder.

Updating our gh-pages is therefore a two-step process.

### 1. Update the `.md` files

Submit a PR for our master branch that updates the `.md` file(s). Test how the changes would look like when deployed to gh-pages by serving it on localhost:

```
# from project root
pip install mkdocs mkdocs-material pymdown-extensions markdown-include
mkdocs build
mkdocs serve
# open http://127.0.0.1:8000
```

### 2. Submit a PR for gh-pages branch to deploy the update

Once the above PR has been merged, use `mkdocs gh-deploy` command to create and push a branch in your fork with the generated site content:

```
# locally, on master branch (which has your updated docs)
mkdocs gh-deploy -m "Commit message" -f ./mkdocs.yml -b remote_branch_name
```

After it's pushed, create a PR that targets our gh-pages branch.

## Contributor License Agreement

Contributions to this project must be accompanied by a Contributor License
Agreement. You (or your employer) retain the copyright to your contribution,
this simply gives us permission to use and redistribute your contributions as
part of the project. Head over to <https://cla.developers.google.com/> to see
your current agreements on file or to sign a new one.

You generally only need to submit a CLA once, so if you've already submitted one
(even if it was for a different project), you probably don't need to do it
again.
