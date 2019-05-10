# New features for Google Summer of Code 2019

Note: this is an abbreviated version of the  accepted proposal. For the full proposal, please follow the link [here](https://docs.google.com/document/d/1BXU_EbQak4EIU9ELpvRIYDiRB0_JCKURtaVkFOpIKQc/edit?usp=sharing).

## Feature 1: external dependencies
This features allows kapitan to fetch files from online repositories/sources during compile and store in a particular target directory.

### User Guide
Specify the files to be fetched as follows:
```yaml
parameters:
 kapitan:
  dependencies:
   - type: git | http[s]
     output_path: relative/path/in/target
     source: <git/http[s]_url>    
``` 

Git type may also include `ref` and `subdir` parameters as illustrated below:
```yaml
   - type: git
     output_path: relative/path/in/target
     source: <git_url>
     subdir: relative/path/in/repository
     ref: <commit_hash/branch/tag>
```

Downloaded files will be cached. For fresh fetch of the dependencies, users may add `--fetch` option as follows:
```bash
$ kapitan compile --fetch
```
### Implementation 
#### Dependencies
- GitPython module (and git executable) for git type
- requests module for http[s]
- (optional) tqdm for reporting download progress

## Feature 2: Templating Helm charts
This will allow kapitan, during compilation, to overwrite the values in user-specified helm charts using its inventory by calling the Go & Sprig template libraries. The helm charts can be specified via local path, and users may download the helm chart via external-dependency feature (of http[s] type) described above.

### User Guide
TBC

### Implementation
- C-binding between Helm (Go) and Kapitan (Python). Go template will be converted into shared object file using CGo, from where the interface to Python will be created.

### Dependencies
- (possibly) pybindgen

## Feature 3: YAML manifest validation for k8s 
If a yaml output is to be used as k8s manifest, users may specify its kind and have Kapitan validate its structure during `kapitan compile`.

### User Guide
The following inventory will validate the structure of Kubernetes Service manifest file in <output_path>.

```yaml
parameters:
  kapitan:
    validate:
       - output_type: kubernetes.service 
         version: 1.6.6
         output_path: relative/path/in/target
```
`version` parameter is optional: if omitted, the version will be set to the stable release of kubernetes (tbc).

### Implementation
- The schemas will be downloaded by requests from 
[this repository](https://raw.githubusercontent.com/garethr/kubernetes-json-schema/master/v1.6.6-standalone/deployment.json).
- Caching of schema will also be implemented.

#### Dependencies
- jsonschema to validate the output yaml/json against the correct schema

## Feature 4: kapitan binary
Create a portable (i.e. static) kapitan binary for users. This binary will be made available for reach release on Github. The target/tested platform is Debian 9 (possibly Windows to be supported in the future).

### Implementation
- Cythonize the code for faster binary

#### Dependencies
- Pyinstaller to create the static binary

## 
Student: Yoshiaki Nishimura

Please feel free to review and suggest new ideas!