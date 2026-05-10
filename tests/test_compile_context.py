#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for CompileContext isolation and contextvars-based scoping."""

import threading
from argparse import Namespace

from kapitan.context import (
    CompileContext,
    current_context,
    reset_context,
    set_current_context,
)


class TestCompileContextDefaults:
    def test_default_inv_is_empty_dict(self):
        ctx = CompileContext()
        assert ctx.inv == {}

    def test_default_global_inv_is_empty_dict(self):
        ctx = CompileContext()
        assert ctx.global_inv == {}

    def test_default_args_is_namespace(self):
        ctx = CompileContext()
        assert isinstance(ctx.args, Namespace)

    def test_default_inv_sources_is_empty_set(self):
        ctx = CompileContext()
        assert ctx.inv_sources == set()

    def test_default_secret_handlers_are_none(self):
        ctx = CompileContext()
        assert ctx.gpg_obj is None
        assert ctx.gkms_obj is None
        assert ctx.awskms_obj is None
        assert ctx.azkms_obj is None
        assert ctx.ref_controller_obj is None
        assert ctx.revealer_obj is None


class TestCompileContextIsolation:
    def test_two_contexts_have_independent_inv(self):
        ctx1 = CompileContext()
        ctx2 = CompileContext()
        ctx1.inv = {"target1": {"key": "value1"}}
        ctx2.inv = {"target2": {"key": "value2"}}
        assert ctx1.inv != ctx2.inv
        assert "target1" not in ctx2.inv
        assert "target2" not in ctx1.inv

    def test_mutable_fields_are_not_shared_between_instances(self):
        """Each CompileContext must own its own mutable defaults, not share them."""
        ctx1 = CompileContext()
        ctx2 = CompileContext()
        ctx1.inv["shared_key"] = "oops"
        assert "shared_key" not in ctx2.inv

    def test_inv_sources_are_not_shared(self):
        ctx1 = CompileContext()
        ctx2 = CompileContext()
        ctx1.inv_sources.add("path/to/inventory")
        assert "path/to/inventory" not in ctx2.inv_sources

    def test_args_mutation_does_not_affect_other_contexts(self):
        ctx1 = CompileContext()
        ctx2 = CompileContext()
        ctx1.args.output_path = "/tmp/ctx1"
        assert not hasattr(ctx2.args, "output_path")

    def test_ref_controller_assignment_is_independent(self):
        ctx1 = CompileContext()
        ctx2 = CompileContext()
        sentinel = object()
        ctx1.ref_controller_obj = sentinel
        assert ctx2.ref_controller_obj is None


class TestContextVarScoping:
    def teardown_method(self):
        """Ensure no context leaks between tests."""
        # Reset to no active context after each test
        from kapitan import context as ctx_module

        ctx_module._current_context.set(None)

    def test_no_context_by_default(self):
        from kapitan import context as ctx_module

        ctx_module._current_context.set(None)
        assert current_context() is None

    def test_set_and_retrieve_context(self):
        ctx = CompileContext()
        ctx.inv = {"target": {"data": 42}}
        token = set_current_context(ctx)
        try:
            assert current_context() is ctx
            assert current_context().inv["target"]["data"] == 42
        finally:
            reset_context(token)

    def test_reset_restores_previous_context(self):
        from kapitan import context as ctx_module

        ctx_module._current_context.set(None)
        ctx1 = CompileContext()
        ctx1.inv = {"level": 1}

        token1 = set_current_context(ctx1)
        assert current_context() is ctx1

        ctx2 = CompileContext()
        ctx2.inv = {"level": 2}
        token2 = set_current_context(ctx2)
        assert current_context() is ctx2

        reset_context(token2)
        assert current_context() is ctx1

        reset_context(token1)
        assert current_context() is None

    def test_context_is_independent_per_thread(self):
        """Each thread starts with its own ContextVar snapshot."""
        results: dict[str, dict] = {}
        barrier = threading.Barrier(2)

        def run(name: str, inv_value: str) -> None:
            ctx = CompileContext()
            ctx.inv = {name: inv_value}
            token = set_current_context(ctx)
            barrier.wait()  # ensure both threads set their context simultaneously
            results[name] = dict(current_context().inv)
            reset_context(token)

        t1 = threading.Thread(target=run, args=("t1", "value1"))
        t2 = threading.Thread(target=run, args=("t2", "value2"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert results["t1"] == {"t1": "value1"}
        assert results["t2"] == {"t2": "value2"}


class TestCompileContextPicklability:
    """CompileContext must be picklable so multiprocessing can pass it to workers."""

    def test_basic_context_is_picklable(self):
        import pickle

        ctx = CompileContext()
        ctx.inv = {"target": {"key": "value"}}
        ctx.args = Namespace(output_path="/tmp/out", targets=["target"])
        ctx.inv_sources = {"path/to/inventory"}

        dumped = pickle.dumps(ctx)
        loaded = pickle.loads(dumped)

        assert loaded.inv == ctx.inv
        assert loaded.args.output_path == "/tmp/out"
        assert loaded.inv_sources == {"path/to/inventory"}


class TestLibraryModeIsolation:
    """
    Verify that two independent compile contexts back-to-back do not bleed state,
    simulating embedded (library-mode) usage of Kapitan.
    """

    def test_sequential_contexts_do_not_bleed_inv(self):
        ctx_a = CompileContext()
        ctx_a.inv = {"target_a": {"param": "alpha"}}

        token_a = set_current_context(ctx_a)
        assert current_context().inv == {"target_a": {"param": "alpha"}}
        reset_context(token_a)

        ctx_b = CompileContext()
        ctx_b.inv = {"target_b": {"param": "beta"}}

        token_b = set_current_context(ctx_b)
        assert current_context().inv == {"target_b": {"param": "beta"}}
        reset_context(token_b)

        assert current_context() is None

    def test_sequential_contexts_do_not_bleed_secret_handlers(self):
        sentinel_a = object()
        ctx_a = CompileContext()
        ctx_a.ref_controller_obj = sentinel_a

        token_a = set_current_context(ctx_a)
        assert current_context().ref_controller_obj is sentinel_a
        reset_context(token_a)

        ctx_b = CompileContext()
        token_b = set_current_context(ctx_b)
        assert current_context().ref_controller_obj is None
        reset_context(token_b)
