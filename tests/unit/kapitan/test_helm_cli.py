#!/usr/bin/env python3

import subprocess
from types import SimpleNamespace

from kapitan.helm_cli import helm_cli


def test_helm_cli_uses_env_path(monkeypatch):
    def _run(*_args, **_kwargs):
        return SimpleNamespace(returncode=0, stderr=b"", stdout=b"")

    monkeypatch.setenv("KAPITAN_HELM_PATH", "custom-helm")
    monkeypatch.setattr("kapitan.helm_cli.subprocess.run", _run)

    result = helm_cli(None, ["version"])
    assert result == ""


def test_helm_cli_returns_error_on_nonzero(monkeypatch):
    def _run(*_args, **_kwargs):
        return SimpleNamespace(returncode=1, stderr=b"boom", stdout=b"")

    monkeypatch.setattr("kapitan.helm_cli.subprocess.run", _run)

    result = helm_cli("helm", ["version"], verbose=True)
    assert result == "boom"


def test_helm_cli_missing_binary(monkeypatch):
    def _run(*_args, **_kwargs):
        raise FileNotFoundError

    monkeypatch.setattr("kapitan.helm_cli.subprocess.run", _run)

    result = helm_cli("missing", ["version"])
    assert "helm binary not found" in result


def test_helm_cli_timeout(monkeypatch):
    def _run(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd=["helm", "version"], timeout=1)

    monkeypatch.setattr("kapitan.helm_cli.subprocess.run", _run)

    result = helm_cli("helm", ["version"], timeout=1)
    assert "timed out" in result


def test_helm_cli_logs_verbose_stdout_lines(monkeypatch, caplog):
    def _run(*_args, **_kwargs):
        return SimpleNamespace(returncode=0, stderr=b"", stdout=b"first\n\nsecond\n")

    monkeypatch.setattr("kapitan.helm_cli.subprocess.run", _run)

    with caplog.at_level("DEBUG", logger="kapitan.helm_cli"):
        result = helm_cli("helm", ["version"], verbose=True)

    assert result == ""
    assert any("[helm] first" in msg for msg in caplog.messages)
    assert any("[helm] second" in msg for msg in caplog.messages)
