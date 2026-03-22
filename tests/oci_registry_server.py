# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Local OCI registry helpers for integration tests."""

import logging
import os
import tempfile
from time import sleep

import docker
import requests

from kapitan.errors import KapitanError


logger = logging.getLogger(__name__)


class OciRegistryError(KapitanError):
    """Raised when the local OCI registry fails to start or become ready."""


class OciRegistryServer:
    """Starts a local registry:2 container and pre-loads it with test artifacts."""

    def __init__(self):
        self.docker_client = docker.from_env()
        self.container = self._start_container()
        self._wait_until_ready()
        self.host = f"localhost:{self.port}"

    def _start_container(self):
        container = self.docker_client.containers.run(
            image="registry:2",
            ports={"5000/tcp": ("127.0.0.1", None)},
            detach=True,
            auto_remove=False,
        )
        while container.status != "running":
            sleep(1)
            container.reload()
            if container.status in ("exited", "dead"):
                logs = container.logs(tail=50).decode("utf-8", errors="replace")
                raise OciRegistryError(
                    f"Registry container exited early: {container.status}\n{logs}"
                )
        self.port = container.attrs["NetworkSettings"]["Ports"]["5000/tcp"][0][
            "HostPort"
        ]
        logger.info("OCI registry container started on port %s", self.port)
        return container

    def _wait_until_ready(self):
        url = f"http://localhost:{self.port}/v2/"
        for _ in range(30):
            try:
                resp = requests.get(url, timeout=2)
                if resp.status_code in (200, 401):
                    logger.info("OCI registry is ready at %s", url)
                    return
            except requests.exceptions.ConnectionError:
                pass
            sleep(1)
        raise OciRegistryError("OCI registry did not become ready in time")

    def push_artifact(self, repository: str, tag: str, files: list[str]) -> str:
        """Push files to the local registry and return the full reference."""
        import oras.client

        target = f"localhost:{self.port}/{repository}:{tag}"
        client = oras.client.OrasClient(insecure=True)
        with tempfile.TemporaryDirectory() as staging:
            # files must be relative to CWD for oras path validation
            staged = []
            for path_spec in files:
                if ":" in path_spec:
                    path, media_type = path_spec.split(":", 1)
                else:
                    path, media_type = path_spec, None
                dest = os.path.join(staging, os.path.basename(path))
                if os.path.isdir(path):
                    import shutil

                    shutil.copytree(path, dest)
                else:
                    import shutil

                    shutil.copy2(path, dest)
                staged.append(f"{dest}:{media_type}" if media_type else dest)

            client.push(
                target=target,
                files=staged,
                disable_path_validation=True,
            )
        logger.info("Pushed artifact to %s", target)
        return target

    def close(self):
        logger.info("Stopping OCI registry container")
        self.container.stop()
        self.container.remove()
        self.docker_client.close()
