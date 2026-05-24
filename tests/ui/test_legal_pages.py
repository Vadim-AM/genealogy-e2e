"""Legal pages — TC-BUG-LEGAL-001 регрессия.

/privacy and /terms must render rendered HTML, not raw markdown. Closed
in commit f3a9d48 per docs/test-plan.md — guard against regression.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure
import httpx
import pytest
from playwright.sync_api import Page, expect

from config.timeouts import TIMEOUTS
from framework.step import step
from pages.tree_page import TreePage
from src.texts import ErrMsg

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory


@pytest.mark.parametrize("path", ["/privacy", "/terms"])
@allure.title("Юридические страницы отрендерены как HTML, не raw markdown")
def test_legal_renders_html_not_raw_markdown(page: Page, base_url: str, path: str):
    """TC-BUG-LEGAL-001: privacy/terms must be rendered HTML."""
    with step("действие: загрузить юридическую страницу"):
        response = page.goto(path)
        assert response is not None, f"page.goto({path}) returned None (navigation failed)"
        assert response.status == HTTPStatus.OK, f"{path}: expected 200, got {response.status}"
        content_type = (response.headers.get("content-type") or "").lower()
        assert "text/html" in content_type, f"{path} content-type={content_type!r}, expected text/html"

    with step("проверка: заголовок и headings присутствуют"):
        # Документ должен иметь непустой title (сырой .md его не устанавливает).
        title = page.title()
        assert title and title.strip(), f"{path} has empty title"

        # Должен быть хотя бы один <h1>/<h2> в отрисованном DOM.
        h1_count = page.locator("h1, h2").count()
        assert h1_count > 0, f"{path} has no <h1>/<h2> headings — looks like raw markdown"

    with step("проверка: нет сырых markdown-маркеров"):
        # Тело НЕ должно содержать литеральных markdown-маркеров вроде '# '
        # в начале строки (отрисованные заголовки не имеют ведущего '#').
        body_text = page.locator("body").text_content() or ""
        lines = body_text.split("\n")
        md_marker_lines = [ln for ln in lines if ln.strip().startswith(("# ", "## ", "### "))]
        assert not md_marker_lines, f"{path} leaks raw markdown lines: {md_marker_lines[:3]}"


@pytest.mark.parametrize("path", ["/privacy", "/terms"])
@allure.title("Юридические страницы не содержат сырых markdown-ссылок")
def test_legal_has_no_unrendered_markdown_links(page: Page, path: str):
    """`[text](url)` syntax must not appear in rendered body."""
    with step("действие: загрузить страницу"):
        page.goto(path)
        page.wait_for_load_state("domcontentloaded")

    with step("проверка: нет markdown-ссылок в тексте"):
        import re
        body = page.locator("body").text_content() or ""
        md_links = re.findall(r"\[[^\]]+\]\([^\)]+\)", body)
        assert not md_links, f"{path} has unrendered MD links: {md_links[:3]}"


# ─────────────────────────────────────────────────────────────────────────
# TC-24.03 — Footer-ссылки на /privacy и /terms видны и открываются в новой вкладке
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("href", ["/privacy", "/terms"])
@allure.title("Футер: юридические ссылки открываются в новой вкладке")
def test_landing_footer_legal_link_is_visible_and_target_blank(
    page: Page, href: str, anon_pages: PageFactory,
):
    """TC-24.03: footer на / содержит link на /privacy и /terms; target=_blank
    чтобы юзер не терял состояние tree/orbit при чтении legal text.

    Селектор по href — устойчив к смене label'ов и i18n.
    """
    with step("действие: открыть главную и найти ссылку"):
        _ = anon_pages.navigate_to(TreePage)
        link = page.locator(f"a[href='{href}']").first
        expect(link, ErrMsg.link_not_visible).to_be_visible()

    with step("проверка: ссылка открывается в новой вкладке"):
        target = link.get_attribute("target")
        assert target == "_blank", (
            f"footer link {href} должен иметь target=_blank, чтобы не терять "
            f"состояние страницы; got target={target!r}"
        )


@pytest.mark.parametrize("href", ["/privacy", "/terms"])
@allure.title("Футер: юридические ссылки ведут на существующие страницы")
def test_landing_footer_legal_link_resolves_to_200(
    base_url: str, href: str,
):
    """TC-24.03: переход по footer-link реально возвращает 200 + HTML
    (защита от битой ссылки). httpx — открывать новую tab через
    Playwright ради этого избыточно.
    """
    with step("действие: запросить юридическую страницу"):
        response = httpx.get(f"{base_url}{href}", follow_redirects=True, timeout=TIMEOUTS.api_request)

    with step("проверка: 200 и content-type text/html"):
        assert response.status_code == HTTPStatus.OK, (
            f"footer link {href} returned {response.status_code}"
        )
        content_type = (response.headers.get("content-type") or "").lower()
        assert "text/html" in content_type, (
            f"footer link {href} content-type={content_type!r}, expected text/html"
        )
