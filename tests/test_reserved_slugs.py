"""INV-SLUG-001a: reserved slugs (admin, api, www, root, ...) must not
be assignable as tenant slugs.

**Сценарий attack:**
- Атакующий регистрируется с email подобным `admin@…`, backend
  деривирует slug = `admin` (или близко).
- В production с subdomain routing — `admin.nasharodoslovnaya.ru`
  принадлежит атакующему: phishing/impersonation.
- Аналогично `api.…`, `www.…`, `root.…` — служебные subdomains
  становятся owned by attacker.

**Защита:** при derivation slug'а из email/full_name backend должен
содержать reserved-words blocklist (admin, api, www, root, mail,
ftp, blog, support, help, status и т.п.). Если deriver попадает на
reserved — добавить numeric suffix или вернуть 4xx с просьбой
выбрать другое.

Run security 28.04 night confirmed, blocklist отсутствует.
"""

from __future__ import annotations

import re

import httpx
import pytest

from tests.timeouts import TIMEOUTS

DEFAULT_PASSWORD = "test_password_8plus"

_RESERVED_SLUGS = ("admin", "api", "www", "root", "mail", "ftp", "support")


def _signup_verify_and_get_slug(client: httpx.Client, email: str) -> str:
    client.post("/api/_test/reset-signup-rate", timeout=TIMEOUTS.api_short).raise_for_status()
    client.post(
        "/api/account/signup",
        json={"email": email, "password": DEFAULT_PASSWORD, "full_name": "Тест"},
    ).raise_for_status()
    mail = client.get("/api/_test/last-email", params={"to": email}).json()
    token = re.search(r"token=([\w\-]+)", mail["text_body"]).group(1)
    client.post("/api/account/verify-email", params={"token": token}).raise_for_status()
    login = client.post(
        "/api/account/login",
        json={"email": email, "password": DEFAULT_PASSWORD},
    )
    login.raise_for_status()
    return login.json()["tenant_slug"]


@pytest.mark.parametrize("reserved", _RESERVED_SLUGS)
def test_signup_does_not_assign_reserved_slug(uvicorn_server: str, reserved: str):
    """INV-SLUG-001a: derived slug не должен ровно совпадать с reserved.

    Was open at Run security 28.04 night (slug derivation хватался
    напрямую из email local-part); фикс сейчас на dev tip uses
    suffix/blocklist. Тест держит контракт.
    """
    # Email crafted чтобы deriver выбрал ровно reserved slug.
    # Local-part = reserved word без суффикса — наш привлекательный
    # для атакующего сценарий.
    email = f"{reserved}@e2e.example.com"

    with httpx.Client(base_url=uvicorn_server, timeout=TIMEOUTS.api_request) as c:
        slug = _signup_verify_and_get_slug(c, email)

    assert slug != reserved, (
        f"INV-SLUG-001a: tenant slug derived to reserved word {reserved!r}. "
        f"Subdomain routing → {reserved}.nasharodoslovnaya.ru would belong "
        f"to this user (phishing/impersonation)."
    )
    assert not slug.startswith(f"{reserved}.") and slug != reserved, (
        f"slug starts with reserved prefix: {slug!r}"
    )
