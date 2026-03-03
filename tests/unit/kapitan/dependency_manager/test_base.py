#!/usr/bin/env python3

from types import SimpleNamespace

import pytest
from git import GitCommandError

from kapitan.dependency_manager import base as dep
from kapitan.errors import (
    GitFetchingError,
    GitSubdirNotFoundError,
    HelmFetchingError,
)
from kapitan.inventory.model.dependencies import KapitanDependencyTypes


def test_exists_in_cache(tmp_path):
    item_path = tmp_path / "cache" / "item"
    assert dep.exists_in_cache(str(item_path)) is False

    item_path.parent.mkdir(parents=True)
    item_path.write_text("data", encoding="utf-8")
    assert dep.exists_in_cache(str(item_path)) is True


def test_fetch_http_source_writes_file(tmp_path, monkeypatch):
    content = b"data"

    def _make_request(_source):
        return content, "text/plain"

    monkeypatch.setattr(dep, "make_request", _make_request)

    save_path = tmp_path / "file.txt"
    content_type = dep.fetch_http_source("http://example", str(save_path), "Dependency")

    assert save_path.read_bytes() == content
    assert content_type == "text/plain"


def test_fetch_http_dependency_unpack(tmp_path, monkeypatch):
    cache_file = tmp_path / "cache.tgz"
    cache_file.write_bytes(b"data")

    def _fetch_http_source(_source, _save_path, _item_type):
        return "application/gzip"

    unpack_calls = []

    def _unpack(_file_path, _output_path, _content_type):
        unpack_calls.append((_file_path, _output_path, _content_type))
        return True

    monkeypatch.setattr(dep, "fetch_http_source", _fetch_http_source)
    monkeypatch.setattr(dep, "unpack_downloaded_file", _unpack)

    dep_mapping = (
        "http://example/file.tgz",
        [SimpleNamespace(output_path=str(tmp_path / "out"), unpack=True)],
    )

    dep.fetch_http_dependency(dep_mapping, save_dir=str(tmp_path), force=True)

    assert unpack_calls


def test_fetch_http_dependency_copy_file(tmp_path, monkeypatch):
    source = "http://example/file.txt"
    path_hash = dep.hashlib.sha256(dep.os.path.dirname(source).encode()).hexdigest()[:8]
    cached_path = tmp_path / f"{path_hash}file.txt"
    cached_path.write_text("data", encoding="utf-8")

    copy_calls = []

    def _safe_copy_file(src, dst):
        copy_calls.append((src, dst))

    monkeypatch.setattr(dep, "safe_copy_file", _safe_copy_file)

    dep_mapping = (
        source,
        [SimpleNamespace(output_path=str(tmp_path / "out.txt"), unpack=False)],
    )

    dep.fetch_http_dependency(dep_mapping, save_dir=str(tmp_path), force=False)

    assert copy_calls


def test_fetch_helm_archive_error(monkeypatch, tmp_path):
    def _helm_cli(_helm_path, _args):
        return "error"

    monkeypatch.setattr(dep, "helm_cli", _helm_cli)

    with pytest.raises(HelmFetchingError):
        dep.fetch_helm_archive(
            helm_path="helm",
            repo="https://example",
            chart_name="chart",
            version="1.0.0",
            save_path=str(tmp_path / "chart"),
        )


def test_fetch_helm_archive_success(monkeypatch, tmp_path):
    def _helm_cli(_helm_path, _args):
        return ""

    monkeypatch.setattr(dep, "helm_cli", _helm_cli)

    save_dir = tmp_path / "charts"
    save_dir.mkdir()
    (save_dir / "chart").mkdir()

    dest = save_dir / "renamed-chart"
    dep.fetch_helm_archive(
        helm_path="helm",
        repo="https://example",
        chart_name="chart",
        version="1.0.0",
        save_path=str(dest),
    )

    assert dest.is_dir()


def test_fetch_git_source_error(monkeypatch, tmp_path):
    def _clone_from(_source, _save_dir):
        raise GitCommandError("clone", 1, stderr="boom")

    monkeypatch.setattr(dep.Repo, "clone_from", _clone_from)

    with pytest.raises(GitFetchingError):
        dep.fetch_git_source("https://example/repo.git", str(tmp_path), "Dependency")


def test_fetch_git_source_success_without_existing_cache(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setattr(
        dep.Repo,
        "clone_from",
        lambda source, save_dir: calls.append((source, save_dir)),
    )

    save_dir = tmp_path / "repo-cache"
    dep.fetch_git_source("https://example/repo.git", str(save_dir), "Dependency")

    assert calls == [("https://example/repo.git", str(save_dir))]


def test_fetch_dependencies_groups_items_and_skips_duplicates(monkeypatch, tmp_path):
    class _Pool:
        def imap_unordered(self, worker, items):
            return [SimpleNamespace(get=lambda result=worker(i): result) for i in items]

    calls = {"git": [], "http": [], "helm": []}

    monkeypatch.setattr(
        dep,
        "fetch_git_dependency",
        lambda mapping, **_kwargs: calls["git"].append(mapping),
    )
    monkeypatch.setattr(
        dep,
        "fetch_http_dependency",
        lambda mapping, **_kwargs: calls["http"].append(mapping),
    )
    monkeypatch.setattr(
        dep,
        "fetch_helm_chart",
        lambda mapping, **_kwargs: calls["helm"].append(mapping),
    )

    git_dep = SimpleNamespace(
        type=KapitanDependencyTypes.GIT,
        source="https://example/repo.git",
        output_path="deps/repo",
        ref="main",
        submodules=False,
        subdir=None,
    )
    git_dep_duplicate = SimpleNamespace(
        type=KapitanDependencyTypes.GIT,
        source="https://example/repo.git",
        output_path="deps/repo",
        ref="main",
        submodules=False,
        subdir=None,
    )
    http_dep = SimpleNamespace(
        type=KapitanDependencyTypes.HTTPS,
        source="https://example/archive.tgz",
        output_path="deps/archive",
        unpack=True,
    )
    helm_dep = SimpleNamespace(
        type=KapitanDependencyTypes.HELM,
        source="https://charts.example",
        output_path="deps/chart",
        chart_name="demo",
        version="1.0.0",
        helm_path="helm",
    )
    invalid_dep = SimpleNamespace(
        type="invalid-type",
        source="https://invalid.example",
        output_path="deps/invalid",
    )

    class _TargetWithoutDependencies(dict):
        @property
        def dependencies(self):
            raise KeyError("dependencies")

    targets = [
        SimpleNamespace(
            dependencies=[git_dep, git_dep_duplicate, http_dep, helm_dep, invalid_dep]
        ),
        _TargetWithoutDependencies(vars={"target": "missing"}),
    ]

    dep.fetch_dependencies(
        output_path=str(tmp_path / "compiled"),
        target_objs=targets,
        save_dir=str(tmp_path / "cache"),
        force=False,
        pool=_Pool(),
    )

    assert len(calls["git"]) == 1
    assert len(calls["http"]) == 1
    assert len(calls["helm"]) == 1
    assert git_dep.output_path.endswith("compiled/deps/repo")


def test_fetch_git_dependency_cached_repo_with_submodules_and_subdir(
    monkeypatch, tmp_path
):
    source = "https://example/repo.git"
    path_hash = dep.hashlib.sha256(dep.os.path.dirname(source).encode()).hexdigest()[:8]
    cached_repo = tmp_path / f"{path_hash}repo.git"
    (cached_repo / "subdir").mkdir(parents=True)

    class _Submodule:
        def __init__(self):
            self.updated = False

        def update(self, init=True):
            self.updated = init

    submodule = _Submodule()

    class _Repo:
        def __init__(self, _path):
            self.git = SimpleNamespace(checkout=lambda _ref: None)
            self.submodules = [submodule]

    copied_sources = []

    monkeypatch.setattr(dep, "exists_in_cache", lambda _path: True)
    monkeypatch.setattr(dep, "Repo", _Repo)
    monkeypatch.setattr(
        dep,
        "safe_copy_tree",
        lambda src, _dst: copied_sources.append(src) or [],
    )

    dep.fetch_git_dependency(
        (
            source,
            [
                SimpleNamespace(
                    output_path=str(tmp_path / "out"),
                    ref="main",
                    submodules=True,
                    subdir="subdir",
                )
            ],
        ),
        save_dir=str(tmp_path),
        force=False,
    )

    assert submodule.updated is True
    assert copied_sources == [str(cached_repo / "subdir")]


def test_fetch_git_dependency_missing_subdir_raises(monkeypatch, tmp_path):
    source = "https://example/repo.git"

    class _Repo:
        def __init__(self, _path):
            self.git = SimpleNamespace(checkout=lambda _ref: None)
            self.submodules = []

    monkeypatch.setattr(dep, "exists_in_cache", lambda _path: True)
    monkeypatch.setattr(dep, "Repo", _Repo)

    with pytest.raises(GitSubdirNotFoundError):
        dep.fetch_git_dependency(
            (
                source,
                [
                    SimpleNamespace(
                        output_path=str(tmp_path / "out"),
                        ref="main",
                        submodules=False,
                        subdir="missing",
                    )
                ],
            ),
            save_dir=str(tmp_path),
            force=False,
        )


def test_fetch_git_dependency_force_path_uses_copy_tree(monkeypatch, tmp_path):
    source = "https://example/repo.git"

    class _Repo:
        def __init__(self, _path):
            self.git = SimpleNamespace(checkout=lambda _ref: None)
            self.submodules = []

    copy_tree_calls = []

    monkeypatch.setattr(dep, "exists_in_cache", lambda _path: True)
    monkeypatch.setattr(dep, "fetch_git_source", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(dep, "Repo", _Repo)
    monkeypatch.setattr(
        dep,
        "copy_tree",
        lambda src, dst, clobber_files=False: copy_tree_calls.append(
            (src, dst, clobber_files)
        )
        or ["copied"],
    )

    dep.fetch_git_dependency(
        (
            source,
            [
                SimpleNamespace(
                    output_path=str(tmp_path / "out"),
                    ref="main",
                    submodules=False,
                    subdir=None,
                )
            ],
        ),
        save_dir=str(tmp_path),
        force=True,
    )

    assert copy_tree_calls
    assert copy_tree_calls[0][2] is True


def test_fetch_helm_chart_fetches_archive_and_safely_copies(monkeypatch, tmp_path):
    source = SimpleNamespace(
        repo="https://charts.example",
        chart_name="demo",
        version="1.0.0",
        helm_path="helm",
    )
    fetched = []
    copied = []

    monkeypatch.setattr(dep, "exists_in_cache", lambda _path: False)
    monkeypatch.setattr(
        dep,
        "fetch_helm_archive",
        lambda helm_path, repo, chart_name, version, save_path: fetched.append(
            (helm_path, repo, chart_name, version, save_path)
        ),
    )
    monkeypatch.setattr(
        dep,
        "safe_copy_tree",
        lambda src, dst: copied.append((src, dst)) or [dst],
    )

    dep.fetch_helm_chart(
        (source, [SimpleNamespace(output_path=str(tmp_path / "out" / "demo"))]),
        save_dir=str(tmp_path / "cache"),
        force=False,
    )

    assert fetched
    assert copied


def test_fetch_http_dependency_non_force_unpack_uses_staging_dir(monkeypatch, tmp_path):
    safe_copy_tree_calls = []
    removed_paths = []

    monkeypatch.setattr(dep, "exists_in_cache", lambda _path: False)
    monkeypatch.setattr(
        dep, "fetch_http_source", lambda *_args, **_kwargs: "application/gzip"
    )
    monkeypatch.setattr(dep, "unpack_downloaded_file", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        dep,
        "safe_copy_tree",
        lambda src, dst: safe_copy_tree_calls.append((src, dst)) or [],
    )
    monkeypatch.setattr(dep, "rmtree", lambda path: removed_paths.append(path))

    dep.fetch_http_dependency(
        (
            "https://example/archive.tgz",
            [SimpleNamespace(output_path=str(tmp_path / "out"), unpack=True)],
        ),
        save_dir=str(tmp_path),
        force=False,
    )

    assert safe_copy_tree_calls
    assert removed_paths


def test_fetch_http_dependency_force_copy_to_parentless_path(monkeypatch, tmp_path):
    copy_calls = []

    monkeypatch.setattr(dep, "exists_in_cache", lambda _path: False)
    monkeypatch.setattr(
        dep, "fetch_http_source", lambda *_args, **_kwargs: "text/plain"
    )
    monkeypatch.setattr(
        dep,
        "copyfile",
        lambda src, dst: copy_calls.append((src, dst)),
    )

    dep.fetch_http_dependency(
        (
            "https://example/file.txt",
            [SimpleNamespace(output_path="out.txt", unpack=False)],
        ),
        save_dir=str(tmp_path),
        force=True,
    )

    assert copy_calls
    assert copy_calls[0][1] == "out.txt"


def test_fetch_http_source_replaces_existing_file_and_handles_empty_content(
    monkeypatch, tmp_path
):
    save_path = tmp_path / "existing.txt"
    save_path.write_text("old", encoding="utf-8")

    monkeypatch.setattr(dep, "make_request", lambda _source: (b"new", "text/plain"))
    content_type = dep.fetch_http_source(
        "https://example/file.txt", str(save_path), "Dependency"
    )
    assert content_type == "text/plain"
    assert save_path.read_bytes() == b"new"

    monkeypatch.setattr(dep, "make_request", lambda _source: (None, "text/plain"))
    assert (
        dep.fetch_http_source("https://example/none.txt", str(save_path), "Dependency")
        is None
    )


def test_fetch_helm_chart_skips_existing_destination_when_not_force(
    monkeypatch, tmp_path
):
    output_path = tmp_path / "chart"
    output_path.mkdir()

    source = dep.HelmSource(
        repo="https://charts.example",
        chart_name="demo",
        version="1.0.0",
        helm_path="helm",
    )
    dep_mapping = (source, [SimpleNamespace(output_path=str(output_path))])

    monkeypatch.setattr(
        dep,
        "fetch_helm_archive",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected")),
    )

    dep.fetch_helm_chart(dep_mapping, save_dir=str(tmp_path), force=False)


def test_fetch_helm_chart_force_uses_cached_repo_and_copy_tree(monkeypatch, tmp_path):
    copy_calls = []

    source = dep.HelmSource(
        repo="https://charts.example",
        chart_name="demo",
        version=None,
        helm_path="helm",
    )
    dep_mapping = (source, [SimpleNamespace(output_path="chart-out")])

    monkeypatch.setattr(dep, "exists_in_cache", lambda _path: True)
    monkeypatch.setattr(
        dep,
        "copy_tree",
        lambda src, dst: copy_calls.append((src, dst)) or [],
    )

    dep.fetch_helm_chart(dep_mapping, save_dir=str(tmp_path), force=True)

    assert copy_calls


def test_fetch_helm_archive_oci_repo_without_version(monkeypatch, tmp_path):
    captured_args = {}

    def _helm_cli(_helm_path, args):
        captured_args["args"] = args
        return ""

    monkeypatch.setattr(dep, "helm_cli", _helm_cli)

    save_dir = tmp_path / "charts"
    save_dir.mkdir()
    (save_dir / "chart").mkdir()

    dep.fetch_helm_archive(
        helm_path="helm",
        repo="oci://registry.example/charts/demo",
        chart_name="chart",
        version=None,
        save_path=str(save_dir / "renamed"),
    )

    assert "--version" not in captured_args["args"]
    assert "--repo" not in captured_args["args"]
    assert captured_args["args"][-1] == "oci://registry.example/charts/demo"
