# SPDX-FileCopyrightText: 2026 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""kapitan publish against a registry:2 container, read back by fetch_oci_dependency."""

import os
import shutil
import time
from pathlib import Path

import pytest
import requests

from kapitan.cli import main as kapitan
from kapitan.dependency_manager.base import fetch_oci_dependency
from kapitan.dependency_manager.oci_push import push_oci_artifact
from kapitan.errors import KapitanError
from kapitan.inventory.model.dependencies import KapitanDependencyOciConfig


@pytest.fixture(scope="module")
def registry():
    docker = pytest.importorskip("docker")
    try:
        client = docker.from_env()
        client.ping()
    except docker.errors.DockerException as e:
        pytest.skip(f"docker is not available: {e}")
    container = client.containers.run(
        "registry:2", detach=True, ports={"5000/tcp": ("127.0.0.1", None)}
    )
    try:
        container.reload()
        port = container.attrs["NetworkSettings"]["Ports"]["5000/tcp"][0]["HostPort"]
        host = f"127.0.0.1:{port}"
        for _ in range(60):
            try:
                if requests.get(f"http://{host}/v2/", timeout=1).ok:
                    break
            except requests.ConnectionError:
                pass
            time.sleep(0.5)
        else:
            pytest.fail(f"registry:2 did not start: {container.logs(tail=20)}")
        yield host
    finally:
        container.remove(force=True)


def _tree(root):
    return {
        os.path.relpath(os.path.join(d, n), root): Path(d, n).read_bytes()
        for d, _, names in os.walk(root)
        for n in names
    }


def test_publish_then_fetch_gives_the_same_tree(registry, tmp_path, capsys):
    src = tmp_path / "src"
    (src / "lib").mkdir(parents=True)
    (src / "__init__.py").write_text("def main(input_params):\n    return {}\n")
    (src / "lib" / "utils.py").write_text("X = 1\n")
    (src / "run.sh").write_text("echo hi\n")
    (src / "run.sh").chmod(0o755)
    (src / ".git").mkdir()
    (src / ".git" / "config").write_text("not published\n")
    ref = f"{registry}/generators/demo"

    kapitan("publish", str(src), f"{ref}:1.0.0", "--insecure")
    digest = capsys.readouterr().out.strip()
    # Pinned: a change to the tar or manifest layout changes every published digest.
    assert digest == (
        "sha256:b3bdac14bb221cf51f38a7ff95da269ba44fbc77ed0a51a276545243df59c4b9"
    )

    copy = tmp_path / "copy"
    shutil.copytree(src, copy)
    for path in copy.rglob("*"):
        os.utime(path, (1_000_000_000, 1_000_000_000))
    kapitan("publish", str(copy), f"{ref}:1.0.1", "--insecure")
    assert capsys.readouterr().out.strip() == digest

    out = tmp_path / "out"
    dep = KapitanDependencyOciConfig(
        type="oci", source=f"{ref}@{digest}", output_path=str(out), insecure=True
    )
    fetch_oci_dependency((dep.source, [dep]), save_dir=str(tmp_path / "cache"))
    expected = _tree(src)
    del expected[os.path.join(".git", "config")]
    assert _tree(out) == expected


def test_publish_refuses_a_symlink(tmp_path):
    (tmp_path / "__init__.py").write_text("")
    (tmp_path / "link").symlink_to(tmp_path / "__init__.py")
    with pytest.raises(KapitanError, match="not a regular file"):
        push_oci_artifact(str(tmp_path), "localhost:1/never/contacted:1")
