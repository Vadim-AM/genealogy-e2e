"""TC-MT-1: tenant-scoped site_config — полная изоляция между tenants и при анонимном доступе.

`test_regressions.py::test_bug_mt_001_site_config_is_per_tenant` проверяет
один факт (PATCH в A не виден в B). Этот файл расширяет до полного
сценария из `docs/test-plan.md` TC-MT-1:

  - PATCH в A → A видит свой, B видит default (не A) — изоляция чтения.
  - PATCH в B → A продолжает видеть свой (зеркальная изоляция записи).
  - Anonymous GET после PATCH в A → не возвращает приватный site_name A.

Семантически это behavioural contract isolation; одной regression-строки
недостаточно — TC-MT-1 в test-plan описывает 8 шагов, не один.
"""

from __future__ import annotations

import httpx
import pytest

from tests.constants import unique_email
from tests.timeouts import TIMEOUTS


_TENANT_A_VALUE = "Семья A — приватное"
_TENANT_B_VALUE = "Семья B — другое"


def _patch_site_name(base_url: str, user, value: str) -> None:
    httpx.patch(
        f"{base_url}/api/site/config",
        json={"site_name": value},
        cookies=user.cookies,
        headers={"X-Tenant-Slug": user.slug},
        timeout=TIMEOUTS.api_request,
    ).raise_for_status()


def _get_site_name_authed(base_url: str, user) -> str:
    r = httpx.get(
        f"{base_url}/api/site/config",
        cookies=user.cookies,
        headers={"X-Tenant-Slug": user.slug},
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    return r.json().get("site_name") or ""


def test_tenant_b_sees_default_not_tenant_a_value(signup_via_api, base_url: str):
    """TC-MT-1 step 6 (read-isolation): B GET до своего PATCH видит default, не A."""
    user_a = signup_via_api(email=unique_email("mt-default-a"))
    user_b = signup_via_api(email=unique_email("mt-default-b"))

    _patch_site_name(base_url, user_a, _TENANT_A_VALUE)

    b_value = _get_site_name_authed(base_url, user_b)
    assert b_value != _TENANT_A_VALUE, (
        f"tenant B leaked tenant A's site_name: got {b_value!r}, "
        f"expected anything except {_TENANT_A_VALUE!r}"
    )


def test_tenant_b_patch_does_not_overwrite_tenant_a(signup_via_api, base_url: str):
    """TC-MT-1 steps 5–7 (write-isolation): PATCH в B не затирает A.

    Зеркало к existing `test_bug_mt_001_*` (PATCH в A не виден в B).
    Здесь проверяем обратное направление.
    """
    user_a = signup_via_api(email=unique_email("mt-mirror-a"))
    user_b = signup_via_api(email=unique_email("mt-mirror-b"))

    _patch_site_name(base_url, user_a, _TENANT_A_VALUE)
    _patch_site_name(base_url, user_b, _TENANT_B_VALUE)

    a_value = _get_site_name_authed(base_url, user_a)
    assert a_value == _TENANT_A_VALUE, (
        f"tenant A's site_config corrupted by tenant B PATCH: "
        f"expected {_TENANT_A_VALUE!r}, got {a_value!r}"
    )


def test_anonymous_site_config_does_not_leak_tenant_value(
    signup_via_api, base_url: str
):
    """TC-MT-1 step 4 (anon-isolation): anon GET после PATCH в A не возвращает A.

    Гость, который заходит на главную ничьего сайта, должен видеть
    глобальный default, а не конфиденциальное название чужого
    пространства. Если значение протекает — это GDPR-grade leak.
    """
    user_a = signup_via_api(email=unique_email("mt-anon-a"))

    _patch_site_name(base_url, user_a, _TENANT_A_VALUE)

    r = httpx.get(f"{base_url}/api/site/config", timeout=TIMEOUTS.api_request)
    r.raise_for_status()
    anon_value = r.json().get("site_name") or ""
    assert anon_value != _TENANT_A_VALUE, (
        f"anonymous /api/site/config leaked tenant A site_name: {anon_value!r}"
    )
