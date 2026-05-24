"""Subscription / quota — TC-AI-2.

Free-tier owner should see {tier, used, limit, remaining, period_start,
period_end, soft_warn, exhausted} in /api/subscription/usage.
"""

from __future__ import annotations

import allure
import httpx

from tests.api_paths import API
from tests.response import expect_response
from tests.step import step
from tests.timeouts import TIMEOUTS

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
def test_subscription_usage_shape_for_free_owner(owner_user, tenant_client):
    """TC-AI-2: /api/subscription/usage returns the canonical free-tier shape."""
    with step("действие: запросить usage для free-tier owner"):
        api = tenant_client(owner_user)
        r = api.get(API.SUBSCRIPTION_USAGE_LEGACY)
        expect_response(r, label="GET subscription/usage").status_ok()
        data = r.json()

    with step("проверка: все обязательные ключи присутствуют"):
        missing = REQUIRED_KEYS - set(data.keys())
        assert not missing, f"missing keys in usage response: {missing} (got {list(data)})"

    with step("проверка: значения соответствуют free-tier"):
        assert data["tier"] == "free", f"new owner must be on free tier, got {data['tier']!r}"
        assert data["limit"] == 3, \
            f"free tier limit per docs/test-plan.md is 3, got {data['limit']}"
        assert data["used"] == 0, f"new owner must have 0 used, got {data['used']}"
        assert data["remaining"] == 3, f"new owner must have 3 remaining, got {data['remaining']}"
        assert data["exhausted"] is False, \
            f"new owner must not be exhausted, got {data['exhausted']!r}"
        assert data["soft_warn"] is False, \
            f"new owner must not have soft_warn, got {data['soft_warn']!r}"


@allure.title("Подписка: анонимный запрос к usage возвращает 401")
def test_subscription_usage_requires_auth(base_url: str):
    """Anonymous request to /api/subscription/usage → 401."""
    r = httpx.get(f"{base_url}{API.SUBSCRIPTION_USAGE_LEGACY}", timeout=TIMEOUTS.api_request)
    expect_response(r, label="anon subscription/usage").status(401)
