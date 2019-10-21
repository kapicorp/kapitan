## 0.25.2:
- Update wrong path for binaries (#400)
- Fix template for kapitan init so that the results compiles out of the box (#403)

## 0.25.1:
- Add jsonnet back to dockerfile.ci (#398)

## 0.25.0:
- Add support for revealing files in subdirectories (#386)
- Upgrade to TF 0.12.10 in Dockerfile.ci (#391)
- Label selectors for compilation (#388)
- Normalise helm compile (#385)
- Jsonschema function for jsonnet (#380)
- Fix issue 381: Document .kapitan and update jsonnet, git and hvac dependencies (#383)
- Vault secret backend added - read-only (#310)
- Add yq to the docker images (#375)
- Update all Dockerfiles to use multi-stage builds (#370)
- Add additional content type header for fetching GZIP files (#364)
- Fix Helm binding errors in docker (#359)
- Restore old order in compile_targets to fix process fork issue (#396)

#### Breaking:
For these breaking changes, run `./scripts/kap_5_migrate.py` to help you migrate the majority of secrets.

- Move to Kap5 ref types (#334)
- Fix issue #277: Change first '|' operator in secrets functions with '||' (#382)

## 0.25.0-rc.2:
- Add support for revealing files in subdirectories (#386)
- Upgrade to TF 0.12.10 in Dockerfile.ci (#391)
- Label selectors for compilation (#388)
- Normalise helm compile (#385)

## 0.25.0-rc.1:
- Jsonschema function for jsonnet (#380)
- Fix issue 381: Document .kapitan and update jsonnet, git and hvac dependencies (#383)
- Vault secret backend added - read-only (#310)

#### Breaking:
- Move to Kap5 ref types (#334)
- Fix issue #277: Change first '|' operator in secrets functions with '||' (#382)

## 0.24.1-rc.3:
- Add yq to the docker images (#375)

## 0.24.1-rc.2:
- Update all Dockerfiles to use multi-stage builds (#370)

## 0.24.1-rc.1:
- Add additional content type header for fetching GZIP files (#364)
- Fix Helm binding errors in docker (#359)

## 0.24.0:
- Add standalone binary to github releases
- Upgrade some packages in requirements.txt (#344)
- Upgrade kapp and kbld to v0.11.0 (#344)
- Fix dependency manager's behavior for files to unpack (#342)
- creating standalone binary for kapitan (#323)
- Add reveal_maybe custom jinja2 filter (#332)
- Add support to import Helm input type (#307)
- Make boto3 requirement more flexible (#320)
- Add kubernetes manifest validation (#317)
- Improve json schema validation error display for inventory (#318)
- Multi-document yaml outputs (#308)
- Add external dependency management (#304)
- Fix bug in resources.py when passing config to reclass (#296)
- Fix requests version to circumvent urllib3 version conflict (#300)
- Upgrade to jsonnet 0.13.0 (#309)
- Add kapp and kbld to kapitan-ci (#314)
- Implement secret sub-variables (#282)

## 0.24.0-rc.6:
- Testing github release of standalone binary

## 0.24.0-rc.4:
- Upgrade some packages in requirements.txt (#344)
- Upgrade kapp and kbld to v0.11.0 (#344)
- Fix dependency manager's behavior for files to unpack (#342)
- creating standalone binary for kapitan (#323)

## 0.24.0-rc.3:
- Add reveal_maybe custom jinja2 filter (#332)
- Add support to import Helm input type (#307)

## 0.24.0-rc.2:
- Make boto3 requirement more flexible (#320)
- Add kubernetes manifest validation (#317)
- Improve json schema validation error display for inventory (#318)
- Multi-document yaml outputs (#308)

## 0.24.0-rc.1:
- Add external dependency management (#304)

## 0.24.0-rc.0:
- Fix bug in resources.py when passing config to reclass (#296)
- Fix requests version to circumvent urllib3 version conflict (#300)
- Upgrade to jsonnet 0.13.0 (#309)
- Add kapp and kbld to kapitan-ci (#314)
- Implement secret sub-variables (#282)

## 0.23.1:
- Fix pypi package by including requirements.txt (#287)
- Make jsonnet & kadet support plain text output_type (#288)
- Fallback to reclass 1.5.6 because of regression (#284)
- Add parseYaml function in jsonnet (#263)
- Add support for specifying custom jinja2 filters (#267)
- Update minor dependencies (#283)

## 0.23.1-rc.1:
- Fallback to reclass 1.5.6 because of regression (#284)

## 0.23.1-rc.0:
- Add parseYaml function in jsonnet (#263)
- Add support for specifying custom jinja2 filters (#267)
- Update reclass (1.6.0) and other minor dependencies (#283)

## 0.23.0:
- Add support for writing ref type secrets in cli (#242)
- Validate target name matches target yml file name (#243)
- randomstr now generates exactly as many characters as requested (#245)
- Add yamllint in kapitan linter checks (#246)
- Added more jinja2 filters (#234)
- Improved tests coverage (#236)
- Fix included input templates (#229)
- Added kapitan init (#213)
- Removed ujson dependency (#220)
- Tests for terraform compile (#225)

#### Breaking:
- Fixed and updated kapitan version checking (#233)

## 0.23.0-rc.2:
- Add support for writing ref type secrets in cli (#242)
- Validate target name matches target yml file name (#243)
- randomstr now generates exactly as many characters as requested (#245)
- Add yamllint in kapitan linter checks (#246)

## 0.23.0-rc.1:
- Added more jinja2 filters (#234)
- Improved tests coverage (#236)

## 0.23.0-rc.0:
#### Breaking:
- Fixed and updated kapitan version checking (#233)

## 0.22.4-rc.1:
- Fix included input templates (#229)

## 0.22.4-rc.0:
- Added kapitan init (#213)
- Removed ujson dependency (#220)
- Tests for terraform compile (#225)

## 0.22.3:
- Fixed bug in secrets --validate-targets and --update-targets (#207)

## 0.22.2 (secrets validation broken, do not use):
- Fixed failing docker builds and added it to the tests (#204)
- Update google api python client (#204)

## 0.22.1 (secrets validation broken, do not use):
- Added some basic linter functionality (kapitan linter -h) (#193)
- Added support for Kadet input type (python, still a beta feature) (#190)

## 0.22.0:
#### Updates:
- Updated python dependencies: pyyaml and six
- Added AWS KMS support as a secrets backend (#179)
- Refactor input\_type code into classes (#180)
- Fix GPG failing when expiry of gpg key is infinite (#181)

#### Breaking:
- Added reveal secrets function, updated rsapublic function (#182)
- parameters.kapitan.secrets.recipients is deprecated, please use parameters.kapitan.secrets.gpg.recipients (#183)

## 0.21.0:
- Upgraded to jsonnet 0.12.1 (https://github.com/google/jsonnet/releases/tag/v0.12.1)

## 0.20.1:
- Added jinja2 base64 filter (#170)

## 0.20.0:
- Fix re.sub hanging (#158)
- gCloud KMS secrets backend (#159)
- Support .yaml in refs (#160)
- Better kapitan version checking (#163)
- Secrets fixes (#165)
- Travis, Docker and requirements updates (#166)
- gkms update and validate secrets (#167)
- Added promtool to CI image (#168)

## 0.20.0-rc.2:
- Travis, Docker and requirements updates (#166)
- gkms update and validate secrets (#167)

## 0.20.0-rc.1:
- Better kapitan version checking (#163)
- Secrets fixes (#165)

## 0.20.0-rc.0:
- gCloud KMS secrets backend (#159)
- Fix re.sub hanging (#158)
- Support .yaml in refs (#160)

## 0.19.0:
- Fix cli secrets (#154)
- Add python_requires (#149) - thanks @Code0x58
- update reclass to release v1.5.6 (#146)
- Secrets restructure (#148)

## 0.18.2:
- Fixed `gzip_b64` determinism

## 0.18.1:
- Dependencies update (#137)
- Made cache an optional flag (`--cache`). Support for additional cache paths (`--cache-paths`) (#138)
- Small fix in caching (#140)
- Added `gzip_b64` jsonnet function to support gzip compression of strings + base64
- Added Python 3.7 support

## 0.18.0:
#### Breaking:
- Renamed `--search-path` to `--search-paths` in `eval` and `compile`, enabling multiple paths for jsonnet/jinja2 and adding support for [jsonnet bundler](https://github.com/jsonnet-bundler/jsonnet-bundler) (#133)

#### Updates:
- Inventory and folders caching; only compile targets that changed (#134)
- Updated reclass to v1.5.5 (#135)
- Updated jsonnet to v0.11.2 (#136)

## 0.17.1:
- Command flags support in .kapitan (#125)
- Upgraded reclass to 1.5.4 (#127)
- Added `rsapublic` function to gpg backend (#128)

## 0.17.0:
#### Breaking:
- `kapitan compile` does not prune jsonnet output anymore by default (#118). `--no-prune` flag has been removed and replaced with `--prune`. If you want to keep jsonnet output consistent with <0.17.0, you can do `kapitan compile --prune`.

#### Updates:
- Add pretty printer (`-p`) option to searchvar (#121)
- Cleaned up examples (#123)
- Updated requests to 2.19.1 (#124)

## 0.16.11:
- Updated RSA key format to PKCS#8 (#120)

## 0.16.10:
- GPG backend cleanup (no change in usage or cli) (#116)
- Improved caching (#117)
- Verbose options for `inventory` and `searchvar` commands (#119)

## 0.16.9:
- Fixed bug with searchvar keys chain (#115)

## 0.16.8:
- Reclass submodule integration fixes

## 0.16.5:
- Reclass update (#112)

## 0.16.4:
- Fixed deep_get recursion and search (#108)
- Customizable indentation of yaml/json (#110)

## 0.16.3:
- Allow recursive search and globbing in searchvar and inventory commands (#97)
- terraform in CI image (#98)
- Updated kube.libjsonnet and fixed secrets example (#101)
- Added secrets info in docs
- Updates to GPG backend functions (#103):
  - RSA private keys `?{gpg:common/rsa.key|rsa}`
  - Support for pipes `?{gpg:mysql/root/password|randomstr|base64}`
  - SHA256 function `?{gpg:mysql/root/password|randomstr|sha256}`
  - Deprecated `|randomstrb64` in favor of `|randomstr|base64`

## 0.16.2:
- Do not escape forward slashes in `json.dump` (#92)
- sha256 jsonnet function (#94)

## 0.16.1:
- Fix for #81
- Clearer message for version check (#82)
- Support for jinja2 'do' extension (#89)

## 0.16.0:
- Updated reclass
- (https://github.com/deepmind/kapitan/pull/78) Support for creating a target secret on compile time, if the secret does not already exist:
```
?{gpg:path/to/new_secret|randomstr:32}
```
If `path/to/new_secret` does not exist under `secrets_path` it evaluates `randomstr:32`, which returns a 32 byte-log random string generated by [secrets.token_urlsafe](https://docs.python.org/3/library/secrets.html#secrets.token_urlsafe) and creates the secret with its content.
- (https://github.com/deepmind/kapitan/pull/79) Support for YAML C bindings to improve compilation performance.

If you're using the pip version of Kapitan, you can benefit from YAML C bindings support by running:

Linux: `sudo apt-get install python3-yaml`
Mac: `brew install libyaml`

## 0.15.0:
- Updates to `deepmind/kapitan:ci` Docker image
- `kapitan secrets --write` and `kapitan secrets --update-targets` are now consistent in terms of the recipients list #67
- Significant performance improvement to `kapitan compile` #71
- `kapitan compile` now writes the version to `.kapitan` and future executions will check if the last used kapitan version is <= than the current kapitan version, to keep compilations consistent. You can skip version check by doing `kapitan compile --ignore-version-check`. For more info see #57 and #72

## 0.14.0:
- Kapitan now requires python 3.6
- Fixed dockerfile to ensure delegated volumes (#47)
- Fixed missing target compiled directory
- Target compilation error improvements (#62)
- gnupg updated to 0.4.2
- Inventory target pattern command parsing improvements

## 0.13.0:
- Added --pattern feature to inventory cli (https://github.com/deepmind/kapitan/issues/41)
- now using python3 lru_cache instead of memoize
- fixed searchvar (https://github.com/deepmind/kapitan/issues/40)

## 0.12.0:
- moved to python 3 (python 2 should still work but no longer supported)
- updated to jsonnet v0.10.0
- new yaml jinja2 filter
- target secrets support (https://github.com/deepmind/kapitan/pull/36)
- more tests

## 0.11.0:
- Supports compiling specific targets
- Breaking change: non inventory target files are gone

## 0.10.0:
- Supports reading targets from the inventory as well as target files
- Breaking change: the keys in compile items changed, see (#22)

## 0.9.19:
- checks for gpg key expiry
- allow base64 encoding content for secrets
- support for revealing files in directories

## 0.9.18:
- fixes a bug that overwrites the output_path if it is set to '.'

## 0.9.17:
- breaking change: the compile command will compile all targets found (https://github.com/deepmind/kapitan/pull/16)
- log/print friendlier error messages avoiding tracebacks for known failure behaviours (https://github.com/deepmind/kapitan/pull/15) (fixes https://github.com/deepmind/kapitan/issues/11)

## 0.9.16:
- gpg secrets support
- compiled secret tags
- new --reveal flag for compile sub-command
- new --no-verify for secrets sub-command
- new yaml_dump() native jsonnet function

## 0.9.15:
- Documentation Improvements
- New --version flag
- Now using jsonnet 0.9.5
- inventory_global in jinja and jsonnet
- Packaged lib/kapitan.libjsonnet

## 0.9.14:
Initial public version
