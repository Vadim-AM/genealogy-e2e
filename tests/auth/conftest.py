"""Auth domain fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from playwright.sync_api import Page


@pytest.fixture
def forgot_password_request_spy(page: Page) -> list[str]:
    """Collect URLs of POST requests to forgot-password API."""
    calls: list[str] = []
    page.on(
        "request",
        lambda req: calls.append(req.url)
        if req.method == "POST" and "forgot-password" in req.url
        else None,
    )
    return calls
