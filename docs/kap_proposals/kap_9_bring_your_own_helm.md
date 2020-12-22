# Bring Your Own Helm Proposal

## The Problem

Currently the helm binding can't be run on Mac OSX. Attempts to fix this have been made on several occasions:
- https://github.com/deepmind/kapitan/pull/414
- https://github.com/deepmind/kapitan/pull/547
- https://github.com/deepmind/kapitan/pull/568

There are some issues with the current bindings besides the lack of Mac OSX support. The golang runtime (1.14) selected will effect older versions helm templates: https://github.com/helm/helm/issues/7711. Users can't select the version of helm they'd like to use for templating.

## Solution

Users supply their own helm binary. This allows them to control the version of golang runtime and version of helm they'd like to use.

In Kapitan we could rewrite the interface to use [subprocess](https://docs.python.org/3/library/subprocess.html) and perform commands. The cli of helm 2 vs helm 3 is slightly different but shouldn't be difficult to codify.

This would be great to get rid of cffi and golang which will reduce complexity and build time of the project.

Depending on how this goes, this could pave the way for a "bring your own binary" input type.