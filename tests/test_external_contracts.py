#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""API stability tests for external consumers.

These tests encode the stable public-ish API surface that downstream tools
rely on when embedding Kapitan as a library. They are not tests of internal
implementation details — they exercise the *contracts* that must hold across
Kapitan releases so that external orchestrators do not break.
"""

from __future__ import annotations

import os
from argparse import Namespace

import pytest

import kapitan.cached
from kapitan.cached import reset_cache
from kapitan.cli import build_parser
from kapitan.defaults import DEFAULT_JINJA2_FILTERS_PATH
from kapitan.inventory import InventoryBackends
from kapitan.resources import inventory as get_inventory
from kapitan.targets import compile_targets, load_target_inventory
from tests.test_helpers import IsolatedTestEnvironment


RECLASS_EXAMPLE_PATH = os.path.join(os.getcwd(), "examples", "reclass")


def _library_style_args(**overrides):
    """Build an args namespace matching the shape external tools set.

    Downstream orchestrators (e.g. Commodore, custom wrappers) populate
    ~20 attributes on ``cached.args`` before calling ``compile_targets()``.
    This helper produces a namespace with the same shape so that changes to
    attribute names or required defaults are caught immediately.
    """
    args = Namespace(
        inventory_backend=InventoryBackends.RECLASS_RS,
        inventory_path="./inventory",
        output_path=".",
        targets=None,
        labels=None,
        parallelism=None,
        prune=False,
        indent=2,
        reveal=False,
        fetch=False,
        force_fetch=False,
        force=False,
        validate=False,
        schemas_path="./schemas",
        jinja2_filters=DEFAULT_JINJA2_FILTERS_PATH,
        use_go_jsonnet=False,
        multiline_string_style="literal",
        yaml_dump_null_as_empty=False,
        verbose=False,
        inventory_pool_cache=True,
        cache=False,
        embed_refs=False,
        ignore_version_check=False,
        yaml_use_rapidyaml=False,
        refs_path="./refs",
        search_paths=["."],
        compose_target_name=False,
        compose_node_name=False,  # deprecated but still referenced by wrappers
        profile_serial=False,
    )
    for key, value in overrides.items():
        setattr(args, key, value)
    return args


class TestCachedArgsContract:
    """Tests that ``cached.args`` accepts the namespace shape external tools build."""

    def test_library_style_args_namespace(self):
        """Building a library-style namespace should not raise."""
        args = _library_style_args()
        assert args.inventory_backend == InventoryBackends.RECLASS_RS
        assert args.jinja2_filters == DEFAULT_JINJA2_FILTERS_PATH

    def test_compile_targets_accepts_library_args(self):
        """compile_targets() must accept the kwargs external tools pass."""
        with IsolatedTestEnvironment(RECLASS_EXAMPLE_PATH) as iso:
            args = _library_style_args(
                inventory_path="inventory",
                output_path=iso.path,
                targets=["compile-test"],
            )
            kapitan.cached.args = args
            reset_cache()

            # Downstream tools pass these four positional args to compile_targets()
            compile_targets(
                inventory_path=args.inventory_path,
                search_paths=[iso.path],
                ref_controller=None,
                args=args,
            )

            # Output directory structure contract
            compiled = os.path.join(iso.path, "compiled", "compile-test")
            assert os.path.isdir(compiled), "compiled/<target>/ should exist"

    def test_compile_targets_with_all_defaults(self):
        """Compile all targets when ``args.targets`` is None."""
        with IsolatedTestEnvironment(RECLASS_EXAMPLE_PATH) as iso:
            args = _library_style_args(
                inventory_path="inventory",
                output_path=iso.path,
            )
            kapitan.cached.args = args
            reset_cache()

            compile_targets(
                inventory_path=args.inventory_path,
                search_paths=[iso.path],
                ref_controller=None,
                args=args,
            )

            # All three reclass targets should be compiled
            for target in ("simple", "advanced", "compile-test"):
                compiled = os.path.join(iso.path, "compiled", target)
                assert os.path.isdir(compiled), f"compiled/{target}/ should exist"


class TestCompileTargetsSignatureContract:
    """Tests that ``compile_targets()`` signature and behavior remain stable."""

    def test_compile_targets_keyword_arg_contract(self):
        """compile_targets() must accept keyword args named:
        inventory_path, search_paths, ref_controller, args.
        """
        with IsolatedTestEnvironment(RECLASS_EXAMPLE_PATH) as iso:
            args = _library_style_args(
                inventory_path="inventory",
                output_path=iso.path,
                targets=["simple"],
            )
            kapitan.cached.args = args
            reset_cache()

            # This is the exact call pattern external tools use
            compile_targets(
                inventory_path=args.inventory_path,
                search_paths=[iso.path],
                ref_controller=None,
                args=args,
            )

    def test_load_target_inventory_returns_list(self):
        """load_target_inventory() must return a list of target objects."""
        with IsolatedTestEnvironment(RECLASS_EXAMPLE_PATH) as iso:
            args = _library_style_args(
                inventory_path="inventory",
            )
            kapitan.cached.args = args
            reset_cache()

            # get_inventory returns a dict; load_target_inventory expects
            # an Inventory instance, so instantiate the backend directly.
            from kapitan.inventory import get_inventory_backend

            backend = get_inventory_backend(args.inventory_backend)
            inv = backend(
                inventory_path="inventory",
                compose_target_name=args.compose_target_name,
                ignore_class_not_found=False,
            )
            targets = load_target_inventory(inv, ["simple"])
            assert isinstance(targets, list)
            assert len(targets) == 1
            assert targets[0].vars.target == "simple"

    def test_load_target_inventory_empty_targets_returns_all(self):
        """load_target_inventory() with an empty target list must return
        all targets (same as ``None``).
        """
        with IsolatedTestEnvironment(RECLASS_EXAMPLE_PATH) as iso:
            args = _library_style_args(inventory_path="inventory")
            kapitan.cached.args = args
            reset_cache()

            from kapitan.inventory import get_inventory_backend

            backend = get_inventory_backend(args.inventory_backend)
            inv = backend(
                inventory_path="inventory",
                compose_target_name=args.compose_target_name,
                ignore_class_not_found=False,
            )
            targets = load_target_inventory(inv, [])
            assert len(targets) == 3  # simple, advanced, compile-test


class TestRefControllerContract:
    """Tests for ``RefController`` API stability."""

    def test_ref_controller_constructor(self, temp_dir):
        """RefController(path) must instantiate without error."""
        from kapitan.refs.base import RefController

        refs_dir = os.path.join(temp_dir, "refs")
        os.makedirs(refs_dir)
        rc = RefController(refs_dir)
        assert rc.path == refs_dir

    def test_ref_controller_register_backend(self, temp_dir):
        """register_backend() must accept a PlainRefBackend subclass."""
        from kapitan.refs.base import PlainRef, PlainRefBackend, RefController

        refs_dir = os.path.join(temp_dir, "refs")
        os.makedirs(refs_dir)
        rc = RefController(refs_dir)

        class FakeBackend(PlainRefBackend):
            def __init__(self, path, **kwargs):
                self.path = path
                self.type_name = "fake"

            def reveal(self, ref_tag):
                return "fake-secret"

            def new_ref(self, key, ref_params):
                return PlainRef(key, "fake-data")

        backend = FakeBackend(refs_dir)
        rc.register_backend(backend)
        assert "fake" in rc.backends


class TestResetCacheContract:
    """Tests that ``reset_cache()`` clears state without side effects."""

    def test_multiple_compile_invocations_in_process(self):
        """Multiple ``compile_targets()`` calls in one process must not leak."""
        with IsolatedTestEnvironment(RECLASS_EXAMPLE_PATH) as iso:
            for target in ("simple", "compile-test"):
                args = _library_style_args(
                    inventory_path="inventory",
                    output_path=iso.path,
                    targets=[target],
                )
                kapitan.cached.args = args
                reset_cache()

                compile_targets(
                    inventory_path=args.inventory_path,
                    search_paths=[iso.path],
                    ref_controller=None,
                    args=args,
                )

                compiled = os.path.join(iso.path, "compiled", target)
                assert os.path.isdir(compiled)

    def test_compile_targets_nonexistent_target_raises(self):
        """Requesting a target that does not exist must raise CompileError."""
        from kapitan.errors import CompileError

        with IsolatedTestEnvironment(RECLASS_EXAMPLE_PATH) as iso:
            args = _library_style_args(
                inventory_path="inventory",
                output_path=iso.path,
                targets=["does-not-exist"],
            )
            kapitan.cached.args = args
            reset_cache()

            with pytest.raises(CompileError):
                compile_targets(
                    inventory_path=args.inventory_path,
                    search_paths=[iso.path],
                    ref_controller=None,
                    args=args,
                )

    def test_compile_targets_parallelism_one(self):
        """compile_targets() must work when ``args.parallelism`` is 1."""
        with IsolatedTestEnvironment(RECLASS_EXAMPLE_PATH) as iso:
            args = _library_style_args(
                inventory_path="inventory",
                output_path=iso.path,
                targets=["simple"],
                parallelism=1,
            )
            kapitan.cached.args = args
            reset_cache()

            compile_targets(
                inventory_path=args.inventory_path,
                search_paths=[iso.path],
                ref_controller=None,
                args=args,
            )

            compiled = os.path.join(iso.path, "compiled", "simple")
            assert os.path.isdir(compiled)

    def test_backend_switch_in_same_process(self):
        """Switching inventory backends in the same process must not leak
        cached state from the previous backend.
        """
        import importlib

        if not importlib.util.find_spec("reclass"):
            pytest.skip("reclass not available")
        if not importlib.util.find_spec("reclass_rs"):
            pytest.skip("reclass_rs not available")

        with IsolatedTestEnvironment(RECLASS_EXAMPLE_PATH) as iso:
            # First compile with reclass
            args_reclass = _library_style_args(
                inventory_backend=InventoryBackends.RECLASS,
                inventory_path="inventory",
                output_path=iso.path,
                targets=["simple"],
            )
            kapitan.cached.args = args_reclass
            reset_cache()
            compile_targets(
                inventory_path="inventory",
                search_paths=[iso.path],
                ref_controller=None,
                args=args_reclass,
            )

            # Then compile with reclass-rs in same process
            args_rs = _library_style_args(
                inventory_backend=InventoryBackends.RECLASS_RS,
                inventory_path="inventory",
                output_path=iso.path,
                targets=["simple"],
            )
            kapitan.cached.args = args_rs
            reset_cache()
            compile_targets(
                inventory_path="inventory",
                search_paths=[iso.path],
                ref_controller=None,
                args=args_rs,
            )

            assert os.path.isdir(os.path.join(iso.path, "compiled", "simple"))


class TestOutputDirectoryStructureContract:
    """Tests for the compiled output directory layout."""

    def test_compiled_output_contains_target_dirs(self):
        """After compile, ``compiled/<target-name>/`` must exist."""
        with IsolatedTestEnvironment(RECLASS_EXAMPLE_PATH) as iso:
            args = _library_style_args(
                inventory_path="inventory",
                output_path=iso.path,
            )
            kapitan.cached.args = args
            reset_cache()

            compile_targets(
                inventory_path=args.inventory_path,
                search_paths=[iso.path],
                ref_controller=None,
                args=args,
            )

            compiled_root = os.path.join(iso.path, "compiled")
            assert os.path.isdir(compiled_root)

            for target in ("simple", "advanced", "compile-test"):
                target_dir = os.path.join(compiled_root, target)
                assert os.path.isdir(target_dir), f"missing {target_dir}"


class TestInventoryBackendContract:
    """Tests for inventory backend output shape stability."""

    @pytest.mark.parametrize(
        "backend_id", [InventoryBackends.RECLASS, InventoryBackends.RECLASS_RS]
    )
    def test_inventory_returns_dict_with_parameters(self, backend_id):
        """inventory() must return a dict where each target contains
        parameters.
        """
        import importlib

        module = backend_id.replace("-", "_")
        if not importlib.util.find_spec(module):
            pytest.skip(f"backend module {module} not available")

        args = build_parser().parse_args(["compile"])
        args.inventory_backend = backend_id
        kapitan.cached.args = args
        reset_cache()

        try:
            inv = get_inventory(
                inventory_path=os.path.join(RECLASS_EXAMPLE_PATH, "inventory")
            )
            assert isinstance(inv, dict)
            for target_name, target_data in inv.items():
                assert "parameters" in target_data, f"{target_name} missing parameters"
        finally:
            reset_cache()
            kapitan.cached.args = build_parser().parse_args(["compile"])

    @pytest.mark.parametrize(
        "backend_id", [InventoryBackends.RECLASS, InventoryBackends.RECLASS_RS]
    )
    def test_inventory_target_name_attribute(self, backend_id):
        """_kapitan_.name.short (or reclass equivalent) must resolve."""
        import importlib

        module = backend_id.replace("-", "_")
        if not importlib.util.find_spec(module):
            pytest.skip(f"backend module {module} not available")

        args = build_parser().parse_args(["compile"])
        args.inventory_backend = backend_id
        kapitan.cached.args = args
        reset_cache()

        try:
            inv = get_inventory(
                inventory_path=os.path.join(RECLASS_EXAMPLE_PATH, "inventory"),
                target_name="compile-test",
            )
            params = inv["parameters"]
            assert params["target_name"] == "compile-test"
        finally:
            reset_cache()
            kapitan.cached.args = build_parser().parse_args(["compile"])


class TestRefsContract:
    """Tests for refs/secrets API stability (consumed by admission controllers
    and other tools that reveal refs outside the compile pipeline).
    """

    def test_ref_token_tag_pattern_matches_valid_tags(self):
        """REF_TOKEN_TAG_PATTERN must match standard ref tags."""
        import re

        from kapitan.refs.base import REF_TOKEN_TAG_PATTERN

        pattern = re.compile(REF_TOKEN_TAG_PATTERN)
        valid = [
            "?{gpg:my/secret}",
            "?{vaultkv:path/to/secret}",
            "?{plain:simple/ref}",
            "?{env:MY_VAR}",
            "?{base64:encoded/ref}",
            "?{gkms:projects/my-project/locations/global/keyRings/...}",
        ]
        for tag in valid:
            assert pattern.search(tag), f"should match {tag}"

    def test_ref_token_tag_pattern_rejects_invalid_tags(self):
        """REF_TOKEN_TAG_PATTERN must not match strings that are not refs."""
        import re

        from kapitan.refs.base import REF_TOKEN_TAG_PATTERN

        pattern = re.compile(REF_TOKEN_TAG_PATTERN)
        invalid = [
            "not-a-ref",
            "{plain:ref}",
            "?{plain}",
            "?{unknown}",
        ]
        for tag in invalid:
            assert not pattern.search(tag), f"should not match {tag}"

    def test_revealer_embedded_refs(self, temp_dir):
        """Revealer with embed_refs=True must resolve embedded refs."""
        from kapitan.refs.base import PlainRef, RefController, Revealer

        refs_dir = os.path.join(temp_dir, "refs")
        os.makedirs(refs_dir)
        rc = RefController(refs_dir, embed_refs=True)
        revealer = Revealer(rc)

        tag = "?{plain:embedded/ref1}"
        rc[tag] = PlainRef(b"secret-value")

        obj = {"password": tag}
        revealed = revealer.reveal_obj(obj)
        assert revealed["password"] == "secret-value"

    def test_revealer_leaves_plain_strings_untouched(self):
        """Revealer must not modify strings that contain no ref tags."""
        from kapitan.refs.base import RefController, Revealer

        rc = RefController("/tmp")
        revealer = Revealer(rc)

        obj = {"message": "hello world", "number": 42}
        revealed = revealer.reveal_obj(obj)
        assert revealed["message"] == "hello world"
        assert revealed["number"] == 42

    def test_ref_controller_missing_ref_raises_keyerror(self, temp_dir):
        """Accessing a non-existent ref must raise KeyError."""
        from kapitan.refs.base import RefController

        refs_dir = os.path.join(temp_dir, "refs")
        os.makedirs(refs_dir)
        rc = RefController(refs_dir)

        with pytest.raises(KeyError):
            _ = rc["?{plain:does/not/exist}"]

    def test_plain_ref_with_unicode(self):
        """PlainRef must handle Unicode data correctly."""
        from kapitan.refs.base import PlainRef

        ref = PlainRef("unicode: éàü")
        assert ref.reveal() == "unicode: éàü"


class TestKadetContract:
    """Tests for Kadet input API stability (consumed by generators and
    component authors).
    """

    def test_kadet_inventory_api(self):
        """inventory() and BaseObj must remain importable and functional."""
        from kapitan.inputs.kadet import BaseObj, Dict, inventory

        # BaseObj is the main entry point for Kadet components
        assert callable(inventory)
        assert callable(BaseObj)
        assert callable(Dict)
