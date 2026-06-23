#!/usr/bin/env python3
"""Verify MkDocs Markdown extensions render fenced code blocks correctly.

When pymdownx.superfences fails to interact properly with the markdown package,
fenced code blocks (e.g.  ```yaml, ```tree) silently render as inline text in <p>
tags instead of <pre><code> elements. This test catches that regression.

Also enforces a baseline of SEO frontmatter (title + description, within the
length bounds search engines actually use) on every docs page.
"""

import pathlib
import re

import markdown
import pytest
import yaml


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


# --- SEO frontmatter enforcement -------------------------------------------
#
# Every docs page must carry a title and description in its YAML frontmatter,
# sized to the limits search engines respect: titles get truncated in results
# around ~60 chars, meta descriptions around ~160. Too-short values waste the
# slot. New pages that skip frontmatter fail here instead of shipping invisible
# to search.

DOCS_DIR = pathlib.Path(__file__).resolve().parent.parent / "docs"
DOCS_PAGES_DIR = DOCS_DIR / "pages"

TITLE_MIN, TITLE_MAX = 30, 65
DESCRIPTION_MIN, DESCRIPTION_MAX = 50, 160

# Top-level docs pages (homepage + nav entries) that the original gate skipped
# but that search engines actually crawl. tags.md is a generated tag-index
# placeholder ([TAGS]) with no prose of its own, so it is excluded.
TOP_LEVEL_EXCLUDE = {"tags.md"}

# Matches a leading YAML frontmatter block. MkDocs only recognises frontmatter
# when it is the very first thing in the file, so anchor at the start.
_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


def _docs_pages():
    pages = set(DOCS_PAGES_DIR.rglob("*.md"))
    pages.update(p for p in DOCS_DIR.glob("*.md") if p.name not in TOP_LEVEL_EXCLUDE)
    return sorted(pages)


def _page_id(path):
    return str(path.relative_to(DOCS_DIR))


def _parse_frontmatter(text):
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None
    data = yaml.safe_load(match.group(1))
    return data if isinstance(data, dict) else {}


@pytest.mark.parametrize("page", _docs_pages(), ids=_page_id)
def test_docs_page_has_seo_frontmatter(page):
    frontmatter = _parse_frontmatter(page.read_text(encoding="utf-8"))
    rel = _page_id(page)

    assert (
        frontmatter is not None
    ), f"{rel}: missing a YAML frontmatter block (---) at the very top of the file"

    title = frontmatter.get("title")
    assert isinstance(title, str), f"{rel}: missing 'title' in frontmatter"
    assert title.strip(), f"{rel}: empty 'title' in frontmatter"
    assert (
        TITLE_MIN <= len(title) <= TITLE_MAX
    ), f"{rel}: title is {len(title)} chars, must be {TITLE_MIN}-{TITLE_MAX}: {title!r}"

    description = frontmatter.get("description")
    assert isinstance(description, str), f"{rel}: missing 'description' in frontmatter"
    assert description.strip(), f"{rel}: empty 'description' in frontmatter"
    assert DESCRIPTION_MIN <= len(description) <= DESCRIPTION_MAX, (
        f"{rel}: description is {len(description)} chars, "
        f"must be {DESCRIPTION_MIN}-{DESCRIPTION_MAX}: {description!r}"
    )
