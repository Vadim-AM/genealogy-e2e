"""INV-AUTH-001: reset password should invalidate active sessions.

**Атак-сценарий:** злоумышленник получил session cookie жертвы (XSS,
malware, leaked logs, replay из network capture). Жертва замечает
подозрительную активность, идёт на forgot-password, сбрасывает пароль.
**Ожидание:** старая cookie перестаёт работать, атакующий выкинут.
**Реальность (Run security 28.04):** старая cookie работает после
reset — атакующий сохраняет access.

Это **P0 security** баг — reset password выглядит как защитная мера
для пользователя («я меняю пароль чтобы выгнать злоумышленника»),
но на деле не делает того, что обещает.

**Fix:** при успешном reset password backend должен:
- Удалить все `PlatformSession` rows для этого user_id (или
  сменить session-key derivation чтобы старые tokens становились
  невалидными).
- Опционально: отправить email «ваш пароль был сменён, все
  сессии завершены» — defence-in-depth notification.
"""

from __future__ import annotations

import re
import uuid

import httpx
import pytest

from tests.timeouts import TIMEOUTS

DEFAULT_PASSWORD = "test_password_8plus"
NEW_PASSWORD = "NewPassword_After_Reset_2026"


def test_password_reset_invalidates_active_sessions(uvicorn_server: str):
    """INV-AUTH-001: после reset-password старая session cookie должна
    быть отозвана — последующий /api/account/me с ней → 401.

    Was xfail under INV-AUTH-001 until upstream commit `5b4c674`
    ("fix(auth): invalidate active sessions on password reset").
    Now regular regression.
    """
    email = f"sess-{uuid.uuid4().hex[:8]}@e2e.example.com"

    with httpx.Client(base_url=uvicorn_server, timeout=TIMEOUTS.api_request) as c:
        c.post("/api/_test/reset-signup-rate", timeout=TIMEOUTS.api_short).raise_for_status()

        # 1. Signup + verify + login → активная сессия.
        c.post(
            "/api/account/signup",
            json={"email": email, "password": DEFAULT_PASSWORD, "full_name": "Тест"},
        ).raise_for_status()

        mail = c.get("/api/_test/last-email", params={"to": email}).json()
        token = re.search(r"token=([\w\-]+)", mail["text_body"]).group(1)
        c.post("/api/account/verify-email", params={"token": token}).raise_for_status()

        login = c.post(
            "/api/account/login",
            json={"email": email, "password": DEFAULT_PASSWORD},
        )
        login.raise_for_status()
        old_cookies = dict(login.cookies)

        # 2. Sanity: старая сессия валидна сейчас.
        me_before = c.get("/api/account/me", cookies=old_cookies)
        assert me_before.status_code == 200, (
            f"baseline: session must work right after login; got {me_before.status_code}"
        )

        # 3. Forgot-password → reset-password.
        c.post(
            "/api/account/forgot-password", json={"email": email}
        ).raise_for_status()

        reset_mail = c.get("/api/_test/last-email", params={"to": email}).json()
        reset_token = re.search(r"token=([\w\-]+)", reset_mail["text_body"]).group(1)

        c.post(
            "/api/account/reset-password",
            json={"token": reset_token, "new_password": NEW_PASSWORD},
        ).raise_for_status()

        # 4. Старая cookie (захваченная атакующим до reset'а) должна
        #    быть невалидна.
        me_after = c.get("/api/account/me", cookies=old_cookies)

    assert me_after.status_code in (401, 403), (
        f"INV-AUTH-001: stolen session NOT invalidated after password reset. "
        f"Old cookie still returns {me_after.status_code} {me_after.text[:200]}. "
        f"Attacker with stolen cookie keeps access — defeats the purpose "
        f"of password reset."
    )
