"""Security boundary tests — TC-SEC-1, TC-SEC-2."""

from __future__ import annotations

import re
from http import HTTPStatus

import allure
import httpx
import pytest

from api import routes
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from src.texts import ErrMsg


# `/api/admin/invites` удалён: legacy admin-поверхность убрана в
# v2-Phase2 (commit `dac8535`, admin_password упразднён) — роут теперь
# отдаёт 404, он больше не является «закрытым endpoint» для проверки.
# v2-поверхность `/api/account/tenant/invites` (ниже) покрывает ту же
# auth-границу.
@pytest.mark.parametrize(
    "endpoint",
    [
        routes.PEOPLE,
        routes.TENANT_INVITES,
        routes.PLATFORM_METRICS,
    ],
)
@allure.title("Безопасность: аноним получает 401 на закрытом endpoint")
def test_anonymous_get_returns_401_on_private_endpoints(base_url: str, endpoint: str) -> None:
    """TC-SEC-1: GET <private> без cookies → 401."""
    with step(f"действие: анонимный GET {endpoint}"):
        r = httpx.get(f"{base_url}{endpoint}")

    with step("проверка: 401 — доступ запрещён"):
        expect_response(r, label=f"GET {endpoint}").status(HTTPStatus.UNAUTHORIZED)


@allure.title("Безопасность: /api/tree публично доступен гостю (200)")
def test_anonymous_get_tree_returns_200_minimal_showcase(base_url: str) -> None:
    """TC-SEC-1 inverse: /api/tree IS public — guest sees the showcase tree."""
    r = httpx.get(f"{base_url}{routes.TREE}")
    expect_response(r, label="GET /api/tree (public)").status(HTTPStatus.OK)


REQUIRED_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
}


@allure.title("Заголовки: nosniff, X-Frame-Options, Referrer-Policy")
def test_security_headers_present_on_api_responses(base_url: str) -> None:
    """TC-SEC-2: required security headers on every response."""
    with step("действие: запросить /api/account/me (заголовки на любом ответе)"):
        r = httpx.get(f"{base_url}{routes.ACCOUNT_ME}")
        # Состояние авторизации неважно — проверяем заголовки, не тело.
        headers = {k.lower(): v for k, v in r.headers.items()}

    with step("проверка: nosniff, X-Frame-Options, Referrer-Policy"):
        for header, expected in REQUIRED_HEADERS.items():
            actual = headers.get(header)
            should.be_equal(actual, expected, ErrMsg.security_header_wrong)


@allure.title("CSP: script-src-attr 'none' запрещает inline-обработчики")
def test_csp_header_disables_inline_event_handlers(base_url: str) -> None:
    """TC-SEC-2 / BUG-SEC-002: CSP must include `script-src-attr 'none'`."""
    with step("действие: запросить /api/account/me и извлечь CSP"):
        r = httpx.get(f"{base_url}{routes.ACCOUNT_ME}")
        csp = r.headers.get("content-security-policy", "")

    with step("проверка: CSP содержит script-src-attr 'none'"):
        should.be_true(csp, ErrMsg.csp_missing)
        # Ищем директиву — 'none' в кавычках может быть или не быть в
        # зависимости от сериализации. Regex толерантен к кавычкам / пробелам.
        should.be_true(re.search(r"script-src-attr\s+'none'", csp), ErrMsg.csp_directive_missing)


@allure.title("CSP: в HTML лендинга нет inline on*= атрибутов")
def test_landing_html_has_no_inline_event_handlers(base_url: str) -> None:
    """TC-CSP-2: served `/` HTML doesn't contain any `on<ident>=` attribute."""
    with step("действие: загрузить HTML лендинга"):
        r = httpx.get(f"{base_url}/")
        expect_response(r, label="GET /").status_ok()
        html = r.text

    with step("проверка: нет inline on*= атрибутов"):
        # Матчим `on<lowercase-ident>=` как HTML-атрибут (пробел перед,
        # `=` после). Исключаем ложные срабатывания вроде `name="oncall"`,
        # т.к. у них `=` после `name`, а не после подстроки `on*`.
        pattern = re.compile(r'\s(on[a-z]+)\s*=', re.IGNORECASE)
        matches = pattern.findall(html)
        should.be_empty(matches, ErrMsg.inline_handlers_found)


@allure.title("HSTS: заголовок отсутствует при работе по HTTP")
def test_hsts_header_only_on_https(base_url: str) -> None:
    """TC-SEC-2: HSTS is conditional on the request being HTTPS."""
    with step("подготовка: проверяем что тест запущен по HTTP"):
        should.be_true(base_url.startswith("http://"), ErrMsg.base_url_not_http)

    with step("проверка: HSTS-заголовок отсутствует"):
        r = httpx.get(f"{base_url}{routes.ACCOUNT_ME}")
        should.be_false("strict-transport-security" in {k.lower() for k in r.headers}, ErrMsg.hsts_on_http)
