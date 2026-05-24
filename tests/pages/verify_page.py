"""POM for /verify?token=..."""

from __future__ import annotations

from typing import Self

from playwright.sync_api import Page, expect

from tests.timeouts import TIMEOUTS

from .base import BasePage


class VerifyPage(BasePage):
    URL = "/verify"

    def __init__(self, page: Page):
        super().__init__(page)
        self.next_link = page.locator("#link")  # no semantic: dynamically populated link, no stable text

    def open_with_token(self, token: str) -> Self:
        """Navigate to the verify page with the given token."""
        self.page.goto(f"{self.URL}?token={token}")
        return self

    def expect_success(self) -> None:
        """After verification the success layout shows a "next step" link
        (`#link`) populated with the tenant slug. Visibility = success path.

        Uses `pw_provision_ms` (wider than the default `pw_expect_ms`): the
        verify-email POST chains into `provision_tenant` (CREATE SCHEMA +
        create_all + alembic stamp, under a session-level advisory lock).
        Under `-n auto` parallel load, with xdist workers contending, that
        round-trip can exceed the default expect window — and `#link` is
        populated by JS only once the POST returns."""
        expect(self.next_link).to_be_visible(timeout=TIMEOUTS.pw_provision_ms)
