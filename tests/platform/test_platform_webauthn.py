"""Platform WebAuthn / TouchID — TC-PA-WEBAUTHN-* (PR-9)."""

from __future__ import annotations

from http import HTTPStatus

import allure

from api import routes
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from pages.platform_dashboard_page import PlatformDashboardPage
from src.texts import ErrMsg
from tests.platform.conftest import add_virtual_authenticator, make_localhost_context


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
        should.be_equal(r.json()["items"], [], ErrMsg.webauthn_list_not_empty)


@allure.title("WebAuthn: начало регистрации возвращает challenge и rp")
def test_webauthn_register_begin_returns_challenge_and_rp(superadmin_user, tenant_client) -> None:
    """TC-PA-WEBAUTHN-3: register/begin отдаёт challenge + rp.id (контракт WebAuthn)."""
    with step("действие: вызываем register/begin"):
        r = tenant_client(superadmin_user).post(routes.WEBAUTHN_REGISTER_BEGIN)
        r.raise_for_status()
        data = r.json()

    with step("проверка: challenge, rp, user, pubKeyCredParams присутствуют"):
        for key in ("challenge", "rp", "user", "pubKeyCredParams"):
            should.be_in(key, data, ErrMsg.webauthn_option_missing)
        should.be_in("id", data["rp"], ErrMsg.webauthn_option_missing)
        should.be_in("name", data["rp"], ErrMsg.webauthn_option_missing)


@allure.title("WebAuthn: аутентификация без ключей возвращает 404")
def test_webauthn_authenticate_begin_404_without_credentials(superadmin_user, tenant_client) -> None:
    """TC-PA-WEBAUTHN-4: authenticate/begin → 404 (no_webauthn_credentials),."""
    with step("действие: вызываем authenticate/begin без credentials"):
        r = tenant_client(superadmin_user).post(routes.WEBAUTHN_AUTH_BEGIN)

    with step("проверка: 404 с no_webauthn_credentials"):
        expect_response(
            r, label="authenticate/begin without credentials",
        ).status(HTTPStatus.NOT_FOUND)
        should.contain(r.text, "no_webauthn_credentials", ErrMsg.no_webauthn_credentials_missing)


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


@allure.title("WebAuthn: полный цикл регистрации ключа через UI")
def test_webauthn_full_register_via_ui(
    browser, superadmin_user, tenant_client, base_url: str,
) -> None:
    """TC-PA-WEBAUTHN-UI-1: full WebAuthn register flow через UI с virtual authenticator."""
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
            should.be_equal(result.get("status"), "ok", ErrMsg.webauthn_register_failed)
            should.be_equal(result.get("label"), label, ErrMsg.webauthn_label_wrong)

        with step("проверка: credential появился в API"):
            r = tenant_client(superadmin_user).get(routes.WEBAUTHN_LIST)
            r.raise_for_status()
            items = r.json()["items"]
            should.have_length(items, 1, ErrMsg.webauthn_credential_count_wrong)
            should.be_equal(items[0]["label"], label, ErrMsg.webauthn_label_wrong)
    finally:
        ctx.close()


@allure.title("WebAuthn: регистрация и аутентификация в одной сессии")
def test_webauthn_register_then_authenticate_via_ui(
    browser, superadmin_user, base_url: str,
) -> None:
    """TC-PA-WEBAUTHN-UI-2: register → authenticate в одной сессии."""
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
            should.be_equal(auth_result.get("status"), "ok", ErrMsg.webauthn_auth_status_wrong)
            should.be_in("valid_until", auth_result, ErrMsg.webauthn_valid_until_missing)
    finally:
        ctx.close()


@allure.title("WebAuthn: кнопка TouchID присутствует в setup-модалке")
def test_setup_modal_has_webauthn_button_first(
    auth_context_factory, superadmin_user
) -> None:
    """TC-PA-WEBAUTHN-UI-3: в setup-модалке кнопка WebAuthn (#mfa_setup_webauthn)."""
    with step("подготовка: открываем дашборд суперадмина"):
        ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
        page = ctx.new_page()
        page.goto("/platform/dashboard")
        page.wait_for_load_state("domcontentloaded")

    with step("проверка: кнопки WebAuthn setup и verify присутствуют в DOM"):
        dashboard = PlatformDashboardPage(page)
        should.be_equal(dashboard.mfa_setup_webauthn_btn.count(), 1, ErrMsg.webauthn_btn_missing)
        should.be_equal(dashboard.mfa_verify_webauthn_btn.count(), 1, ErrMsg.webauthn_btn_missing)
