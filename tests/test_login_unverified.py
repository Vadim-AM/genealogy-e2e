"""TC-VERIFY-1 / BUG-LG-001: попытка login до verify-email.

После signup, до того как пользователь кликнул verify-email link, его
аккаунт уже в БД (записан с `email_verified=False`), но ещё не активен.
Попытка login должна возвращать осмысленное сообщение «подтвердите
почту», а не generic 401 — иначе пользователь будет думать что забыл
пароль и пойдёт сбрасывать.

Run 2 (28.04): ответ generic «Invalid email or password» (на английском
+ путает unverified с wrong-password). Тест документирует ожидаемый
контракт: 401 + message на русском, упоминающее «подтверждение почты»
(или конкретный код типа `verification_required` в JSON).

Снять xfail когда продукт-фикс добавит specific path для unverified
user в login handler.
"""

from __future__ import annotations

import uuid

import httpx
import pytest

from tests.timeouts import TIMEOUTS

DEFAULT_PASSWORD = "test_password_8plus"


@pytest.mark.xfail(
    reason="BUG-LG-001: /api/account/login для unverified user возвращает "
           "generic «Invalid email or password» (Run 2 28.04). Пользователь "
           "не понимает почему его credentials не работают, идёт сбрасывать "
           "пароль. Fix: branch в login handler — если user найден но "
           "email_verified=False, вернуть 403 + status=verification_required "
           "+ Russian message «Подтвердите почту по ссылке из письма»; "
           "опционально re-send verification email.",
    strict=False,
)
def test_login_unverified_returns_specific_verify_required(uvicorn_server: str):
    """Login до verify-email → response должен указывать на причину
    (verification needed), не маскировать как «invalid credentials»."""
    email = f"unverified-{uuid.uuid4().hex[:8]}@e2e.example.com"

    with httpx.Client(base_url=uvicorn_server, timeout=TIMEOUTS.api_request) as c:
        c.post(
            "/api/_test/reset-signup-rate", timeout=TIMEOUTS.api_short
        ).raise_for_status()

        signup = c.post(
            "/api/account/signup",
            json={"email": email, "password": DEFAULT_PASSWORD, "full_name": "Тест"},
        )
        signup.raise_for_status()

        login = c.post(
            "/api/account/login",
            json={"email": email, "password": DEFAULT_PASSWORD},
        )

    # Должно быть 403 (forbidden — не permission, но «не подтвердил») или
    # 401 с конкретным `status`/`detail` указывающим на verification.
    assert login.status_code in (401, 403), (
        f"login should reject unverified user; got {login.status_code}"
    )

    body = (login.json() if login.headers.get("content-type", "").startswith("application/json") else {}) or {}
    detail = (body.get("detail") or body.get("message") or "").lower()

    # Один из двух признаков: status discriminator OR русский текст про
    # подтверждение/верификацию. Не accept generic «invalid credentials».
    has_status_code = body.get("status") in ("verification_required", "email_not_verified")
    has_russian_hint = "подтверд" in detail or "верифик" in detail or "почт" in detail

    assert has_status_code or has_russian_hint, (
        f"login response для unverified user не указывает на причину. "
        f"Status: {login.status_code}, body: {body!r}. Expected status="
        f"verification_required ИЛИ detail упоминает «подтверд/верифик/почт»."
    )
