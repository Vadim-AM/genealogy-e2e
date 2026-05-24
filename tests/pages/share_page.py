"""POM for the public share page (/share/{token}).

An anonymous visitor sees a read-only person card. If the share is
revoked or invalid, a `.share-error` block is shown instead.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect


class SharePage:
    """Drives the public share page: inspect person, check errors."""

    def __init__(self, page: Page):
        self.page = page
        self.person_name = page.locator('[data-testid="share-name"]')
        self.error = page.locator('[data-testid="share-error"]')
        self.edit_button = page.locator('[data-action="profile-edit"]')

    def expect_person_visible(self, name_substring: str) -> None:
        """Assert the shared person name contains the given substring."""
        expect(self.person_name).to_contain_text(name_substring)

    def expect_error_visible(self) -> None:
        """Assert the share error block is visible."""
        expect(self.error).to_be_visible()

    def expect_no_edit_controls(self) -> None:
        """Assert no edit button is present on the shared page."""
        expect(self.edit_button).to_have_count(0)
