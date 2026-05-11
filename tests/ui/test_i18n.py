"""TC-i18N-1 / BUG-i18N-001: backend возвращает error detail на английском.

Genealogy позиционируется как RU-product (домен .ru, аудитория РФ +
post-Soviet diaspora). UI полностью на русском. Но **backend** при
ошибках валидации возвращает error.detail на английском — например
«Invalid email or password», «Password too short» и т.п.

Симптом видимый: пользователь, заполнивший signup на русском, видит
красное сообщение под полем на английском — disconnect, downgrades
trust.

Тест: triggering известную ошибку — login с wrong password, signup с
short password — проверяем что detail на русском (содержит кириллицу).

Снять xfail когда backend локализует error messages (через FastAPI
gettext-like layer или просто Russian strings в auth handler).
"""

from __future__ import annotations

import re

import httpx
import pytest

from tests.api_paths import API
from tests.constants import unique_email
from tests.timeouts import TIMEOUTS

_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")


def _has_cyrillic(s: str) -> bool:
    return bool(_CYRILLIC_RE.search(s or ""))


def test_login_wrong_credentials_error_detail_in_russian(uvicorn_server: str):
    """Login с несуществующим email → response detail должен быть на русском."""
    with httpx.Client(base_url=uvicorn_server, timeout=TIMEOUTS.api_request) as c:
        r = c.post(
            API.LOGIN,
            json={
                "email": unique_email("i18n"),
                "password": "any-password-here",
            },
            headers={"Accept-Language": "ru"},
        )

    assert r.status_code == 401, f"expected 401 for unknown user; got {r.status_code}"
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    detail = body.get("detail") or body.get("message") or ""

    assert _has_cyrillic(detail), (
        f"login error detail must be in Russian; got: {detail!r}"
    )


def test_signup_validation_error_detail_in_russian(uvicorn_server: str):
    """Signup с слишком коротким паролем → 422 с detail на русском."""
    with httpx.Client(base_url=uvicorn_server, timeout=TIMEOUTS.api_request) as c:
        c.post(API.TEST_RESET_SIGNUP_RATE, timeout=TIMEOUTS.api_short).raise_for_status()
        r = c.post(
            API.SIGNUP,
            json={
                "email": unique_email("i18n-sg"),
                "password": "short",
                "full_name": "Тест",
            },
            headers={"Accept-Language": "ru"},
        )

    assert r.status_code == 422, f"expected 422 Pydantic validation for short password; got {r.status_code}"
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}

    # FastAPI/Pydantic 422 имеет body.detail = list[dict]; каждый item имеет
    # `msg`. Пин на canonical Pydantic shape — если backend подменит формат
    # на plain-string, тест упадёт и его придётся переписать осознанно.
    detail = body.get("detail")
    assert isinstance(detail, list), (
        f"expected Pydantic 422 list[dict] shape, got {type(detail).__name__}: {detail!r}"
    )
    msgs = [item.get("msg", "") for item in detail if isinstance(item, dict)]
    assert any(_has_cyrillic(m) for m in msgs), \
        f"all signup validation msgs in English: {msgs!r}"
