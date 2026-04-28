"""Legal pages — TC-BUG-LEGAL-001 регрессия.

/privacy and /terms must render rendered HTML, not raw markdown. Closed
in commit f3a9d48 per docs/test-plan.md — guard against regression.
"""

from __future__ import annotations

import httpx
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.parametrize("path", ["/privacy", "/terms"])
def test_legal_renders_html_not_raw_markdown(page: Page, base_url: str, path: str):
    """TC-BUG-LEGAL-001: privacy/terms must be rendered HTML."""
    response = page.goto(path)
    assert response is not None
    assert response.status == 200
    content_type = (response.headers.get("content-type") or "").lower()
    assert "text/html" in content_type, f"{path} content-type={content_type!r}, expected text/html"

    # Document must have a non-empty title (raw .md doesn't set one).
    title = page.title()
    assert title and title.strip(), f"{path} has empty title"

    # Must have at least one <h1>/<h2> in the rendered DOM.
    h1_count = page.locator("h1, h2").count()
    assert h1_count > 0, f"{path} has no <h1>/<h2> headings — looks like raw markdown"

    # The body must NOT contain literal markdown markers like '# ' at line
    # start (rendered headings have no leading '#').
    body_text = page.locator("body").text_content() or ""
    lines = body_text.split("\n")
    md_marker_lines = [ln for ln in lines if ln.strip().startswith(("# ", "## ", "### "))]
    assert not md_marker_lines, f"{path} leaks raw markdown lines: {md_marker_lines[:3]}"


@pytest.mark.parametrize("path", ["/privacy", "/terms"])
def test_legal_has_no_unrendered_markdown_links(page: Page, path: str):
    """`[text](url)` syntax must not appear in rendered body."""
    page.goto(path)
    page.wait_for_load_state("domcontentloaded")
    body = page.locator("body").text_content() or ""
    import re
    md_links = re.findall(r"\[[^\]]+\]\([^\)]+\)", body)
    assert not md_links, f"{path} has unrendered MD links: {md_links[:3]}"
