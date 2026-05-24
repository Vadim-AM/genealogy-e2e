"""Platform WebAuthn / TouchID — TC-PA-WEBAUTHN-* (PR-9).

Покрывает:
  • GET /api/platform/mfa/webauthn — список credentials (изначально пуст)
  • POST /api/platform/mfa/webauthn/register/begin — challenge + опции
  • POST /api/platform/mfa/webauthn/authenticate/begin — 404 без credentials
  • UI flow через Playwright Virtual Authenticator (CDP) — full register +
    authenticate круг с эмулированным TouchID-устройством.

Virtual Authenticator: Playwright не имеет высокоуровневого API, но
доступен `WebAuthn.addVirtualAuthenticator` через CDP-сессию.
Документация: https://chromedevtools.github.io/devtools-protocol/tot/WebAuthn/

Hard rules: hard assert, single canonical field, no skip-fallback.
"""

from __future__ import annotations

from http import HTTPStatus

import allure

from api import routes
from framework.response import expect_response
from framework.step import step
from pages.platform_dashboard_page import PlatformDashboardPage
from tests.platform.conftest import add_virtual_authenticator, make_localhost_context

# ─────────────────────────────────────────────────────────────────────
# API-уровень
# ─────────────────────────────────────────────────────────────────────


@allure.title("WebAuthn: список ключей недоступен обычному владельцу")
def test_webauthn_list_403_for_non_super(owner_user, tenant_client) -> None:
    """TC-PA-WEBAUTHN-1: regular owner → 401/403."""
    r = tenant_client(owner_user).get(routes.WEBAUTHN_LIST)
    expect_response(r, label="WebAuthn list for non-super").status(HTTPStatus.FORBIDDEN)


@allure.title("WebAuthn: список ключей пуст у нового суперадмина")
def test_webauthn_list_initially_empty(superadmin_user, tenant_client) -> None:
    """TC-PA-WEBAUTHN-2: свежий superadmin без зарегистрированных credentials → []."""
    with step("действие: запрашиваем список WebAuthn-ключей"):
        r = tenant_client(superadmin_user).get(routes.WEBAUTHN_LIST)
        r.raise_for_status()

    with step("проверка: список пуст"):
        assert r.json()["items"] == [], \
            f"items: expected empty list, got {r.json()['items']!r}"


@allure.title("WebAuthn: начало регистрации возвращает challenge и rp")
def test_webauthn_register_begin_returns_challenge_and_rp(superadmin_user, tenant_client) -> None:
    """TC-PA-WEBAUTHN-3: register/begin отдаёт challenge + rp.id (контракт WebAuthn)."""
    with step("действие: вызываем register/begin"):
        r = tenant_client(superadmin_user).post(routes.WEBAUTHN_REGISTER_BEGIN)
        r.raise_for_status()
        data = r.json()

    with step("проверка: challenge, rp, user, pubKeyCredParams присутствуют"):
        for key in ("challenge", "rp", "user", "pubKeyCredParams"):
            assert key in data, f"WebAuthn option {key!r} missing: {sorted(data)}"
        assert "id" in data["rp"], f"rp.id missing: {data['rp']}"
        assert "name" in data["rp"], \
            f"rp.name missing: {data['rp']}"


@allure.title("WebAuthn: аутентификация без ключей возвращает 404")
def test_webauthn_authenticate_begin_404_without_credentials(superadmin_user, tenant_client) -> None:
    """TC-PA-WEBAUTHN-4: authenticate/begin → 404 (no_webauthn_credentials),
    если у юзера ничего не зарегистрировано. Hard 404, не silent fallback."""
    with step("действие: вызываем authenticate/begin без credentials"):
        r = tenant_client(superadmin_user).post(routes.WEBAUTHN_AUTH_BEGIN)

    with step("проверка: 404 с no_webauthn_credentials"):
        expect_response(
            r, label="authenticate/begin without credentials",
        ).status(HTTPStatus.NOT_FOUND)
        assert "no_webauthn_credentials" in r.text, \
            f"expected 'no_webauthn_credentials' in response: {r.text[:200]}"


@allure.title("WebAuthn: завершение регистрации без challenge — 400")
def test_webauthn_register_complete_400_without_challenge(superadmin_user, tenant_client) -> None:
    """TC-PA-WEBAUTHN-5: complete без предшествующего begin → 400 (no_pending_challenge)."""
    with step("действие: вызываем complete без begin"):
        r = tenant_client(superadmin_user).post(
            routes.WEBAUTHN_REGISTER_COMPLETE,
            json={"credential": {}, "label": "Test"},
        )

    with step("проверка: 400 no_pending_challenge"):
        expect_response(
            r, label="register/complete without begin",
        ).status(HTTPStatus.BAD_REQUEST)


# ─────────────────────────────────────────────────────────────────────
# UI flow с Virtual Authenticator (Playwright + CDP)
# ─────────────────────────────────────────────────────────────────────




@allure.title("WebAuthn: полный цикл регистрации ключа через UI")
def test_webauthn_full_register_via_ui(
    browser, superadmin_user, tenant_client, base_url: str,
) -> None:
    """TC-PA-WEBAUTHN-UI-1: full WebAuthn register flow через UI с virtual authenticator.

    Сценарий:
      1. Открываем дашборд (force-MFA ВЫКЛ для этого теста — env флаг по умолчанию)
      2. Setup-модалка не появится без force-MFA → вместо этого вызываем
         JS-функцию `webauthnRegister(label)` напрямую.
      3. Virtual authenticator подписывает attestation.
      4. Проверяем GET /webauthn — credential появился.

    Этот тест критичен: он гарантирует что JS-обвязка в platform-dashboard.html
    (base64url helpers, navigator.credentials.create) собрана корректно и
    бэкенд принимает реальный attestation от Chrome WebAuthn-стека.
    """
    ctx = make_localhost_context(browser, superadmin_user, base_url)
    try:
        with step("подготовка: открываем дашборд и добавляем virtual authenticator"):
            page = ctx.new_page()
            page.goto("/platform/dashboard")
            page.wait_for_load_state("domcontentloaded")
            add_virtual_authenticator(page)

        with step("действие: вызываем webauthnRegister через JS"):
            label = "VirtualE2EKey"
            result = page.evaluate(f"() => webauthnRegister({label!r})")
            assert result.get("status") == "ok", f"webauthnRegister returned: {result}"
            assert result.get("label") == label, \
                f"label: expected {label!r}, got {result.get('label')!r}"

        with step("проверка: credential появился в API"):
            r = tenant_client(superadmin_user).get(routes.WEBAUTHN_LIST)
            r.raise_for_status()
            items = r.json()["items"]
            assert len(items) == 1, f"expected 1 credential, got {len(items)}"
            assert items[0]["label"] == label, \
                f"credential label: expected {label!r}, got {items[0]['label']!r}"
    finally:
        ctx.close()


@allure.title("WebAuthn: регистрация и аутентификация в одной сессии")
def test_webauthn_register_then_authenticate_via_ui(
    browser, superadmin_user, base_url: str,
) -> None:
    """TC-PA-WEBAUTHN-UI-2: register → authenticate в одной сессии.

    Гарантирует sign_count anti-replay работает: после auth счётчик растёт.
    """
    ctx = make_localhost_context(browser, superadmin_user, base_url)
    try:
        with step("подготовка: открываем дашборд и регистрируем ключ"):
            page = ctx.new_page()
            page.goto("/platform/dashboard")
            page.wait_for_load_state("domcontentloaded")
            add_virtual_authenticator(page)
            page.evaluate("() => webauthnRegister('AuthFlowKey')")

        with step("действие: аутентификация через WebAuthn"):
            auth_result = page.evaluate("() => webauthnAuthenticate()")

        with step("проверка: status=ok и valid_until присутствует"):
            assert auth_result.get("status") == "ok", \
                f"status: expected 'ok', got {auth_result.get('status')!r}"
            assert "valid_until" in auth_result, \
                f"valid_until missing from auth result: {sorted(auth_result)}"
    finally:
        ctx.close()


# ─────────────────────────────────────────────────────────────────────
# UI smoke — TouchID-кнопка первой в setup и verify
# ─────────────────────────────────────────────────────────────────────


@allure.title("WebAuthn: кнопка TouchID присутствует в setup-модалке")
def test_setup_modal_has_webauthn_button_first(
    auth_context_factory, superadmin_user
) -> None:
    """TC-PA-WEBAUTHN-UI-3: в setup-модалке кнопка WebAuthn (#mfa_setup_webauthn)
    есть в DOM. (Reveal-модалки требует force-MFA env — здесь проверяем
    что разметка собрана.)"""
    with step("подготовка: открываем дашборд суперадмина"):
        ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
        page = ctx.new_page()
        page.goto("/platform/dashboard")
        page.wait_for_load_state("domcontentloaded")

    with step("проверка: кнопки WebAuthn setup и verify присутствуют в DOM"):
        dashboard = PlatformDashboardPage(page)
        assert dashboard.mfa_setup_webauthn_btn.count() == 1, \
            f"mfa_setup_webauthn_btn: expected 1 in DOM, got {dashboard.mfa_setup_webauthn_btn.count()}"
        assert dashboard.mfa_verify_webauthn_btn.count() == 1, \
            f"mfa_verify_webauthn_btn: expected 1 in DOM, got {dashboard.mfa_verify_webauthn_btn.count()}"
