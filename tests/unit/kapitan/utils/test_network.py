# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import pytest

import kapitan.utils.network as utils_network
from kapitan.utils.network import make_request


class _Response:
    def __init__(self, ok=True, content=b"", headers=None):
        self.ok = ok
        self.content = content
        self.headers = headers or {"Content-Type": "text/plain"}

    def raise_for_status(self):
        raise RuntimeError("bad status")


def test_make_request_non_raising_error_response(monkeypatch):
    class _NonRaisingResponse:
        ok = False
        content = b""
        headers = {"Content-Type": "application/octet-stream"}

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr(
        utils_network.requests, "get", lambda _url: _NonRaisingResponse()
    )
    assert make_request("https://example.test") == (None, None)


def test_make_request_ok(monkeypatch):
    response = _Response(
        ok=True, content=b"data", headers={"Content-Type": "text/plain"}
    )
    monkeypatch.setattr(utils_network.requests, "get", lambda _url: response)

    content, content_type = make_request("http://example")
    assert content == b"data"
    assert content_type == "text/plain"


def test_make_request_error(monkeypatch):
    response = _Response(ok=False)
    monkeypatch.setattr(utils_network.requests, "get", lambda _url: response)

    with pytest.raises(RuntimeError):
        make_request("http://example")
