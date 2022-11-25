# Google Summer of Code project ideas

Here are some project ideas for GSoC 2020

## 1. Remote Inventory Federation

Description: This work would add the ability to Kapitan to fetch parts of the Inventory from remote locations (https/git). This would allow users to combine different inventories from different sources and build modular infrastructure reusable across various repos.

Fetching of the inventory would have to happen before compiling the inventory with reclass, as a separate/initial step.
What is still to be defined is how users would declare their remote inventories (maybe in .kapitan ?) and where those files will be saved locally. Putting that config in the inventory makes parsing it before reclass cumbersome so ideally it would be in a separate location.

Expected Outcome: The feature is implemented and works, tests are added that also fetch inventories from remote locations and documentation for the feature is updated.
Skills required: Python, coding, minor automation for our tests/CI/CD.
Difficulty: Medium

## 2. Follow up on helm OSX Bindings

Description: This would be a followup project from last years GSoC to complete the helm bindings pipelines so they also build bindings for OSX. <https://github.com/kapicorp/kapitan/pull/359> Along with the bindings, it should be possible/fairly easy to also compile the binary of Kapitan for OSX with the bindings prebaked in it.

Expected Outcome: The pip python package for Kapitan ships with pre-included OSX helm bindings. Documentation is updated and the build is implemented in a way that runs automatically and doesn't require a lot of human time. Along with this, the student would also ship the OSX binary of Kapitan in the github releases page.
As a bonus, this work could also add a brew manifest for OSX so that users there can install Kapitan in a simpler way.

Skills required: Some python/Go for the bindings, DevOps/scripting skills to automate the pipelines
Difficulty: Hard

## 3. Modularize Kapitan

Description: Currently kapitan is packaged in pypi (or as a binary) along with all its dependencies. Adding an extra key/security backend means that we need to ship another dependency with that pypi package which in turn makes deploying changes more complicated.

Adding more input types or secret backends means adding extra dependencies which might not be useful or acceptable for certain users (due to license?).
This project would be about modularizing of kapitan to a set of core dependencies (cryptography,pyyaml,jsonschema etc) and then extra modules (e.g. boto3,google-api-python-client) that can be loaded by users that actually use those specific features.
<https://docs.python.org/3/library/imp.html> might be one of the ways to do that.

Expected Outcome: The pypi Kapitan package now contains the minimum set of dependencies and the pipelines on Github build extra packages with any extended functionality like (AWS Key backend, Google KMS Key Backend, Vault Key backend etc)
Skills required: Python, understanding packaging/modularization, some scripting for automating the pipelines
Difficulty: Medium

## 4. Implement Azure KMS and Vault KMS backends

Description: Currently there is a PR to add Azure KMS support to Kapitan <https://github.com/kapicorp/kapitan/pull/410> but it needs some adjustments, as well as a methodology to mock the KMS APIs during tests in python. There is also some work done on adding Hashicorp's Vault as a secrets backend <https://github.com/kapicorp/kapitan/blob/master/docs/kap_proposals/kap_6_hashicorp_vault.md> but that is only implemented for reading values from vaultkv.

This project would be about finalizing all work related to the Azure KMS backend, adding tests + mocks for the Azure/Google/AWS secret backends and finally adding read/write support for the Vault secrets backend.

Expected Outcome: Azure KMS is added to Kapitan, tests are added for all secret backends (Azure, AWS, Google, Vault) and then support for the Vault backend is also added
Skills required: Python, some understanding of crypto/secret management
Difficulty: Medium/Hard

## 5. Your Idea

Description: If you think you have a good idea for another project for Kapitan feel free to reach out to us on Slack or our mailing list and discuss about it there. :)
