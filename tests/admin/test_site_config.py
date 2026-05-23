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

import allure
import httpx
import pytest

from tests.api_paths import API
from tests.constants import unique_email
from tests.timeouts import TIMEOUTS


_TENANT_A_VALUE = "Семья A — приватное"
_TENANT_B_VALUE = "Семья B — другое"


@allure.title("Мультитенант: тенант B не видит site_name тенанта A")
def test_tenant_b_sees_default_not_tenant_a_value(signup_via_api, tenant_client):
    """TC-MT-1 step 6 (read-isolation): B GET до своего PATCH видит default, не A."""
    user_a = signup_via_api(email=unique_email("mt-default-a"))
    user_b = signup_via_api(email=unique_email("mt-default-b"))

    tenant_client(user_a).patch(
        API.SITE_CONFIG, json={"site_name": _TENANT_A_VALUE},
    ).raise_for_status()

    r = tenant_client(user_b).get(API.SITE_CONFIG)
    r.raise_for_status()
    b_value = r.json().get("site_name") or ""
    assert b_value != _TENANT_A_VALUE, (
        f"tenant B leaked tenant A's site_name: got {b_value!r}, "
        f"expected anything except {_TENANT_A_VALUE!r}"
    )


@allure.title("Мультитенант: PATCH в тенанте B не затирает данные A")
def test_tenant_b_patch_does_not_overwrite_tenant_a(signup_via_api, tenant_client):
    """TC-MT-1 steps 5–7 (write-isolation): PATCH в B не затирает A.

    Зеркало к existing `test_bug_mt_001_*` (PATCH в A не виден в B).
    Здесь проверяем обратное направление.
    """
    user_a = signup_via_api(email=unique_email("mt-mirror-a"))
    user_b = signup_via_api(email=unique_email("mt-mirror-b"))

    api_a = tenant_client(user_a)
    api_b = tenant_client(user_b)

    api_a.patch(API.SITE_CONFIG, json={"site_name": _TENANT_A_VALUE}).raise_for_status()
    api_b.patch(API.SITE_CONFIG, json={"site_name": _TENANT_B_VALUE}).raise_for_status()

    r = api_a.get(API.SITE_CONFIG)
    r.raise_for_status()
    a_value = r.json().get("site_name") or ""
    assert a_value == _TENANT_A_VALUE, (
        f"tenant A's site_config corrupted by tenant B PATCH: "
        f"expected {_TENANT_A_VALUE!r}, got {a_value!r}"
    )


@allure.title("Мультитенант: анонимный запрос не утекает site_name тенанта")
def test_anonymous_site_config_does_not_leak_tenant_value(
    signup_via_api, tenant_client, base_url: str,
):
    """TC-MT-1 step 4 (anon-isolation): anon GET после PATCH в A не возвращает A.

    Гость, который заходит на главную ничьего сайта, должен видеть
    глобальный default, а не конфиденциальное название чужого
    пространства. Если значение протекает — это GDPR-grade leak.
    """
    user_a = signup_via_api(email=unique_email("mt-anon-a"))

    tenant_client(user_a).patch(
        API.SITE_CONFIG, json={"site_name": _TENANT_A_VALUE},
    ).raise_for_status()

    r = httpx.get(f"{base_url}{API.SITE_CONFIG}", timeout=TIMEOUTS.api_request)
    r.raise_for_status()
    anon_value = r.json().get("site_name") or ""
    assert anon_value != _TENANT_A_VALUE, (
        f"anonymous /api/site/config leaked tenant A site_name: {anon_value!r}"
    )
