# How to Contribute

We'd love to accept your patches and contributions to this project. There are
just a few small guidelines you need to follow.

## Testing

Run `make test` to run all tests. If you modify anything in the `examples/` folder
make sure you replicate the compiled result of that in `tests/test_kubernetes_compiled`.

## Code Style

Try to fix warnings from `make codestyle` before submitting to make sure you adhere to the
[Style Guide for Python (PEP8)](http://python.org/dev/peps/pep-0008/).

## Releasing

 - Create a branch named `release-v<NUMBER>`. Use `v0.*.*-rc.*` if you want pre-release versions to be uploaded.
 - Update CHANGELOG.md with the release changes.
 - Once reviewed and merged, Travis will auto-release.
 - The merge has to happen with a merge commit not with squash/rebase so that the commit message still mentions `deepmind/release-v*` inside.

## Contributor License Agreement

Contributions to this project must be accompanied by a Contributor License
Agreement. You (or your employer) retain the copyright to your contribution,
this simply gives us permission to use and redistribute your contributions as
part of the project. Head over to <https://cla.developers.google.com/> to see
your current agreements on file or to sign a new one.

You generally only need to submit a CLA once, so if you've already submitted one
(even if it was for a different project), you probably don't need to do it
again.

## Code reviews

All submissions, including submissions by project members, require review. We
use GitHub pull requests for this purpose. Consult
[GitHub Help](https://help.github.com/articles/about-pull-requests/) for more
information on using pull requests.
