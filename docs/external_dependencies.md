# Fetching external dependencies

Kapitan is capable of fetching components stored in remote locations. This feature can be used by specifying those dependencies in the inventory under `parameters.kapitan.dependencies`. Supported types are:

- [git type](#git-type)
- [http type](#http-type)

Some use cases of this feature may include:

- using templates/jsonnet libraries hosted remotely
- using values in remote files via `file_read` jsonnet callback

## Usage

```yaml
parameters:
  kapitan:
    dependencies:
    - type: <dependency_type>
      output_path: path/to/file/or/dir
      source: <source_of_dependency>
      # other type-specific parameters, if any
```

Use `--fetch` option to fetch the dependencies:

```
$ kapitan compile --fetch
```

This will download the dependencies and store them at their respective `output_path`. Dependencies whose `output_path` already exists will be skipped.

## Git type

Git types can fetch external dependencies available at `git://` URL. This is useful for fetching repositories or their sub-directories.

**Note**: git types require git binary available on your system. 

### Usage

```yaml
parameters:
  kapitan:
    dependencies:
    - type: git
      output_path: path/to/dir
      source: git://<url>
      subdir: relative/path/from/repo/root (optional)
      ref: tag, commit, branch etc. (optional)
```

## HTTP type

http[s] types can fetch external dependencies available at `http://` or `https://` URL. 

### Usage

```yaml
parameters:
  kapitan:
    dependencies:
    - type: http | https
      output_path: path/to/file
      source: http[s]://<url>
      unpack: True | False
```

`output_path` must fully specify the file name. For example:

```yaml
parameters:
  kapitan:
    dependencies:
    - type: https
      output_path: foo.txt
      source: https://example.com/foo.txt
      unpack: True | False
```

Setting `unpack: True` will unpack zip or tar files onto the output_path.