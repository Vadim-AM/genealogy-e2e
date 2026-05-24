"""TC-AI-2: subscription/usage shape для free-tier owner."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure
import httpx

from api import routes
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from src.texts import ErrMsg

if TYPE_CHECKING:
    from collections.abc import Callable

    from fixtures.users import AuthUser


REQUIRED_KEYS = {
    "tier",
    "used",
    "limit",
    "remaining",
    "period_start",
    "period_end",
    "soft_warn",
    "exhausted",
}


@allure.title("Подписка: free-тариф показывает лимит 3 и 0 использованных")
def test_subscription_usage_shape_for_free_owner(
    owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """Free-tier owner получает canonical usage shape."""
    with step("действие: запросить usage для free-tier owner"):
        api = tenant_client(owner_user)
        r = api.get(routes.SUBSCRIPTION_USAGE_LEGACY)
        data = expect_response(r, label="GET subscription/usage").status_ok().data

    with step("проверка: все обязательные ключи присутствуют"):
        missing = REQUIRED_KEYS - set(data.keys())
        should.be_empty(missing, ErrMsg.usage_keys_missing)

    with step("проверка: значения соответствуют free-tier"):
        should.be_equal(data["tier"], "free", ErrMsg.usage_tier_wrong)
        should.be_equal(data["limit"], 3, ErrMsg.usage_limit_wrong)
        should.be_equal(data["used"], 0, ErrMsg.usage_used_wrong)
        should.be_equal(data["remaining"], 3, ErrMsg.usage_remaining_wrong)
        should.be_equal(data["exhausted"], False, ErrMsg.usage_exhausted_wrong)
        should.be_equal(data["soft_warn"], False, ErrMsg.usage_soft_warn_wrong)


@allure.title("Подписка: анонимный запрос к usage возвращает 401")
def test_subscription_usage_requires_auth(base_url: str) -> None:
    """Анонимный запрос к usage возвращает 401."""
    r = httpx.get(f"{base_url}{routes.SUBSCRIPTION_USAGE_LEGACY}")
    expect_response(r, label="anon subscription/usage").status(HTTPStatus.UNAUTHORIZED)
