#!/usr/bin/env python3

from kapitan.refs.env import DEFAULT_ENV_REF_VAR_PREFIX, EnvRef


def test_env_ref_compile(ref_controller):
    tag = "?{env:my/ref1_env}"
    ref_controller[tag] = EnvRef(b"ref 1 env data")
    ref_obj = ref_controller[tag]
    assert ref_obj.compile() == "?{env:my/ref1_env:877234e3}"


def test_env_ref_reveal_default(ref_controller):
    tag = "?{env:my/ref1_env}"
    ref_controller[tag] = EnvRef(b"ref 1 env data")
    ref_obj = ref_controller[tag]
    assert ref_obj.reveal() == "ref 1 env data"


def test_env_ref_reveal_from_env(ref_controller, monkeypatch):
    tag = "?{env:my/ref1_env}"
    ref_controller[tag] = EnvRef(b"ref 1 env data")
    ref_obj = ref_controller[tag]
    monkeypatch.setenv(
        f"{DEFAULT_ENV_REF_VAR_PREFIX}ref1_env", "ref 1 env data from EV"
    )
    assert ref_obj.reveal() == "ref 1 env data from EV"
