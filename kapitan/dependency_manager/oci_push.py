# SPDX-FileCopyrightText: 2026 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Push a directory to an OCI registry in the layout fetch_oci_dependency reads."""

import hashlib
import json
import os
import tarfile
import tempfile
from pathlib import Path


try:
    import oras.client
except ImportError:
    oras = None

from kapitan.errors import KapitanError


ARTIFACT_TYPE = "application/vnd.kapitan.generator.v1"
LAYER_MEDIA_TYPE = "application/vnd.oci.image.layer.v1.tar"
LAYER_TITLE = "generator.tar"
MANIFEST_MEDIA_TYPE = "application/vnd.oci.image.manifest.v1+json"
# The OCI empty descriptor, the config of an artifact that carries none.
EMPTY_CONFIG = {
    "mediaType": "application/vnd.oci.empty.v1+json",
    "digest": "sha256:44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
    "size": 2,
}


def _raise(error):
    raise error


def write_tar(directory, out):
    """Write the files below directory to out so that the same tree gives the same bytes.

    Entries are sorted, with mtime 0, owner 0 and mode 0644 or 0755. Names starting
    with a dot are skipped, as safe_copy_tree skips them when a dependency is fetched.
    """
    files = []
    # onerror: an unreadable directory must fail the push, not drop out of it.
    for root, dirs, names in os.walk(directory, onerror=_raise):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in dirs + [n for n in names if not n.startswith(".")]:
            path = os.path.join(root, name)
            if os.path.islink(path) or not (
                os.path.isdir(path) or os.path.isfile(path)
            ):
                raise KapitanError(
                    f"cannot publish {path}: not a regular file or directory"
                )
            if os.path.isfile(path):
                files.append(Path(path).relative_to(directory).as_posix())
    if not files:
        raise KapitanError(f"cannot publish {directory}: no files to publish")
    with tarfile.open(out, "w", format=tarfile.PAX_FORMAT) as tar:
        for name in sorted(files):
            path = os.path.join(directory, name)
            info = tarfile.TarInfo(name)
            info.size = os.path.getsize(path)
            info.mode = 0o755 if os.stat(path).st_mode & 0o100 else 0o644
            with open(path, "rb") as f:
                tar.addfile(info, f)


def push_oci_artifact(directory, reference, insecure=False):
    """Push directory to reference as one tar layer and return the manifest digest."""
    if oras is None:
        raise ImportError(
            "The 'oras' package is required to publish OCI artifacts. "
            "Install it with: pip install kapitan[oci]"
        )
    if not os.path.isdir(directory):
        raise KapitanError(f"cannot publish {directory}: not a directory")

    with tempfile.TemporaryDirectory() as tmp:
        layer_path = os.path.join(tmp, LAYER_TITLE)
        write_tar(directory, layer_path)
        with open(layer_path, "rb") as f:
            layer_digest = hashlib.sha256(f.read()).hexdigest()
        layer = {
            "mediaType": LAYER_MEDIA_TYPE,
            "digest": f"sha256:{layer_digest}",
            "size": os.path.getsize(layer_path),
            "annotations": {"org.opencontainers.image.title": LAYER_TITLE},
        }
        config_path = os.path.join(tmp, "config.json")
        with open(config_path, "w") as f:
            f.write("{}")

        client = oras.client.OrasClient(insecure=insecure)
        container = client.get_container(reference)
        client.auth.load_configs(container)
        # The same environment credentials fetch_oci_dependency reads.
        username = os.environ.get("OCI_USERNAME")
        password = os.environ.get("OCI_PASSWORD")
        if username and password:
            client.auth.set_basic_auth(username, password)

        for path, descriptor in ((config_path, EMPTY_CONFIG), (layer_path, layer)):
            response = client.upload_blob(path, container, descriptor)
            if not response.ok:
                raise KapitanError(
                    f"uploading {descriptor['digest']} to {reference} failed: "
                    f"{response.status_code} {response.text}"
                )

    manifest = json.dumps(
        {
            "schemaVersion": 2,
            "mediaType": MANIFEST_MEDIA_TYPE,
            "artifactType": ARTIFACT_TYPE,
            "config": EMPTY_CONFIG,
            "layers": [layer],
        },
        separators=(",", ":"),
    ).encode()
    response = client.do_request(
        f"{client.prefix}://{container.manifest_url()}",
        "PUT",
        headers={"Content-Type": MANIFEST_MEDIA_TYPE},
        data=manifest,
    )
    if not response.ok:
        raise KapitanError(
            f"pushing the manifest to {reference} failed: "
            f"{response.status_code} {response.text}"
        )
    return f"sha256:{hashlib.sha256(manifest).hexdigest()}"
