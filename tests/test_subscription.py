"""Subscription / quota — TC-AI-2.

Free-tier owner should see {tier, used, limit, remaining, period_start,
period_end, soft_warn, exhausted} in /api/subscription/usage.
"""

from __future__ import annotations

import httpx

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


def test_subscription_usage_shape_for_free_owner(owner_user, base_url: str):
    """TC-AI-2: /api/subscription/usage returns the canonical free-tier shape."""
    r = httpx.get(
        f"{base_url}/api/subscription/usage",
        cookies=owner_user.cookies,
        headers={"X-Tenant-Slug": owner_user.slug},
        timeout=TIMEOUTS.api_request,
    )
    r.raise_for_status()
    data = r.json()

    missing = REQUIRED_KEYS - set(data.keys())
    assert not missing, f"missing keys in usage response: {missing} (got {list(data)})"

    assert data["tier"] == "free", f"new owner must be on free tier, got {data['tier']!r}"
    assert data["limit"] == 3, \
        f"free tier limit per docs/test-plan.md is 3, got {data['limit']}"
    assert data["used"] == 0, f"new owner must have 0 used, got {data['used']}"
    assert data["remaining"] == 3, f"new owner must have 3 remaining, got {data['remaining']}"
    assert data["exhausted"] is False
    # `soft_warn` is True when remaining/limit < 0.2 — a fresh owner is well above.
    assert data["soft_warn"] is False


def test_subscription_usage_requires_auth(base_url: str):
    """Anonymous request to /api/subscription/usage → 401."""
    r = httpx.get(f"{base_url}/api/subscription/usage", timeout=TIMEOUTS.api_request)
    assert r.status_code == 401, \
        f"anon got {r.status_code} on /api/subscription/usage (expected 401)"
