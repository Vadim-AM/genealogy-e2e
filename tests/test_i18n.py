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
import uuid

import httpx
import pytest

from tests.timeouts import TIMEOUTS

DEFAULT_PASSWORD = "test_password_8plus"
_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")


def _has_cyrillic(s: str) -> bool:
    return bool(_CYRILLIC_RE.search(s or ""))


@pytest.mark.xfail(
    reason="BUG-i18N-001: backend error detail на английском "
           "(`Invalid email or password`, `Password too short` и пр.). "
           "RU-product, RU-аудитория, RU-UI — ошибки тоже должны быть на "
           "русском. Fix: локализовать strings в auth_v2/auth handlers "
           "(или подключить FastAPI gettext middleware).",
    strict=False,
)
def test_login_wrong_credentials_error_detail_in_russian(uvicorn_server: str):
    """Login с несуществующим email → response detail должен быть на русском."""
    with httpx.Client(base_url=uvicorn_server, timeout=TIMEOUTS.api_request) as c:
        r = c.post(
            "/api/account/login",
            json={
                "email": f"i18n-{uuid.uuid4().hex[:8]}@e2e.example.com",
                "password": "any-password-here",
            },
            headers={"Accept-Language": "ru"},
        )

    assert r.status_code in (401, 403), f"expected 401/403 for unknown user; got {r.status_code}"
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    detail = body.get("detail") or body.get("message") or ""

    assert _has_cyrillic(detail), (
        f"login error detail must be in Russian; got: {detail!r}"
    )


@pytest.mark.xfail(
    reason="BUG-i18N-001 (same): signup validation errors на английском "
           "(«Password too short», «Disposable email» и т.п.). См. выше.",
    strict=False,
)
def test_signup_validation_error_detail_in_russian(uvicorn_server: str):
    """Signup с слишком коротким паролем → 422 с detail на русском."""
    with httpx.Client(base_url=uvicorn_server, timeout=TIMEOUTS.api_request) as c:
        c.post("/api/_test/reset-signup-rate", timeout=TIMEOUTS.api_short).raise_for_status()
        r = c.post(
            "/api/account/signup",
            json={
                "email": f"i18n-sg-{uuid.uuid4().hex[:8]}@e2e.example.com",
                "password": "short",
                "full_name": "Тест",
            },
            headers={"Accept-Language": "ru"},
        )

    assert 400 <= r.status_code < 500, f"expected 4xx for short password; got {r.status_code}"
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}

    # FastAPI/Pydantic 422 имеет body.detail = list[dict]. У каждого item
    # есть `msg` поле. Хоть один из этих msg должен быть на русском.
    detail = body.get("detail")
    if isinstance(detail, list):
        msgs = [item.get("msg", "") for item in detail if isinstance(item, dict)]
        # Хоть один сообщение должно быть на русском.
        any_russian = any(_has_cyrillic(m) for m in msgs)
        assert any_russian, f"all signup validation msgs in English: {msgs!r}"
    else:
        # Plain string detail.
        assert _has_cyrillic(str(detail)), (
            f"signup error detail must be in Russian; got: {detail!r}"
        )
