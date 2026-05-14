"""Misc test utilities that don't belong in users/clients/server modules."""

from __future__ import annotations

import pytest


@pytest.fixture
def soft_check():
    """Yields Playwright `expect` for `expect.soft(...)` usage.

    Use ONLY for smoke blocks asserting >=3 independent facts at once
    (e.g. "all 5 nav tabs visible"). For functional flow — hard `expect`.
    """
    from playwright.sync_api import expect

    yield expect
