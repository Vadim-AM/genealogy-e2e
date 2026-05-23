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

import allure
import httpx
import pytest

from tests.api_paths import API
from tests.constants import unique_email
from tests.timeouts import TIMEOUTS


@allure.title("Welcome-письмо содержит URL из GENEALOGY_PUBLIC_URL, не прод")
def test_welcome_email_uses_public_url_env_not_hardcoded_prod(
    signup_via_api, uvicorn_server: str,
):
    """Welcome-email должен ссылаться на `GENEALOGY_PUBLIC_URL`-based URL,
    не на захардкоженный `nasharodoslovnaya.ru`.

    Тест-окружение запускается без `GENEALOGY_PUBLIC_URL` (default
    `http://127.0.0.1:8642` или внутренний). Welcome-email НЕ должен
    содержать prod-домен — иначе мы знаем, что domen hardcoded.
    """
    email = unique_email("welcome")
    signup_via_api(email=email)

    with httpx.Client(base_url=uvicorn_server, timeout=TIMEOUTS.api_request) as c:
        # Welcome-email отправляется при verify — то есть это самое последнее
        # сообщение для адреса после signup_via_api flow.
        mail = c.get(API.TEST_LAST_EMAIL, params={"to": email})
        mail.raise_for_status()
        body = mail.json()
        text_body = body.get("text_body") or ""
        html_body = body.get("html_body") or ""
        full_body = text_body + html_body

    # Pin-positive: welcome URL должен совпадать с тем, как backend
    # сейчас знает себя (GENEALOGY_PUBLIC_URL). Тест запускается с
    # E2E_PUBLIC_URL_HOST = host из uvicorn_server (e.g. 127.0.0.1).
    # Если в письме hardcoded `nasharodoslovnaya.ru` или другой
    # production-домен — fail.
    public_host = uvicorn_server.split("://", 1)[-1].split(":", 1)[0]
    assert public_host in full_body, (
        f"welcome-email URL не содержит host из GENEALOGY_PUBLIC_URL "
        f"({public_host!r}). Backend hardcodes prod domain in template "
        f"вместо env-driven derivation. Body excerpt: {full_body[:300]!r}"
    )
    assert "nasharodoslovnaya.ru" not in full_body, (
        f"welcome-email содержит hardcoded prod-домен 'nasharodoslovnaya.ru' "
        f"при запуске на {uvicorn_server}. URL должен derive из "
        f"GENEALOGY_PUBLIC_URL, не быть статической строкой в template."
    )
