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

import pytest


_RESERVED_SLUGS = ("admin", "api", "www", "root", "mail", "ftp", "support")


@pytest.mark.parametrize("reserved", _RESERVED_SLUGS)
def test_signup_does_not_assign_reserved_slug(signup_via_api, reserved: str):
    """INV-SLUG-001a: derived slug не должен ровно совпадать с reserved.

    Was open at Run security 28.04 night (slug derivation хватался
    напрямую из email local-part); фикс сейчас на dev tip uses
    suffix/blocklist. Тест держит контракт.
    """
    # Email crafted чтобы deriver выбрал ровно reserved slug —
    # local-part = reserved word без суффикса.
    email = f"{reserved}@e2e.example.com"

    user = signup_via_api(email=email)

    assert user.slug != reserved, (
        f"INV-SLUG-001a: tenant slug derived to reserved word {reserved!r}. "
        f"Subdomain routing → {reserved}.nasharodoslovnaya.ru would belong "
        f"to this user (phishing/impersonation)."
    )
