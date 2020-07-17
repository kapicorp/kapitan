#  macOS release

This task can be divided into 3 parts.

- Complete the Helm binding pipeline so that TravisCI also builds binding for osx and releases them to GitHub release.

- Packaging the binding to the pypi release.

- Add a brew formula for kapitan

## 1. Helm binding pipeline
Build 2 separate versions of shared object (.so) file depending on the platform.
This can be achieved as Travis supports builds on multiple platforms.

## 2. PYPI packaging
The packaging can be incorporated in the travis pipeline by adding a ​travis_wait​ argument ​to the ​`.travis.yml`​ file so that the packaging happens after the build. Users can then simply install kapitan using pip which installs wheels compatible with the running platform.

## 3. Brew packaging
Create a formula for kapitan using `$ brew create <url>` and configure the formula using the [Formula API](https://rubydoc.brew.sh/Formula)

- Create and maintain a tap for the formula.
    * A tap has to be a GitHub repository starting with "Homebrew-"
    * We can either [https://github.com/deepmind] or [https://github.com/kapicorp] to host the tap
    * It has to be manually updated with PRs for every kapitan release

- This will enable the users to install kapitan on MacOS using the following commands:
```shell
$ brew tap kapicorp/kapitan
$ brew install kapitan
```

