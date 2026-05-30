"""Legal pages — TC-BUG-LEGAL-001 регрессия."""

from __future__ import annotations

import re
from http import HTTPStatus
from typing import TYPE_CHECKING

import allure
import httpx
import pytest
from playwright.sync_api import Page, expect

from assertions.base import should
from framework.response import expect_response
from framework.step import step
from pages.legal_page import LegalPage
from pages.tree_page import TreePage
from src.texts import ErrMsg

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory


@pytest.mark.parametrize("path", ["/privacy", "/terms"])
@allure.title("Юридические страницы отрендерены как HTML, не raw markdown")
def test_legal_renders_html_not_raw_markdown(page: Page, base_url: str, path: str) -> None:
    """TC-BUG-LEGAL-001: privacy/terms must be rendered HTML."""
    with step("действие: загрузить юридическую страницу"):
        legal = LegalPage(page, path)
        response = page.goto(path)
        response = should.not_none(response, ErrMsg.page_navigation_failed)
        should.be_equal(response.status, HTTPStatus.OK, ErrMsg.status_mismatch)
        content_type = (response.headers.get("content-type") or "").lower()
        should.contain(content_type, "text/html", ErrMsg.content_type_not_html)

    with step("проверка: заголовок и headings присутствуют"):
        # Документ должен иметь непустой title (сырой .md его не устанавливает).
        title = legal.title()
        should.be_true(title and title.strip(), ErrMsg.empty_page_title)

        # Должен быть хотя бы один <h1>/<h2> в отрисованном DOM.
        should.greater(legal.heading_count(), 0, ErrMsg.no_headings_found)

    with step("проверка: нет сырых markdown-маркеров"):
        # Тело НЕ должно содержать литеральных markdown-маркеров вроде '# '
        # в начале строки (отрисованные заголовки не имеют ведущего '#').
        body_text = legal.body_text()
        lines = body_text.split("\n")
        md_marker_lines = [ln for ln in lines if ln.strip().startswith(("# ", "## ", "### "))]
        should.be_empty(md_marker_lines, ErrMsg.raw_markdown_lines)


@pytest.mark.parametrize("path", ["/privacy", "/terms"])
@allure.title("Юридические страницы не содержат сырых markdown-ссылок")
def test_legal_has_no_unrendered_markdown_links(page: Page, path: str) -> None:
    """`[text](url)` syntax must not appear in rendered body."""
    with step("действие: загрузить страницу"):
        legal = LegalPage(page, path)
        legal.goto()
        legal.wait_for_page_load()

    with step("проверка: нет markdown-ссылок в тексте"):
        body = legal.body_text()
        md_links = re.findall(r"\[[^\]]+\]\([^\)]+\)", body)
        should.be_empty(md_links, ErrMsg.raw_markdown_links)


@pytest.mark.parametrize("href", ["/privacy", "/terms"])
@allure.title("Футер: юридические ссылки открываются в новой вкладке")
def test_landing_footer_legal_link_is_visible_and_target_blank(
    page: Page,
    href: str,
    anon_pages: PageFactory,
) -> None:
    """TC-24.03: footer на / содержит link на /privacy и /terms; target=_blank."""
    with step("действие: открыть главную и найти ссылку"):
        tree = anon_pages.navigate_to(TreePage)
        link = tree.footer_link(href)
        expect(link, ErrMsg.link_not_visible).to_be_visible()

    with step("проверка: ссылка открывается в новой вкладке"):
        target = tree.footer_link_target(href)
        should.be_equal(target, "_blank", ErrMsg.link_target_wrong)


@pytest.mark.parametrize("href", ["/privacy", "/terms"])
@allure.title("Футер: юридические ссылки ведут на существующие страницы")
def test_landing_footer_legal_link_resolves_to_200(
    base_url: str,
    href: str,
) -> None:
    """TC-24.03: переход по footer-link реально возвращает 200 + HTML."""
    with step("действие: запросить юридическую страницу"):
        response = httpx.get(f"{base_url}{href}", follow_redirects=True)

    with step("проверка: 200 и content-type text/html"):
        expect_response(response, label=f"footer link {href}").status(HTTPStatus.OK)
        content_type = (response.headers.get("content-type") or "").lower()
        should.contain(content_type, "text/html", ErrMsg.content_type_not_html)
