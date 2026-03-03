#!/usr/bin/env python3

import base64
import errno
import importlib
import importlib.util
import sys
import types
from pathlib import Path

import pytest

from kapitan.errors import RefFromFuncError, RefHashMismatchError
from kapitan.refs.base import RefParams
from kapitan.refs.base64 import Base64Ref


def test_base64_ref_compile(ref_controller):
    tag = "?{base64:my/ref1}"
    ref_controller[tag] = Base64Ref(b"ref 1 data")
    ref_obj = ref_controller[tag]
    assert ref_obj.compile() == "?{base64:my/ref1:3342a45c}"


def test_base64_ref_embedded_compile(ref_controller_embedded):
    tag = "?{base64:my/ref1}"
    ref_controller_embedded[tag] = Base64Ref(b"ref 1 data")
    ref_obj = ref_controller_embedded[tag]
    compiled_embedded = ref_obj.compile()
    embedded_tag = (
        "?{base64:eyJkYXRhIjogImNtVm1JREVnWkdGMFlRPT0iLCAiZW5jb2"
        "RpbmciOiAib3JpZ2luYWwiLCAidHlwZSI6ICJiYXNlNjQifQ==:embedded}"
    )
    assert compiled_embedded == embedded_tag


def test_base64_ref_recompile(ref_controller):
    tag = "?{base64:my/ref1}"
    ref_controller[tag] = Base64Ref(b"ref 1 data")
    ref_obj = ref_controller[tag]
    assert ref_obj.compile() == "?{base64:my/ref1:3342a45c}"


def test_base64_ref_update_compile(ref_controller):
    tag = "?{base64:my/ref1}"
    ref_controller[tag] = Base64Ref(b"ref 1 more data")
    ref_obj = ref_controller[tag]
    assert ref_obj.compile() == "?{base64:my/ref1:ed438a62}"


def test_base64_ref_reveal(ref_controller):
    tag = "?{base64:my/ref2}"
    ref_controller[tag] = Base64Ref(b"ref 2 data")
    ref_obj = ref_controller[tag]
    assert ref_obj.reveal() == "ref 2 data"


def test_base64_ref_embedded_reveal(ref_controller_embedded):
    tag = "?{base64:my/ref2}"
    ref_controller_embedded[tag] = Base64Ref(b"ref 2 data")
    ref_obj = ref_controller_embedded[tag]
    assert ref_obj.reveal() == "ref 2 data"


def test_base64_ref_embedded_reveal_encoding_original(ref_controller_embedded):
    tag = "?{base64:my/ref2}"
    ref_controller_embedded[tag] = Base64Ref(b"ref 2 data")
    ref_obj = ref_controller_embedded[tag]
    assert ref_obj.reveal() == "ref 2 data"
    assert ref_obj.encoding == "original"


def test_base64_ref_embedded_reveal_encoding_base64(ref_controller_embedded):
    tag = "?{base64:my/ref3}"
    ref_controller_embedded[tag] = Base64Ref(
        base64.b64encode(b"ref 3 data"), encoding="base64"
    )
    ref_obj = ref_controller_embedded[tag]
    assert ref_obj.reveal() == base64.b64encode(b"ref 3 data").decode()
    assert ref_obj.encoding == "base64"


def test_base64_ref_non_existent_raises_key_error(ref_controller):
    tag = "?{base64:non/existent}"
    with pytest.raises(KeyError):
        ref_controller[tag]


def test_base64_ref_tag_type(ref_controller):
    tag = "?{base64:my/ref3}"
    tag_type = ref_controller.tag_type(tag)
    assert tag_type == Base64Ref


def test_base64_ref_tag_type_name(ref_controller):
    tag = "?{base64:my/ref4}"
    tag, token, func_str = ref_controller.tag_params(tag)
    type_name = ref_controller.token_type_name(token)
    assert tag == "?{base64:my/ref4}"
    assert token == "base64:my/ref4"
    assert func_str is None
    assert type_name == "base64"


def test_base64_ref_tag_func_name(ref_controller):
    tag = "?{base64:my/ref5||random:str}"
    tag, token, func_str = ref_controller.tag_params(tag)
    assert tag == "?{base64:my/ref5||random:str}"
    assert token == "base64:my/ref5"
    assert func_str == "||random:str"


def test_base64_ref_embedded_attr(ref_controller_embedded):
    tag = "?{base64:my/ref2}"
    ref_controller_embedded[tag] = Base64Ref(b"ref 2 data")
    ref_obj = ref_controller_embedded[tag]
    assert ref_obj.embed_refs is True


def test_base64_ref_attr(ref_controller):
    tag = "?{base64:my/ref2}"
    ref_controller[tag] = Base64Ref(b"ref 2 data")
    ref_obj = ref_controller[tag]
    assert ref_obj.embed_refs is False


def test_base64_ref_path(ref_controller):
    tag = "?{base64:my/ref6}"
    tag, token, func_str = ref_controller.tag_params(tag)
    assert tag == "?{base64:my/ref6}"
    assert token == "base64:my/ref6"
    assert func_str is None
    ref_controller[tag] = Base64Ref(b"ref 6 data")
    ref_obj = ref_controller[tag]
    assert ref_obj.path == "my/ref6"


def test_base64_ref_func_raise_ref_from_func_error(ref_controller):
    tag = "?{base64:my/ref7||random:str}"
    with pytest.raises(RefFromFuncError):
        ref_controller[tag]
    try:
        ref_controller[tag]
    except RefFromFuncError:
        ref_controller[tag] = RefParams()
    ref_controller[tag]


def test_base64_ref_revealer_reveal_raw_data_tag(ref_controller, revealer):
    tag = "?{base64:my/ref2}"
    ref_controller[tag] = Base64Ref(b"ref 2 data")
    data = f"data with {tag}, period."
    revealed_data = revealer.reveal_raw(data)
    assert revealed_data == "data with ref 2 data, period."


def test_base64_ref_revealer_reveal_raw_data_tag_compiled_hash(
    ref_controller, revealer
):
    tag = "?{base64:my/ref2}"
    ref_controller[tag] = Base64Ref(b"ref 2 data")
    tag_compiled = ref_controller[tag].compile()
    data = f"data with {tag_compiled}, period."
    revealed_data = revealer.reveal_raw(data)
    assert revealed_data == "data with ref 2 data, period."


def test_base64_ref_revealer_reveal_raw_data_tag_compiled_hash_mismatch(
    ref_controller, revealer
):
    tag = "?{base64:my/ref2}"
    ref_controller[tag] = Base64Ref(b"ref 2 data")
    tag_compiled_hash_mismatch = "?{base64:my/ref2:deadbeef}"
    with pytest.raises(RefHashMismatchError):
        data = f"data with {tag_compiled_hash_mismatch}, period."
        revealer.reveal_raw(data)


def test_base64_ref_reveal_returns_raw_data_when_decoding_fails():
    encoded_binary = base64.b64encode(b"\xff\xfe").decode()
    ref_obj = Base64Ref(encoded_binary, from_base64=True)
    assert ref_obj.reveal() == encoded_binary


def test_base64_ref_from_path_handles_non_enoent_oserror(monkeypatch):
    def _raise_oserror(*_args, **_kwargs):
        raise OSError(errno.EPERM, "operation not permitted")

    monkeypatch.setattr("builtins.open", _raise_oserror)
    assert Base64Ref.from_path("/tmp/forbidden") is None


def test_base64_module_falls_back_to_yaml_safeloader(monkeypatch):
    import yaml as real_yaml

    import kapitan.refs.base64 as base64_module

    fake_yaml = types.ModuleType("yaml")
    fake_yaml.SafeLoader = real_yaml.SafeLoader
    fake_yaml.load = real_yaml.load

    module_path = Path(base64_module.__file__)
    temp_module_name = "kapitan.refs.base64_test_safeloader"

    monkeypatch.setitem(sys.modules, "yaml", fake_yaml)
    monkeypatch.delitem(sys.modules, temp_module_name, raising=False)

    spec = importlib.util.spec_from_file_location(temp_module_name, module_path)
    temp_module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(temp_module)

    assert temp_module.YamlLoader is real_yaml.SafeLoader
