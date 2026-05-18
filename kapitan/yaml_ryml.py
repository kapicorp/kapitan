#!/usr/bin/env python3
# Copyright 2026 The Kapitan Authors
# SPDX-FileCopyrightText: 2026 The Kapitan Authors <kapitan-admins@googlegroups.com>
# SPDX-License-Identifier: Apache-2.0
"""
High-performance YAML emitter backed by rapidyaml.

This module is an opt-in drop-in replacement for the PyYAML emitter used by
``kapitan.inputs.base.CompilingFile.write_yaml``. It is invoked when the user
passes ``--yaml-use-rapidyaml`` (or sets ``cached.args.yaml_use_rapidyaml``).

rapidyaml is a C++ YAML parser/emitter with a Python wrapper. Its emitter is
noticeably faster than both pure-Python PyYAML and the C ``libyaml`` backend,
because it works directly on a contiguous tree buffer instead of streaming
through a series of Python representer/emitter callbacks.

For Kubernetes-style manifests it produces output that matches Kapitan's
existing ``PrettyDumper`` byte-for-byte in the common case:

  * block sequences are indented (``a:\\n  - item``), matching ``PrettyDumper``;
  * multiline strings honor ``--yaml-multiline-string-style``
    (``literal`` / ``folded`` / ``double-quotes``);
  * ``None`` is emitted as ``null`` (or ``""`` with ``--yaml-dump-null-as-empty``);
  * sequence-at-top objects are emitted as multi-doc YAML, matching
    PyYAML's ``yaml.dump_all`` behaviour.

rapidyaml's emitter does not auto-quote string scalars that would be
mis-parsed as another scalar type (e.g. ``"true"`` or ``"123"`` would
round-trip as a bool / int). PyYAML's emitter does, via its
``Resolver.yaml_implicit_resolvers`` regex table.

We reuse that very table to detect ambiguous strings and force them to
single-quoted style, which guarantees round-trip fidelity with any
spec-compliant YAML parser.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any


try:
    import ryml  # type: ignore[import-not-found]

    HAS_RYML = True
except ImportError:  # pragma: no cover - the optional dep is missing
    ryml = None  # type: ignore[assignment]
    HAS_RYML = False

from yaml.resolver import Resolver as _PyYAMLResolver


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Ambiguous-string detection (reuses PyYAML's authoritative resolver table).
# ---------------------------------------------------------------------------
#
# ``_RESOLVERS_BY_CHAR`` maps a scalar's first character to the list of
# (tag, compiled-regex) pairs that PyYAML would use to *implicitly* resolve a
# plain scalar to a non-string type. We exclude the str-tag entries (they are
# the fallback). If any regex matches, the string would be re-parsed as the
# corresponding type and therefore needs explicit quoting in the YAML output.
_RESOLVERS_BY_CHAR: dict[str, list[tuple[str, Any]]] = {}
for _ch, _entries in _PyYAMLResolver.yaml_implicit_resolvers.items():
    if not _ch:
        # The empty-key entry is the catch-all for empty scalars; we handle
        # empty strings separately (ryml already quotes them correctly).
        continue
    _non_str = [
        (tag, regex) for tag, regex in _entries if tag != "tag:yaml.org,2002:str"
    ]
    if _non_str:
        _RESOLVERS_BY_CHAR[_ch] = _non_str


def _str_is_ambiguous(s: str) -> bool:
    """Return True if plain emission of ``s`` would round-trip as a non-string.

    Equivalent to PyYAML's ``Resolver.resolve`` returning a non-``str`` tag
    for ``s`` in plain style, but ~10x faster because it short-circuits on
    the first character and avoids the loader's full implicit-resolution
    machinery.
    """
    if not s:
        return False  # ryml emits "" for empty strings — that's fine.
    entries = _RESOLVERS_BY_CHAR.get(s[0])
    if entries is None:
        return False
    return any(regex.match(s) for _tag, regex in entries)


# ---------------------------------------------------------------------------
# Multiline style mapping. We mirror the choices accepted by
# ``--yaml-multiline-string-style``.
# ---------------------------------------------------------------------------
def _multiline_flag(style: str | None) -> int:
    """Return the ryml VAL_* style flag for a multiline string."""
    if ryml is None:
        return 0
    if style == "folded":
        return ryml.VAL_FOLDED
    if style == "double-quotes":
        return ryml.VAL_DQUO
    # "literal" is both the kapitan default and the safest choice (it
    # preserves exact bytes for things like shell scripts).
    return ryml.VAL_LITERAL


# ---------------------------------------------------------------------------
# Scalar conversion: Python value -> (string, ryml style flag).
#
# ryml is a string-only tree: every scalar leaf is text, and the *style* flag
# controls whether it's emitted plain, single-quoted, double-quoted, literal
# or folded. We encode Python's types here so PyYAML-compatible round-tripping
# is preserved.
# ---------------------------------------------------------------------------
def _scalar_for_ryml(
    value: Any,
    multiline_flag: int,
    null_repr: str,
) -> tuple[str, int]:
    """Convert a Python scalar to ``(text, style_flag)`` for ryml emission."""
    if value is None:
        # ``null_repr`` is either "null" (default) or "" when the user passed
        # --yaml-dump-null-as-empty. Both must be emitted *plain* so a
        # downstream parser resolves them to a null scalar, not the string.
        return null_repr, ryml.VAL_PLAIN  # type: ignore[union-attr]
    if value is True:
        return "true", ryml.VAL_PLAIN  # type: ignore[union-attr]
    if value is False:
        return "false", ryml.VAL_PLAIN  # type: ignore[union-attr]
    if isinstance(value, int):
        return str(value), ryml.VAL_PLAIN  # type: ignore[union-attr]
    if isinstance(value, float):
        # PyYAML uses 'repr' to preserve precision; do the same.
        return repr(value), ryml.VAL_PLAIN  # type: ignore[union-attr]
    if isinstance(value, bytes):
        # Match PyYAML SafeRepresenter: emit as a binary-tagged base64 blob.
        # Rare in kapitan output; we fall back to a safe representation.
        import base64

        return base64.b64encode(value).decode("ascii"), ryml.VAL_DQUO  # type: ignore[union-attr]
    if isinstance(value, str):
        if "\n" in value:
            return value, multiline_flag
        if _str_is_ambiguous(value):
            # Single-quotes are the cheapest safe quoting for plain strings
            # with no embedded special characters; ryml will pick double
            # quotes itself if escaping is required.
            return value, ryml.VAL_SQUO  # type: ignore[union-attr]
        # Let ryml decide (plain unless it needs quotes for chars like leading
        # whitespace, leading '-', embedded ': ', etc.).
        return value, 0
    # Fallback: stringify and force quoting so the type-tagged value at least
    # survives as a string.
    return str(value), ryml.VAL_SQUO  # type: ignore[union-attr]


def _key_for_ryml(key: Any) -> tuple[str, int]:
    """Like ``_scalar_for_ryml`` but for mapping keys (KEY_* flag variants)."""
    if key is None:
        return "null", ryml.KEY_PLAIN  # type: ignore[union-attr]
    if key is True:
        return "true", ryml.KEY_PLAIN  # type: ignore[union-attr]
    if key is False:
        return "false", ryml.KEY_PLAIN  # type: ignore[union-attr]
    if isinstance(key, int):
        return str(key), ryml.KEY_PLAIN  # type: ignore[union-attr]
    if isinstance(key, float):
        return repr(key), ryml.KEY_PLAIN  # type: ignore[union-attr]
    if isinstance(key, str):
        if _str_is_ambiguous(key) or "\n" in key:
            return key, ryml.KEY_SQUO  # type: ignore[union-attr]
        return key, 0
    return str(key), ryml.KEY_SQUO  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Arena pre-sizing.
#
# ``Tree.to_arena(s)`` copies ``s`` into an internal C++ buffer and returns a
# *view* (``csubstr``) into it. The buffer grows by realloc, which means any
# previously-returned view becomes a dangling pointer as soon as the arena
# grows. The corrupted views then surface as garbage scalars in the emitted
# YAML (e.g. ``"U: xxx..."`` instead of ``"k: xxx..."``) or, when the garbage
# bytes happen to be non-printable, as massive escape-expansion that
# overflows the emitter's output buffer with the error:
#
#   /project/cpp/src/c4/yml/./writer.hpp:144:
#       ERROR: [basic] not enough space in the given buffer
#
# We avoid that by walking ``obj`` once up front, summing the bytes we'll need
# in the arena, and calling ``Tree.reserve_arena(total)`` so the arena is
# allocated exactly once and never relocates during the build.
# ---------------------------------------------------------------------------
# Control characters that ryml's emitter does NOT escape, even with VAL_DQUO.
# Per the YAML 1.2 spec these characters MUST be escaped in any string scalar,
# so emitting them raw produces output that is rejected by spec-compliant
# parsers (including PyYAML's loader). We pre-scan ``obj`` and fall back to
# PyYAML when any string contains one of them.
# ASCII C0 controls minus \t (0x09), \n (0x0A), \r (0x0D); plus DEL (0x7F).
_CONTROL_RE = None


def _has_unescapable_controls(obj: Any) -> bool:
    """Return True if any string anywhere in ``obj`` contains a control char
    that ryml will refuse to escape."""
    global _CONTROL_RE
    if _CONTROL_RE is None:
        import re

        _CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
    stack: list = [obj]
    while stack:
        v = stack.pop()
        if isinstance(v, str):
            if _CONTROL_RE.search(v):
                return True
        elif isinstance(v, Mapping):
            for k, sv in v.items():
                if isinstance(k, str) and _CONTROL_RE.search(k):
                    return True
                stack.append(sv)
        elif isinstance(v, (list | tuple)):
            stack.extend(v)
    return False


def _estimate_arena(obj: Any) -> int:
    """Return an upper bound on the arena bytes needed to encode ``obj``.

    We over-estimate slightly (UTF-8 byte length per char, plus a small
    per-node constant) because over-reservation is cheap whereas
    under-reservation triggers a realloc and the dangling-pointer bug.
    """
    total = 0
    stack: list = [obj]
    while stack:
        v = stack.pop()
        if isinstance(v, Mapping):
            for k, sv in v.items():
                if isinstance(k, str):
                    total += len(k.encode("utf-8")) + 2
                else:
                    total += 24  # bool / int / float repr
                stack.append(sv)
        elif isinstance(v, (list | tuple)):
            stack.extend(v)
        elif isinstance(v, str):
            total += len(v.encode("utf-8")) + 2
        elif isinstance(v, bytes):
            # We base64-encode bytes; output is 4/3 the input rounded up.
            total += ((len(v) + 2) // 3) * 4 + 2
        elif v is None or isinstance(v, bool):
            total += 8
        else:
            total += 32  # int / float as text
    # 64-byte tail-padding for the rare case where a Python string is longer
    # in bytes than the UTF-8 estimate (it shouldn't be) or for the
    # built-in literal values ("true", "false", "null") added by
    # ``_scalar_for_ryml``.
    return total + 64


# ---------------------------------------------------------------------------
# Tree builder. We walk the Python object once, allocating ryml nodes as we go.
# ---------------------------------------------------------------------------
def _sorted_items(mapping: Mapping):
    """Return ``mapping.items()`` sorted alphabetically by key.

    Compiled outputs must be deterministic regardless of Python dict
    insertion order. This matches PyYAML's default ``sort_keys=True``
    behaviour, including its fallback to insertion order when keys have
    mixed/incomparable types (e.g. mixing ``str`` and ``int`` keys).
    """
    items = list(mapping.items())
    try:
        items.sort(key=lambda kv: kv[0])
    except TypeError:
        # Mixed/incomparable key types — keep insertion order, like PyYAML.
        pass
    return items


def _build(
    tree: ryml.Tree,
    node: int,
    value: Any,
    key: Any,
    has_key: bool,
    ml_flag: int,
    null_repr: str,
) -> None:
    """Populate ``node`` with ``value``.

    Args:
        tree: The ryml tree.
        node: The id of the (already-allocated) node to populate.
        value: The Python value to encode.
        key: Mapping key for this node, when applicable.
        has_key: Whether ``key`` is meaningful (this node is a map child).
        ml_flag: Pre-computed ``VAL_*`` flag for multiline strings.
        null_repr: ``"null"`` or ``""`` depending on yaml_dump_null_as_empty.
    """
    if isinstance(value, Mapping):
        if has_key:
            key_text, key_flag = _key_for_ryml(key)
            tree.to_map(node, key=tree.to_arena(key_text), more_flags=key_flag)
        else:
            tree.to_map(node)
        for k, v in _sorted_items(value):
            child = tree.append_child(node)
            _build(tree, child, v, k, True, ml_flag, null_repr)
        return

    if isinstance(value, (list | tuple)) or (
        isinstance(value, Sequence) and not isinstance(value, (str | bytes))
    ):
        if has_key:
            key_text, key_flag = _key_for_ryml(key)
            tree.to_seq(node, key=tree.to_arena(key_text), more_flags=key_flag)
        else:
            tree.to_seq(node)
        for item in value:
            child = tree.append_child(node)
            _build(tree, child, item, None, False, ml_flag, null_repr)
        return

    # Scalar leaf
    val_text, val_flag = _scalar_for_ryml(value, ml_flag, null_repr)
    val_arena = tree.to_arena(val_text)
    if has_key:
        key_text, key_flag = _key_for_ryml(key)
        tree.to_keyval(
            node,
            tree.to_arena(key_text),
            val_arena,
            more_flags=val_flag | key_flag,
        )
    else:
        tree.to_val(node, val_arena, more_flags=val_flag)


# ---------------------------------------------------------------------------
# Public entry point: emit ``obj`` to ``fp``.
# ---------------------------------------------------------------------------
def dump(
    obj: Any,
    fp,
    multiline_style: str | None = "literal",
    dump_null_as_empty: bool = False,
    multi_doc: bool = False,
) -> None:
    """Emit ``obj`` as YAML to file-like ``fp`` using rapidyaml.

    Args:
        obj: Object to serialize.
        fp: File-like object opened in text mode.
        multiline_style: One of ``"literal"``, ``"folded"``,
            ``"double-quotes"``. Anything else falls back to literal.
        dump_null_as_empty: When True, ``None`` is emitted as an empty
            scalar rather than ``null``.
        multi_doc: When True and ``obj`` is a sequence (list/tuple), emit
            each element as its own YAML document — matching PyYAML's
            ``yaml.dump_all`` semantics.

    Raises:
        RuntimeError: If rapidyaml is not installed.
    """
    if ryml is None:
        raise RuntimeError(
            "rapidyaml is not installed; install with `pip install rapidyaml`"
        )

    # rapidyaml does not escape ASCII control characters even in double-quoted
    # scalars (see comment above ``_has_unescapable_controls``). If the input
    # contains any, emit through PyYAML to keep output spec-compliant.
    if _has_unescapable_controls(obj):
        import yaml as _yaml

        from kapitan.utils import PrettyDumper as _PrettyDumper

        logger.debug(
            "yaml_ryml: object contains control characters; falling back to "
            "PyYAML for this document to ensure escaping."
        )
        dumper = _PrettyDumper.get_dumper_for_style(multiline_style)
        dump_fn = _yaml.dump if isinstance(obj, Mapping) else _yaml.dump_all
        dump_fn(
            obj,
            stream=fp,
            indent=2,
            Dumper=dumper,
            default_flow_style=False,
        )
        return

    ml_flag = _multiline_flag(multiline_style)
    null_repr = "" if dump_null_as_empty else "null"

    tree = ryml.Tree()
    # Reserve the arena up front so ``to_arena`` never reallocates while we
    # build the tree (see ``_estimate_arena`` for the rationale).
    tree.reserve_arena(_estimate_arena(obj))
    root = tree.root_id()

    if multi_doc and isinstance(obj, (list | tuple)):
        # Multi-document stream: one DOC per top-level item.
        tree.to_stream(root)
        for item in obj:
            doc = tree.append_child(root)
            # The child of a stream is a doc-node; ``to_*`` calls below set
            # both the container type *and* the DOC flag in one shot.
            if isinstance(item, Mapping):
                tree.to_map(doc, more_flags=ryml.DOC)
                for k, v in _sorted_items(item):
                    c = tree.append_child(doc)
                    _build(tree, c, v, k, True, ml_flag, null_repr)
            elif isinstance(item, (list | tuple)):
                tree.to_seq(doc, more_flags=ryml.DOC)
                for v in item:
                    c = tree.append_child(doc)
                    _build(tree, c, v, None, False, ml_flag, null_repr)
            else:
                val_text, val_flag = _scalar_for_ryml(item, ml_flag, null_repr)
                tree.to_val(
                    doc, tree.to_arena(val_text), more_flags=val_flag | ryml.DOC
                )
    else:
        _build(tree, root, obj, None, False, ml_flag, null_repr)

    out = _emit_tree(tree)
    # ``_emit_tree`` returns a ``str``; write directly to text streams, or
    # UTF-8 encode for binary streams.
    if "b" in getattr(fp, "mode", ""):
        fp.write(out.encode("utf-8"))
    else:
        fp.write(out)


def _emit_tree(tree: ryml.Tree) -> str:
    """Emit ``tree`` to a ``str``, sizing the output buffer correctly.

    ``ryml.emit_yaml`` / ``emit_yaml_malloc`` use an internal heuristic to
    pre-allocate the output buffer. For some trees (notably those with
    long double-quoted strings that require heavy escaping, or deeply
    nested structures with significant indentation overhead) the heuristic
    underestimates and ryml raises ``ExceptionBasic`` ("not enough space
    in the given buffer") instead of growing.

    To avoid that, we compute the exact required size via
    ``compute_yaml_length`` and emit into a correctly-sized buffer with
    ``emit_yaml_in_place``. A small slack is added as a defensive measure
    in case ``compute_yaml_length`` and the emitter ever disagree by a
    byte (they shouldn't, but the cost of slack is negligible).

    If anything still goes wrong we fall back to a doubling-buffer retry
    loop, so the user gets correct output rather than a crash.
    """
    needed = ryml.compute_yaml_length(tree)
    # +64 bytes of slack covers any potential off-by-one in the emitter's
    # length computation; it's a fixed-cost rounding error vs. the size of
    # the output, which is typically KBs to MBs.
    buf = bytearray(needed + 64)
    try:
        view = ryml.emit_yaml_in_place(tree, buf)
        return bytes(view).decode("utf-8")
    except IndexError as first_err:
        # ``compute_yaml_length`` disagreed with the emitter — should never
        # happen, but if it does, grow the buffer aggressively and retry.
        size = max(needed * 2, 65536)
        for _ in range(6):  # at most ~64x growth
            buf = bytearray(size)
            try:
                view = ryml.emit_yaml_in_place(tree, buf)
                logger.debug(
                    "yaml_ryml: emit succeeded after retry at buffer size %d "
                    "(compute_yaml_length reported %d)",
                    size,
                    needed,
                )
                return bytes(view).decode("utf-8")
            except IndexError:
                size *= 2
        # Re-raise the original error if every retry size failed.
        raise first_err
