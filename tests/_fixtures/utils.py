"""Misc test utilities that don't belong in users/clients/server modules."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

    from playwright.sync_api import Expect


@pytest.fixture
def soft_check() -> Generator[Expect]:
    """Yields Playwright `expect` for `expect.soft(...)` usage.

    Use ONLY for smoke blocks asserting >=3 independent facts at once
    (e.g. "all 5 nav tabs visible"). For functional flow — hard `expect`.
    """
    from playwright.sync_api import expect

    yield expect
