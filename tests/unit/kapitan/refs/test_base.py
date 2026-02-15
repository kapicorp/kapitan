# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

import base64
import errno
import importlib.util
import os
import string
import sys
import types
from pathlib import Path

import pytest

from kapitan.errors import RefError
from kapitan.refs.base import (
    PlainRef,
    PlainRefBackend,
    RefParams,
)
from kapitan.refs.base64 import Base64Ref
from kapitan.utils import get_entropy


def test_plain_ref_compile(ref_controller):
    tag = "?{plain:my/ref1_plain}"
    ref_controller[tag] = PlainRef(b"ref plain data")
    ref_obj = ref_controller[tag]
    assert ref_obj.compile() == "ref plain data"


def test_plain_ref_reveal(ref_controller):
    tag = "?{plain:my/ref2_plain}"
    ref_controller[tag] = PlainRef(b"ref 2 plain data")
    ref_obj = ref_controller[tag]
    assert ref_obj.reveal() == "ref 2 plain data"


def test_compile_subvars(ref_controller):
    subvar_tag1 = "?{base64:ref/subvars@var1}"
    subvar_tag2 = "?{base64:ref/subvars@var2}"
    ref_controller["?{base64:ref/subvars}"] = Base64Ref(b"ref 1 data")
    ref_obj1 = ref_controller[subvar_tag1]
    ref_obj2 = ref_controller[subvar_tag2]
    assert ref_obj1.compile() == "?{base64:ref/subvars@var1:4357a29b}"
    assert ref_obj2.compile() == "?{base64:ref/subvars@var2:4357a29b}"


def test_compile_embedded_subvar_path(ref_controller_embedded):
    subvar_tag = "?{base64:ref/subvars}"
    subvar_tag_var1 = "?{base64:ref/subvars@var1}"
    subvar_tag_var2 = "?{base64:ref/subvars@var2}"
    subvar_tag_var3 = "?{base64:ref/subvars@var3.var4}"
    ref_controller_embedded[subvar_tag] = Base64Ref(b"I am not yaml, just testing")
    ref_controller_embedded[subvar_tag_var1] = Base64Ref(b"I am not yaml, just testing")
    ref_controller_embedded[subvar_tag_var2] = Base64Ref(b"I am not yaml, just testing")
    ref_obj1 = ref_controller_embedded[subvar_tag_var1]
    ref_obj2 = ref_controller_embedded[subvar_tag_var2]
    ref_obj3 = ref_controller_embedded[subvar_tag_var3]

    assert ref_obj1.embed_refs is True
    assert ref_obj2.embed_refs is True
    assert ref_obj3.embed_refs is True

    ref_obj1 = ref_controller_embedded[ref_obj1.compile()]
    ref_obj2 = ref_controller_embedded[ref_obj2.compile()]
    ref_obj3 = ref_controller_embedded[ref_obj3.compile()]

    assert ref_obj1.embedded_subvar_path == "var1"
    assert ref_obj2.embedded_subvar_path == "var2"
    assert ref_obj3.embedded_subvar_path == "var3.var4"


def test_compile_embedded_subvars(ref_controller_embedded):
    subvar_tag = "?{base64:ref/subvars}"
    subvar_tag_var1 = "?{base64:ref/subvars@var1}"
    subvar_tag_var2 = "?{base64:ref/subvars@var2}"
    ref_controller_embedded[subvar_tag] = Base64Ref(b"I am not yaml, just testing")
    ref_controller_embedded[subvar_tag_var1] = Base64Ref(b"I am not yaml, just testing")
    ref_controller_embedded[subvar_tag_var2] = Base64Ref(b"I am not yaml, just testing")
    ref_obj1 = ref_controller_embedded[subvar_tag_var1]
    ref_obj2 = ref_controller_embedded[subvar_tag_var2]
    assert ref_obj1.compile() != ref_obj2.compile()


def test_reveal_subvars_raise_ref_error(ref_controller, revealer):
    tag_to_save = "?{base64:ref/subvars_error}"
    yaml_secret = b"this is not yaml"
    ref_controller[tag_to_save] = Base64Ref(yaml_secret)
    assert os.path.isfile(os.path.join(ref_controller.path, "ref/subvars_error"))

    with pytest.raises(RefError):
        tag_subvar = "?{base64:ref/subvars_error@var3.var4}"
        data = f"message here: {tag_subvar}"
        revealer.reveal_raw(data)


def test_reveal_subvars(ref_controller, revealer):
    tag_to_save = "?{base64:ref/subvars}"
    yaml_secret = b"""
    var1:
      var2: hello
    var3:
      var4: world
    """
    ref_controller[tag_to_save] = Base64Ref(yaml_secret)
    assert os.path.isfile(os.path.join(ref_controller.path, "ref/subvars"))

    tag_subvar = "?{base64:ref/subvars@var1.var2}"
    data = f"message here: {tag_subvar}"
    revealed_data = revealer.reveal_raw(data)
    assert revealed_data == "message here: hello"

    tag_subvar = "?{base64:ref/subvars@var3.var4}"
    data = f"message here: {tag_subvar}"
    revealed_data = revealer.reveal_raw(data)
    assert revealed_data == "message here: world"

    with pytest.raises(RefError):
        tag_subvar = "?{base64:ref/subvars@var3.varDoesntExist}"
        data = f"message here: {tag_subvar}"
        revealer.reveal_raw(data)


def test_reveal_embedded_subvars(ref_controller_embedded, revealer_embedded):
    tag_to_save = "?{base64:ref/subvars}"
    tag_var1 = "?{base64:ref/subvars@var1.var2}"
    tag_var2 = "?{base64:ref/subvars@var3.var4}"
    tag_var_doesnt_exist = "?{base64:ref/subvars@var3.varDoesntExist}"
    yaml_secret = b"""
    var1:
      var2: hello
    var3:
      var4: world
    """
    ref_controller_embedded[tag_to_save] = Base64Ref(yaml_secret)
    assert os.path.isfile(os.path.join(ref_controller_embedded.path, "ref/subvars"))

    ref_controller_embedded[tag_var1] = Base64Ref(yaml_secret)
    ref_controller_embedded[tag_var2] = Base64Ref(yaml_secret)
    ref_controller_embedded[tag_var_doesnt_exist] = Base64Ref(yaml_secret)

    ref_var1 = ref_controller_embedded[tag_var1]
    ref_var2 = ref_controller_embedded[tag_var2]
    ref_var_doesnt_exist = ref_controller_embedded[tag_var_doesnt_exist]

    data = f"message here: {ref_var1.compile()}"
    revealed_data = revealer_embedded.reveal_raw(data)
    assert revealed_data == "message here: hello"

    data = f"message here: {ref_var2.compile()}"
    revealed_data = revealer_embedded.reveal_raw(data)
    assert revealed_data == "message here: world"

    with pytest.raises(RefError):
        data = f"message here: {ref_var_doesnt_exist.compile()}"
        revealer_embedded.reveal_raw(data)


def test_ref_function_randomstr(ref_controller, revealer, tmp_path):
    tag = "?{base64:ref/randomstr||randomstr}"
    ref_controller[tag] = RefParams()
    file_exists = os.path.isfile(
        os.path.join(ref_controller.path, "ref/base64")
    ) or os.path.isfile(os.path.join(ref_controller.path, "ref/randomstr"))
    assert file_exists is True

    file_with_tags = tmp_path / "tags.txt"
    file_with_tags.write_text("?{base64:ref/randomstr}")
    revealed = revealer.reveal_raw_file(str(file_with_tags))
    assert len(revealed) == 43
    assert get_entropy(revealed) > 4

    tag = "?{base64:ref/randomstr||randomstr:16}"
    ref_controller[tag] = RefParams()
    revealer._reveal_tag_without_subvar.cache_clear()
    revealed = revealer.reveal_raw_file(str(file_with_tags))
    assert len(revealed) == 16


def test_ref_function_base64(ref_controller, revealer, tmp_path):
    tag = "?{base64:ref/base64||random:str|base64}"
    ref_controller[tag] = RefParams()
    assert os.path.isfile(os.path.join(ref_controller.path, "ref/base64"))

    file_with_tags = tmp_path / "tags.txt"
    file_with_tags.write_text("?{base64:ref/base64}")
    revealed = revealer.reveal_raw_file(str(file_with_tags))
    assert base64.b64decode(revealed) is not None


def test_ref_function_sha256(ref_controller, revealer, tmp_path):
    tag = "?{base64:ref/sha256||random:str|sha256}"
    ref_controller[tag] = RefParams()
    assert os.path.isfile(os.path.join(ref_controller.path, "ref/sha256"))

    file_with_tags = tmp_path / "tags.txt"
    file_with_tags.write_text("?{base64:ref/sha256}")
    revealed = revealer.reveal_raw_file(str(file_with_tags))
    assert len(revealed) == 64


def test_ref_function_random_loweralphanum(ref_controller, revealer, tmp_path):
    tag = "?{base64:ref/random_loweralphanum||random:loweralphanum}"
    ref_controller[tag] = RefParams()
    file_exists = os.path.isfile(
        os.path.join(ref_controller.path, "ref/base64")
    ) or os.path.isfile(os.path.join(ref_controller.path, "ref/random_loweralphanum"))
    assert file_exists is True

    file_with_tags = tmp_path / "tags.txt"
    file_with_tags.write_text("?{base64:ref/random_loweralphanum}")
    revealed = revealer.reveal_raw_file(str(file_with_tags))
    assert revealed.islower() is True
    assert revealed.isalnum() is True


def test_ref_function_random_upperalphanum(ref_controller, revealer, tmp_path):
    tag = "?{base64:ref/random_upperalphanum||random:upperalphanum}"
    ref_controller[tag] = RefParams()
    file_exists = os.path.isfile(
        os.path.join(ref_controller.path, "ref/base64")
    ) or os.path.isfile(os.path.join(ref_controller.path, "ref/random_upperalphanum"))
    assert file_exists is True

    file_with_tags = tmp_path / "tags.txt"
    file_with_tags.write_text("?{base64:ref/random_upperalphanum}")
    revealed = revealer.reveal_raw_file(str(file_with_tags))
    assert revealed.isupper() is True
    assert revealed.isalnum() is True


def test_ref_function_loweralpha(ref_controller, revealer, tmp_path):
    tag = "?{base64:ref/random_loweralpha||random:loweralpha}"
    ref_controller[tag] = RefParams()
    file_exists = os.path.isfile(
        os.path.join(ref_controller.path, "ref/base64")
    ) or os.path.isfile(os.path.join(ref_controller.path, "ref/random_loweralpha"))
    assert file_exists is True

    file_with_tags = tmp_path / "tags.txt"
    file_with_tags.write_text("?{base64:ref/random_loweralpha}")
    revealed = revealer.reveal_raw_file(str(file_with_tags))
    assert revealed.islower() is True
    assert revealed.isalpha() is True


def test_ref_function_upperalpha(ref_controller, revealer, tmp_path):
    tag = "?{base64:ref/random_upperalpha||random:upperalpha}"
    ref_controller[tag] = RefParams()
    file_exists = os.path.isfile(
        os.path.join(ref_controller.path, "ref/base64")
    ) or os.path.isfile(os.path.join(ref_controller.path, "ref/random_upperalpha"))
    assert file_exists is True

    file_with_tags = tmp_path / "tags.txt"
    file_with_tags.write_text("?{base64:ref/random_upperalpha}")
    revealed = revealer.reveal_raw_file(str(file_with_tags))
    assert revealed.isupper() is True
    assert revealed.isalpha() is True


def test_ref_function_randomint(ref_controller, revealer, tmp_path):
    tag = "?{base64:ref/randomint||random:int:6}"
    ref_controller[tag] = RefParams()
    assert os.path.isfile(os.path.join(ref_controller.path, "ref/randomint"))

    file_with_tags = tmp_path / "tags.txt"
    file_with_tags.write_text("?{base64:ref/randomint}")
    revealed = revealer.reveal_raw_file(str(file_with_tags))
    assert revealed.isdigit()
    assert len(revealed) == 6


def test_ref_function_special(ref_controller, revealer, tmp_path):
    tag = "?{base64:ref/special||random:special}"
    ref_controller[tag] = RefParams()
    assert os.path.isfile(os.path.join(ref_controller.path, "ref/special"))

    file_with_tags = tmp_path / "tags.txt"
    file_with_tags.write_text("?{base64:ref/special}")
    revealed = revealer.reveal_raw_file(str(file_with_tags))
    allowed = set(string.ascii_letters + string.digits + string.punctuation)
    assert revealed
    assert set(revealed).issubset(allowed)


def test_ref_function_basicauth(ref_controller, revealer, tmp_path):
    tag = "?{base64:ref/basicauth||basicauth:username:password}"
    ref_controller[tag] = RefParams()
    assert os.path.isfile(os.path.join(ref_controller.path, "ref/basicauth"))

    file_with_tags = tmp_path / "tags.txt"
    file_with_tags.write_text("?{base64:ref/basicauth}")
    revealed = revealer.reveal_raw_file(str(file_with_tags))
    assert base64.b64decode(revealed).decode() == "username:password"


def test_plain_ref_compile_embedded_subvar_branches():
    encoded_yaml = base64.b64encode(b"nested:\n  value: hello\n")
    ref_obj = PlainRef(
        encoded_yaml,
        encoding="base64",
        embedded_subvar_path="nested.value",
    )
    assert ref_obj.compile() == base64.b64encode(b"hello")

    not_yaml_ref = PlainRef(
        base64.b64encode(b"- item"),
        encoding="base64",
        embedded_subvar_path="nested.value",
    )
    with pytest.raises(RefError, match="not in embedded yaml"):
        not_yaml_ref.compile()

    missing_key_ref = PlainRef(
        encoded_yaml,
        encoding="base64",
        embedded_subvar_path="nested.missing",
    )
    with pytest.raises(RefError, match="cannot access sub-variable key"):
        missing_key_ref.compile()


def test_plain_ref_from_path_missing_file_returns_none(tmp_path):
    assert PlainRef.from_path(str(tmp_path / "does-not-exist")) is None


def test_base_module_falls_back_to_yaml_safeloader(monkeypatch):
    import yaml as real_yaml

    import kapitan.refs.base as base_module

    fake_yaml = types.ModuleType("yaml")
    fake_yaml.SafeLoader = real_yaml.SafeLoader
    fake_yaml.SafeDumper = real_yaml.SafeDumper
    fake_yaml.representer = real_yaml.representer
    fake_yaml.load = real_yaml.load
    fake_yaml.dump = real_yaml.dump
    fake_yaml.safe_dump = real_yaml.safe_dump
    fake_yaml.safe_load = real_yaml.safe_load

    module_path = Path(base_module.__file__)
    temp_module_name = "kapitan.refs.base_test_safeloader"

    monkeypatch.setitem(sys.modules, "yaml", fake_yaml)
    monkeypatch.delitem(sys.modules, temp_module_name, raising=False)

    spec = importlib.util.spec_from_file_location(temp_module_name, module_path)
    temp_module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(temp_module)

    assert temp_module.YamlLoader is real_yaml.SafeLoader


def test_plain_ref_non_enoent_and_unknown_encoding_branches(monkeypatch):
    def _raise_permission_error(*_args, **_kwargs):
        raise OSError(errno.EPERM, "permission denied")

    monkeypatch.setattr("builtins.open", _raise_permission_error)
    assert PlainRef.from_path("/tmp/forbidden") is None

    assert PlainRef.from_params("payload", RefParams(encoding="unsupported")) is None


def test_plain_ref_backend_iterates_empty_directory(tmp_path):
    backend = PlainRefBackend(str(tmp_path / "refs-empty"))
    assert list(backend) == []


def test_revealer_compile_raw_success_and_create_from_function(
    ref_controller, revealer
):
    ref_controller["?{plain:compile/path}"] = PlainRef(b"compiled")
    assert revealer.compile_raw("value ?{plain:compile/path}") == "value compiled"

    generated = revealer.compile_raw("?{base64:generated/path||random:str}")
    assert generated.startswith("?{base64:generated/path:")


def test_ref_controller_vault_key_validation_and_function_lookup_fallthrough(
    ref_controller,
):
    class _VaultToken:
        @staticmethod
        def split(_sep):
            return ["vaultkv", "path", "mount", "path/in/vault", None]

    with pytest.raises(RefError, match="key in vault is needed"):
        ref_controller._get_from_token(_VaultToken())

    with pytest.raises(KeyError, match="ref not found"):
        ref_controller["?{plain:missing:path:parts||random:str}"]
