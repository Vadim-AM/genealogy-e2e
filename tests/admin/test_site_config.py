"""TC-MT-1: изоляция site_config между тенантами и анонимным доступом."""

from __future__ import annotations

import allure
import httpx

from api import routes
from assertions.base import should
from config.constants import unique_email
from framework.step import step
from src.texts import ErrMsg

_TENANT_A_VALUE = "Семья A — приватное"
_TENANT_B_VALUE = "Семья B — другое"


@allure.title("Мультитенант: тенант B не видит site_name тенанта A")
def test_tenant_b_sees_default_not_tenant_a_value(signup_via_api, tenant_client) -> None:
    """Tenant B видит default, не значение tenant A."""
    with step("подготовка: PATCH site_name в tenant A"):
        user_a = signup_via_api(email=unique_email("mt-default-a"))
        user_b = signup_via_api(email=unique_email("mt-default-b"))

        tenant_client(user_a).patch(
            routes.SITE_CONFIG, json={"site_name": _TENANT_A_VALUE},
        ).raise_for_status()

    with step("проверка: tenant B видит default, не значение A"):
        r = tenant_client(user_b).get(routes.SITE_CONFIG)
        r.raise_for_status()
        b_value = r.json().get("site_name") or ""
        should.not_equal(b_value, _TENANT_A_VALUE, ErrMsg.tenant_value_leaked)


@allure.title("Мультитенант: PATCH в тенанте B не затирает данные A")
def test_tenant_b_patch_does_not_overwrite_tenant_a(signup_via_api, tenant_client) -> None:
    """PATCH в tenant B не перезаписывает site_name tenant A."""
    with step("подготовка: PATCH site_name в обоих tenants"):
        user_a = signup_via_api(email=unique_email("mt-mirror-a"))
        user_b = signup_via_api(email=unique_email("mt-mirror-b"))

        api_a = tenant_client(user_a)
        api_b = tenant_client(user_b)

        api_a.patch(routes.SITE_CONFIG, json={"site_name": _TENANT_A_VALUE}).raise_for_status()
        api_b.patch(routes.SITE_CONFIG, json={"site_name": _TENANT_B_VALUE}).raise_for_status()

    with step("проверка: PATCH B не затёр значение A"):
        r = api_a.get(routes.SITE_CONFIG)
        r.raise_for_status()
        a_value = r.json().get("site_name") or ""
        should.be_equal(a_value, _TENANT_A_VALUE, ErrMsg.tenant_value_corrupted)


@allure.title("Мультитенант: анонимный запрос не утекает site_name тенанта")
def test_anonymous_site_config_does_not_leak_tenant_value(
    signup_via_api, tenant_client, base_url: str,
) -> None:
    """Анонимный GET не возвращает приватное значение tenant A."""
    with step("подготовка: PATCH site_name в tenant A"):
        user_a = signup_via_api(email=unique_email("mt-anon-a"))

        tenant_client(user_a).patch(
            routes.SITE_CONFIG, json={"site_name": _TENANT_A_VALUE},
        ).raise_for_status()

    with step("проверка: анонимный GET не возвращает значение tenant A"):
        r = httpx.get(f"{base_url}{routes.SITE_CONFIG}")
        r.raise_for_status()
        anon_value = r.json().get("site_name") or ""
        should.not_equal(anon_value, _TENANT_A_VALUE, ErrMsg.anon_value_leaked)
