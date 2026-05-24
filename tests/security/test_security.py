"""Security boundary tests — TC-SEC-1, TC-SEC-2.

Verifies the public/private surface separation and the security HTTP headers
required for the beta launch.
"""

from __future__ import annotations

import re
from http import HTTPStatus

import allure
import httpx
import pytest

from api import routes
from config.timeouts import TIMEOUTS
from framework.response import expect_response
from framework.step import step

# ─────────────────────────────────────────────────────────────────────────
# TC-SEC-1: Аноним → 401 на закрытых endpoints
# ─────────────────────────────────────────────────────────────────────────


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
def test_anonymous_get_returns_401_on_private_endpoints(base_url: str, endpoint: str):
    """TC-SEC-1: GET <private> без cookies → 401.

    Public surface is allowed (e.g. `/api/tree` returns 200 with the demo
    showcase) — those are tested separately in `test_landing.py`.
    """
    with step(f"действие: анонимный GET {endpoint}"):
        r = httpx.get(f"{base_url}{endpoint}", timeout=TIMEOUTS.api_request)

    with step("проверка: 401 — доступ запрещён"):
        expect_response(r, label=f"GET {endpoint}").status(HTTPStatus.UNAUTHORIZED)


@allure.title("Безопасность: /api/tree публично доступен гостю (200)")
def test_anonymous_get_tree_returns_200_minimal_showcase(base_url: str):
    """TC-SEC-1 inverse: /api/tree IS public — guest sees the showcase tree."""
    r = httpx.get(f"{base_url}{routes.TREE}", timeout=TIMEOUTS.api_request)
    expect_response(r, label="GET /api/tree (public)").status(HTTPStatus.OK)


# ─────────────────────────────────────────────────────────────────────────
# TC-SEC-2: Заголовки безопасности
# ─────────────────────────────────────────────────────────────────────────


REQUIRED_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
}


@allure.title("Заголовки: nosniff, X-Frame-Options, Referrer-Policy")
def test_security_headers_present_on_api_responses(base_url: str):
    """TC-SEC-2: required security headers on every response.

    Picks `/api/account/me` (anonymous → 401) — headers must be set on every
    response, including error ones, so attackers cannot get a privileged
    response without protection.
    """
    with step("действие: запросить /api/account/me (заголовки на любом ответе)"):
        r = httpx.get(f"{base_url}{routes.ACCOUNT_ME}", timeout=TIMEOUTS.api_request)
        # Состояние авторизации неважно — проверяем заголовки, не тело.
        headers = {k.lower(): v for k, v in r.headers.items()}

    with step("проверка: nosniff, X-Frame-Options, Referrer-Policy"):
        for header, expected in REQUIRED_HEADERS.items():
            actual = headers.get(header)
            assert actual == expected, \
                f"{header}: expected {expected!r}, got {actual!r}"


@allure.title("CSP: script-src-attr 'none' запрещает inline-обработчики")
def test_csp_header_disables_inline_event_handlers(base_url: str):
    """TC-SEC-2 / BUG-SEC-002: CSP must include `script-src-attr 'none'`
    so inline `onclick=` event handlers cannot execute (XSS hardening)."""
    with step("действие: запросить /api/account/me и извлечь CSP"):
        r = httpx.get(f"{base_url}{routes.ACCOUNT_ME}", timeout=TIMEOUTS.api_request)
        csp = r.headers.get("content-security-policy", "")

    with step("проверка: CSP содержит script-src-attr 'none'"):
        assert csp, "Content-Security-Policy header missing"
        # Ищем директиву — 'none' в кавычках может быть или не быть в
        # зависимости от сериализации. Regex толерантен к кавычкам / пробелам.
        assert re.search(r"script-src-attr\s+'none'", csp), \
            f"CSP missing `script-src-attr 'none'`: {csp[:200]}"


# ─────────────────────────────────────────────────────────────────────────
# TC-CSP-2 / BUG-CSP-001: inline event handlers в отдаваемом HTML
# ─────────────────────────────────────────────────────────────────────────


@allure.title("CSP: в HTML лендинга нет inline on*= атрибутов")
def test_landing_html_has_no_inline_event_handlers(base_url: str):
    """TC-CSP-2: served `/` HTML doesn't contain any `on<ident>=` attribute.

    CSP header alone не достаточно: оно блокирует только runtime (handler
    не выполнится), но HTML с inline `onload=` всё равно ломает функцию
    (например, fonts.css media=print → media=all переключение). Тест
    ловит **факт** наличия inline event handlers в shipped HTML — это
    регрессия BUG-SEC-002 sweep.
    """
    with step("действие: загрузить HTML лендинга"):
        r = httpx.get(f"{base_url}/", timeout=TIMEOUTS.api_request)
        expect_response(r, label="GET /").status_ok()
        html = r.text

    with step("проверка: нет inline on*= атрибутов"):
        # Матчим `on<lowercase-ident>=` как HTML-атрибут (пробел перед,
        # `=` после). Исключаем ложные срабатывания вроде `name="oncall"`,
        # т.к. у них `=` после `name`, а не после подстроки `on*`.
        pattern = re.compile(r'\s(on[a-z]+)\s*=', re.IGNORECASE)
        matches = pattern.findall(html)
        unique = sorted(set(m.lower() for m in matches))

        assert not matches, (
            f"inline event handlers found in /: {unique}. CSP `script-src-attr "
            f"'none'` blocks them at runtime, but the HTML still ships them — "
            f"this is a BUG-SEC-002 sweep regression. Use addEventListener "
            f"instead of inline `on*=` attributes."
        )


@allure.title("HSTS: заголовок отсутствует при работе по HTTP")
def test_hsts_header_only_on_https(base_url: str):
    """TC-SEC-2: HSTS is conditional on the request being HTTPS.

    Local dev runs over HTTP; the header MUST NOT appear here (otherwise
    it would lock browsers into a stale config). On HTTPS deploys the
    header is added by `security_headers` middleware.
    """
    with step("подготовка: проверяем что тест запущен по HTTP"):
        assert base_url.startswith("http://"), \
            "this test assumes local dev (HTTP); HTTPS path is verified by deployment smoke"

    with step("проверка: HSTS-заголовок отсутствует"):
        r = httpx.get(f"{base_url}{routes.ACCOUNT_ME}", timeout=TIMEOUTS.api_request)
        assert "strict-transport-security" not in {k.lower() for k in r.headers}, \
            "HSTS must not be sent on HTTP responses (only HTTPS)"
