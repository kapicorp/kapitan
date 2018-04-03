## Kapitan: Docker image for macOS

tl;dr: Use `deepmind/kapitan:mac` instead of `deepmind/kapitan:latest` on macOS. This was created to address: https://github.com/deepmind/kapitan/issues/47

The [Docker image](https://hub.docker.com/r/deepmind/kapitan/tags/) (`deepmind/kapitan:mac`) ([Dockerfile](https://github.com/deepmind/kapitan/tree/master/docker-mac/Dockerfile)) has `deepmind/kapitan:latest` as its base, with the addition of:

- Copying files mounted in `/src` to `/tmp/kapitan`
- Running the `kapitan` command inside `/tmp/kapitan`
- Copying any generated files back into `/src`
