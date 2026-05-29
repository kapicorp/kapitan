#!/usr/bin/env python3
"""Verify MkDocs Markdown extensions render fenced code blocks correctly.

When pymdownx.superfences fails to interact properly with the markdown package,
fenced code blocks (e.g.  ```yaml, ```tree) silently render as inline text in <p>
tags instead of <pre><code> elements. This test catches that regression.
"""

import markdown
import pytest


# Extensions loaded in mkdocs.yml (simplified set; superfences is the critical one)
MKDOCS_MARKDOWN_EXTENSIONS = [
    "md_in_html",
    "admonition",
    "pymdownx.tabbed",
    "pymdownx.superfences",
    "pymdownx.arithmatex",
    "pymdownx.betterem",
    "pymdownx.caret",
    "pymdownx.critic",
    "pymdownx.details",
    "pymdownx.snippets",
    "pymdownx.emoji",
    "pymdownx.inlinehilite",
    "pymdownx.magiclink",
    "pymdownx.mark",
    "pymdownx.smartsymbols",
    "pymdownx.tasklist",
    "pymdownx.tilde",
    "markdown_include.include",
    "attr_list",
    "abbr",
]

FENCED_BLOCK_CASES = [
    # yaml and plain are handled by pymdownx.superfences; mermaid uses a custom fence.
    # tree blocks are handled by the markdown-exec mkdocs plugin and are not tested here.
    (
        "yaml_block",
        "```yaml\n# inventory/targets/production.yaml\nclasses:\n  - common\n```",
    ),
    (
        "mermaid_block",
        "```mermaid\ngraph LR\n    A --> B\n```",
    ),
    (
        "plain_code_block",
        "```\n$ kapitan compile\nCompiled 200 targets\n```",
    ),
]


@pytest.fixture(scope="module")
def md():
    return markdown.Markdown(extensions=MKDOCS_MARKDOWN_EXTENSIONS)


@pytest.mark.parametrize(("name", "source"), FENCED_BLOCK_CASES)
def test_fenced_block_renders(md, name, source):
    md.reset()
    html = md.convert(source)
    assert "<pre" in html, f"Expected <pre> in rendered HTML, got: {html[:200]}"
    assert "```" not in html, f"Literal backticks leaked into HTML: {html[:200]}"
