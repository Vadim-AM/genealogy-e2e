"""Landing (этап 0 funnel — F-LND-1..5, U-LND-1, C-LND-1..3).

Public landing page rendering, headers, content guarantees.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from tests._core import api_paths as routes
from tests._core.err_msg import ErrMsg
from tests._core.messages import PII, Brand, t
from tests._core.step import step
from tests.pages.tree_page import TreePage

if TYPE_CHECKING:
    from tests._fixtures.page_factory import PageFactory


@allure.title("Лендинг: заголовок страницы содержит название бренда")
def test_landing_title_has_brand(page: Page, anon_pages: PageFactory):
    """F-LND-2: title contains a brand fragment.

    Title is finalised by `_bootstrapSiteConfig` (js/init.js) after fetching
    /api/site/config — Playwright `expect(page).to_have_title(...)` auto-waits
    через polling, не требует `networkidle`.
    """
    import re

    with step("действие: открыть главную"):
        _ = anon_pages.navigate_to(TreePage)

    with step("проверка: заголовок содержит бренд"):
        fragments = t(Brand.TITLE_FRAGMENTS)
        pattern = re.compile("|".join(re.escape(f) for f in fragments))
        expect(page, ErrMsg.page_title_wrong).to_have_title(pattern)


@allure.title("Лендинг: нет JS-ошибок в консоли при загрузке")
def test_landing_no_console_errors(page: Page, anon_pages: PageFactory):
    """N-1: no JS exceptions on landing; only allowlisted 401-on-anon network errors.

    Two channels are tracked separately:
      - `pageerror`: uncaught JS exceptions — must be empty.
      - `response`: 4xx/5xx network responses — 401s on known anon-rejected
        endpoints are allowlisted by URL (browser console error text alone
        does not include the URL).
    """
    with step("подготовка: подключить listeners на ошибки"):
        js_errors: list[str] = []
        bad_responses: list[tuple[str, int]] = []

        EXPECTED_401_URLS = (routes.ACCOUNT_ME, routes.TREE)

        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        def _on_response(resp):
            # 404 covered by static-assets test
            if resp.status >= HTTPStatus.BAD_REQUEST and resp.status != HTTPStatus.NOT_FOUND:
                url = resp.url
                if resp.status == HTTPStatus.UNAUTHORIZED and any(u in url for u in EXPECTED_401_URLS):
                    return
                bad_responses.append((url, resp.status))

        page.on("response", _on_response)

    with step("действие: загрузить главную страницу"):
        _ = anon_pages.navigate_to(TreePage)

    with step("проверка: нет JS-ошибок и неожиданных сетевых ошибок"):
        assert not js_errors, f"JS pageerrors on landing: {js_errors}"
        assert not bad_responses, f"unexpected network errors: {bad_responses}"


@allure.title("Лендинг: гость видит вкладки Древо и О проекте")
def test_landing_has_main_tabs(page: Page, anon_pages: PageFactory):
    """U-LND-1: guest-visible tabs are present.

    Guests see only `tree` and `about`; map/sources/timeline are auth-gated
    by `updateGuestUI()` in index.html.
    """
    with step("действие: открыть лендинг"):
        tree = anon_pages.navigate_to(TreePage)

    with step("проверка: вкладки Древо и О проекте видны"):
        expect(tree.tab_tree, ErrMsg.tab_not_visible).to_be_visible()
        expect(tree.tab_about, ErrMsg.tab_not_visible).to_be_visible()


@allure.title("Лендинг: на главной нет персональных данных владельца")
def test_landing_no_personal_owner_data(page: Page, anon_pages: PageFactory):
    """C-LND-3: public landing must not leak owner family names (PII).

    Was xfailed under BUG-COPY-001 until upstream commit `fc2849e`
    ("fix(landing): clear inline owner PII from index.html") landed in
    dev on 28.04. Now a regular regression — the page MUST stay clean
    of any owner family names (`PII.OWNER_FAMILY_NAMES`).
    """
    with step("действие: загрузить главную"):
        _ = anon_pages.navigate_to(TreePage)
        body = page.content()

    with step("проверка: нет PII владельца в контенте"):
        for needle in PII.OWNER_FAMILY_NAMES:
            assert needle not in body, f"PII leak: '{needle}' visible on /"


@allure.title("Лендинг: CSS/JS-ресурсы загружаются без ошибок")
def test_static_assets_load(page: Page, anon_pages: PageFactory):
    """F-LND-5: critical CSS/JS bundles return 200."""
    with step("подготовка: подключить listener на статику"):
        statuses: dict[str, int] = {}

        def _track(response):
            url = response.url
            if any(seg in url for seg in ("/css/", "/js/", "/assets/", "/fonts/")):
                statuses[url] = response.status

        page.on("response", _track)

    with step("действие: загрузить главную"):
        _ = anon_pages.navigate_to(TreePage)

    with step("проверка: все статические ресурсы отдали 2xx/3xx"):
        bad = {url: status for url, status in statuses.items() if status >= HTTPStatus.BAD_REQUEST}
        assert not bad, f"static assets returned errors: {bad}"
