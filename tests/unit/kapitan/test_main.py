#!/usr/bin/env python3

import runpy

from kapitan import cli


def test_main_invokes_cli_main(monkeypatch):
    called = {"value": False}

    def _main():
        called["value"] = True

    monkeypatch.setattr(cli, "main", _main)
    runpy.run_module("kapitan.__main__", run_name="__main__")

    assert called["value"] is True
