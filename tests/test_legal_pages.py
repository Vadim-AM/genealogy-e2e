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


# ─────────────────────────────────────────────────────────────────────────
# TC-24.03 — Footer links на /privacy и /terms видны и open в новой вкладке
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("href", ["/privacy", "/terms"])
def test_landing_footer_legal_link_is_visible_and_target_blank(
    page: Page, href: str,
):
    """TC-24.03: footer на / содержит link на /privacy и /terms; target=_blank
    чтобы юзер не терял состояние tree/orbit при чтении legal text.

    Селектор по href — устойчив к смене label'ов и i18n.
    """
    page.goto("/")
    page.wait_for_load_state("domcontentloaded")
    link = page.locator(f"a[href='{href}']").first
    expect(link).to_be_visible()
    target = link.get_attribute("target")
    assert target == "_blank", (
        f"footer link {href} должен иметь target=_blank, чтобы не терять "
        f"состояние страницы; got target={target!r}"
    )


@pytest.mark.parametrize("href", ["/privacy", "/terms"])
def test_landing_footer_legal_link_resolves_to_200(
    base_url: str, href: str,
):
    """TC-24.03: переход по footer-link реально возвращает 200 + HTML
    (защита от битой ссылки). httpx — открывать новую tab через
    Playwright ради этого избыточно.
    """
    response = httpx.get(f"{base_url}{href}", follow_redirects=True, timeout=10)
    assert response.status_code == 200, (
        f"footer link {href} returned {response.status_code}"
    )
    content_type = (response.headers.get("content-type") or "").lower()
    assert "text/html" in content_type, (
        f"footer link {href} content-type={content_type!r}, expected text/html"
    )
