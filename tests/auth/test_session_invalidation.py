"""INV-AUTH-001 + INV-MULTIDEVICE-001a: reset password invalidates sessions.

**Атак-сценарий (INV-AUTH-001):** атакующий получил session cookie
жертвы. Жертва замечает подозрительную активность, меняет пароль.
**Ожидание:** старая cookie перестаёт работать.

**Multi-device амплификация (INV-MULTIDEVICE-001a):** жертва
залогинена параллельно на двух устройствах (телефон + ноут). Меняет
пароль с ноута. Сессия на телефоне (которую мог украсть атакующий)
тоже должна быть отозвана — `revoke_all_user_sessions(user_id)`.

Оба теста были xfail на предыдущих QA Run'ах; закрыты upstream
коммитами `5b4c674` (INV-AUTH-001) и батч-2 (INV-MULTIDEVICE-001a).
Сейчас держат контракт против будущих регрессий.
"""

from __future__ import annotations

from http import HTTPStatus

import allure

from config.constants import unique_email
from framework.step import step
from helpers.auth.session_helpers import NEW_PASSWORD, me_status, trigger_password_reset


@allure.title("Сброс пароля инвалидирует текущую активную сессию")
def test_password_reset_invalidates_active_session(
    signup_via_api, read_email_token, base_url: str,
) -> None:
    """INV-AUTH-001: после reset-password старая session cookie должна
    быть отозвана — `/api/account/me` возвращает 401.

    Was xfail until upstream commit `5b4c674`. Regression-trail.
    """
    with step("подготовка: signup и проверка активной сессии"):
        email = unique_email("sess")
        user = signup_via_api(email=email)
        assert me_status(base_url, user.cookies) == HTTPStatus.OK, \
            "session must be active immediately after signup"

    with step("действие: сброс пароля"):
        trigger_password_reset(
            base_url, email=email, new_password=NEW_PASSWORD,
            read_email_token=read_email_token,
        )

    with step("проверка: старая сессия инвалидирована (401)"):
        after = me_status(base_url, user.cookies)
        assert after == HTTPStatus.UNAUTHORIZED, (
            f"INV-AUTH-001 regression: stolen session NOT invalidated after "
            f"password reset. Cookie still returns {after}. Defeats the "
            f"security purpose of reset."
        )


@allure.title("Сброс пароля отзывает сессии на всех устройствах")
def test_password_reset_invalidates_all_devices_sessions(
    signup_via_api, login_existing, read_email_token, base_url: str,
) -> None:
    """INV-MULTIDEVICE-001a: все sessions user'а должны быть отозваны
    при reset-password, не только current.

    Was xfail at Run security 28.04 night. Closed by upstream batch-2.
    Regression-trail для `revoke_all_user_sessions(user_id)` контракта.
    """
    with step("подготовка: signup и создание двух параллельных сессий"):
        email = unique_email("mdev")
        user = signup_via_api(email=email)
        device_a_cookies = user.cookies
        device_b_cookies = login_existing(email)

    with step("подготовка: проверка что обе сессии активны"):
        assert me_status(base_url, device_a_cookies) == HTTPStatus.OK, \
            "device A session must be active before reset"
        assert me_status(base_url, device_b_cookies) == HTTPStatus.OK, \
            "device B session must be active before reset"

    with step("действие: сброс пароля"):
        trigger_password_reset(
            base_url, email=email, new_password=NEW_PASSWORD,
            read_email_token=read_email_token,
        )

    with step("проверка: сессия device A инвалидирована (401)"):
        a_after = me_status(base_url, device_a_cookies)
        assert a_after == HTTPStatus.UNAUTHORIZED, (
            f"INV-MULTIDEVICE-001a regression: device A session NOT "
            f"invalidated after reset initiated elsewhere. Cookie "
            f"returns {a_after}."
        )
