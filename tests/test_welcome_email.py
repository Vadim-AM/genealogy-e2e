"""TC-COPY-3 / BUG-COPY-003: welcome-email домен hardcoded.

После verify-email backend отправляет welcome-email с инструкцией
«Ваш персональный поддомен → https://{slug}.nasharodoslovnaya.ru/».
URL **захардкожен** на prod-домен в `notifications/templates.py:41`,
игнорируя `GENEALOGY_PUBLIC_URL`.

Последствие: на staging / Self-hosted клиентских инстансах юзер
получает welcome-email со ссылкой на чужой prod, идёт туда, не находит
свой tenant, теряется.

Тест проверяет, что welcome-email базируется на `GENEALOGY_PUBLIC_URL`
(env, который backend знает) — не на hardcoded prod-домене.

Снять xfail когда фикс в `templates.py` подставит `os.environ.get(
"GENEALOGY_PUBLIC_URL", default)` или эквивалент.
"""

from __future__ import annotations

import uuid

import httpx
import pytest

from tests.timeouts import TIMEOUTS

DEFAULT_PASSWORD = "test_password_8plus"


def _signup_and_verify(client: httpx.Client, email: str) -> str:
    """Полный signup + verify, возвращает tenant_slug (для assert)."""
    client.post(
        "/api/_test/reset-signup-rate", timeout=TIMEOUTS.api_short
    ).raise_for_status()

    r = client.post(
        "/api/account/signup",
        json={"email": email, "password": DEFAULT_PASSWORD, "full_name": "Тест"},
    )
    r.raise_for_status()

    mail = client.get("/api/_test/last-email", params={"to": email})
    mail.raise_for_status()
    body = mail.json()["text_body"] or ""
    import re

    m = re.search(r"token=([A-Za-z0-9_\-]+)", body)
    assert m, f"no verification token in email: {body[:200]}"

    client.post("/api/account/verify-email", params={"token": m.group(1)}).raise_for_status()

    login = client.post(
        "/api/account/login",
        json={"email": email, "password": DEFAULT_PASSWORD},
    )
    login.raise_for_status()
    return login.json()["tenant_slug"]


@pytest.mark.xfail(
    reason="BUG-COPY-003: welcome-email domain hardcoded to "
           "nasharodoslovnaya.ru in `notifications/templates.py:41`, "
           "ignores GENEALOGY_PUBLIC_URL env. Confirmed Run 2 28.04. "
           "Fix: derive base URL from settings/env. Multi-tenant Self-"
           "hosted клиенты сейчас получают ссылки на чужой prod.",
    strict=False,
)
def test_welcome_email_uses_public_url_env_not_hardcoded_prod(
    uvicorn_server: str,
):
    """Welcome-email должен ссылаться на `GENEALOGY_PUBLIC_URL`-based URL,
    не на захардкоженный `nasharodoslovnaya.ru`.

    Тест-окружение запускается без `GENEALOGY_PUBLIC_URL` (default
    `http://127.0.0.1:8642` или внутренний). Welcome-email НЕ должен
    содержать prod-домен — иначе мы знаем, что domen hardcoded.
    """
    email = f"welcome-{uuid.uuid4().hex[:8]}@e2e.example.com"

    with httpx.Client(base_url=uvicorn_server, timeout=TIMEOUTS.api_request) as c:
        _signup_and_verify(c, email)

        # Welcome-email отправляется при verify (или отдельным шагом —
        # depends on flow). Берём latest mail для этого адреса.
        mail = c.get("/api/_test/last-email", params={"to": email})
        mail.raise_for_status()
        body = mail.json()
        text_body = body.get("text_body") or ""
        html_body = body.get("html_body") or ""
        full_body = text_body + html_body

    # Hardcoded prod не должно появиться когда среда не prod.
    assert "nasharodoslovnaya.ru" not in full_body, (
        f"welcome-email содержит hardcoded prod-домен 'nasharodoslovnaya.ru'. "
        f"Тест-окружение работает на {uvicorn_server}. Welcome URL должен "
        f"derive из GENEALOGY_PUBLIC_URL/settings, не быть статической "
        f"строкой в template."
    )
