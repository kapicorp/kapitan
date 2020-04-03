# External dependencies

This features allows kapitan to fetch files from online repositories/sources during compile and store in a particular target directory.

Author: @yoshi-1224

## Specification

Specify the files to be fetched as follows:

```yaml
parameters:
 kapitan:
  dependencies:
   - type: git | http[s]
     output_path: <output_path>
     source: <git/http[s]_url>    
``` 

The output path is the path to save the dependency into. For example, it could be `/components/external/manifest.jsonnet`. Then, the user can specify the fetched file as a `kapitan.compile` item along with the locally-created files.  

Git type may also include `ref` and `subdir` parameters as illustrated below:

```yaml
- type: git
  output_path: <output_path>
  source: <git_url>
  subdir: relative/path/in/repository
  ref: <commit_hash/branch/tag>
```

If the file already exists at `output_path`, the fetch will be skipped. For fresh fetch of the dependencies, users may add `--fetch` option as follows:

```bash
$ kapitan compile --fetch
```

Users can also add the `fetch_always: true` option to the `kapitan.compile` in the inventory in order to force fresh fetch of the dependencies every time.

## Implementation details

### Dependencies

- [GitPython](https://github.com/gitpython-developers/GitPython) module (and git executable) for git type
- requests module for http[s]
- (optional) [tqdm](https://github.com/tqdm/tqdm) for reporting download progress