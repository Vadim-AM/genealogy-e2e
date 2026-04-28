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

import httpx

from tests.api_paths import API
from tests.constants import unique_email
from tests.timeouts import TIMEOUTS

NEW_PASSWORD = "NewPassword_After_Reset_2026"


def _me_status(base_url: str, cookies: dict[str, str]) -> int:
    return httpx.get(
        f"{base_url}{API.ACCOUNT_ME}",
        cookies=cookies,
        timeout=TIMEOUTS.api_request,
    ).status_code


def _trigger_password_reset(
    base_url: str, *, email: str, new_password: str, read_email_token,
) -> None:
    """forgot-password → read token from mail → reset-password."""
    httpx.post(
        f"{base_url}{API.FORGOT_PASSWORD}",
        json={"email": email},
        timeout=TIMEOUTS.api_request,
    ).raise_for_status()
    token = read_email_token(email)
    httpx.post(
        f"{base_url}{API.RESET_PASSWORD}",
        json={"token": token, "new_password": new_password},
        timeout=TIMEOUTS.api_request,
    ).raise_for_status()


def test_password_reset_invalidates_active_session(
    signup_via_api, read_email_token, base_url: str,
):
    """INV-AUTH-001: после reset-password старая session cookie должна
    быть отозвана — `/api/account/me` возвращает 401.

    Was xfail until upstream commit `5b4c674`. Regression-trail.
    """
    email = unique_email("sess")
    user = signup_via_api(email=email)

    # Sanity: сессия активна сразу после signup.
    assert _me_status(base_url, user.cookies) == 200

    _trigger_password_reset(
        base_url, email=email, new_password=NEW_PASSWORD,
        read_email_token=read_email_token,
    )

    after = _me_status(base_url, user.cookies)
    assert after in (401, 403), (
        f"INV-AUTH-001 regression: stolen session NOT invalidated after "
        f"password reset. Cookie still returns {after}. Defeats the "
        f"security purpose of reset."
    )


def test_password_reset_invalidates_all_devices_sessions(
    signup_via_api, login_existing, read_email_token, base_url: str,
):
    """INV-MULTIDEVICE-001a: все sessions user'а должны быть отозваны
    при reset-password, не только current.

    Was xfail at Run security 28.04 night. Closed by upstream batch-2.
    Regression-trail для `revoke_all_user_sessions(user_id)` контракта.
    """
    email = unique_email("mdev")
    user = signup_via_api(email=email)

    # «Device A»: первая сессия (атакующий мог украсть эту cookie).
    device_a_cookies = user.cookies

    # «Device B»: жертва залогинена параллельно с того же email.
    device_b_cookies = login_existing(email)

    # Sanity: обе валидны.
    assert _me_status(base_url, device_a_cookies) == 200
    assert _me_status(base_url, device_b_cookies) == 200

    _trigger_password_reset(
        base_url, email=email, new_password=NEW_PASSWORD,
        read_email_token=read_email_token,
    )

    a_after = _me_status(base_url, device_a_cookies)
    assert a_after in (401, 403), (
        f"INV-MULTIDEVICE-001a regression: device A session NOT "
        f"invalidated after reset initiated elsewhere. Cookie "
        f"returns {a_after}."
    )
