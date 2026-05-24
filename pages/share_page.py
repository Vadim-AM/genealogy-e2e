"""POM for the public share page (/share/{token}).

An anonymous visitor sees a read-only person card. If the share is
revoked or invalid, a `.share-error` block is shown instead.
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from framework.step import step


class SharePage:
    """Drives the public share page: inspect person, check errors."""

    def __init__(self, page: Page):
        self.page = page

    @property
    def person_name(self) -> Locator:
        """Shared person name element."""
        return self.page.locator('[data-testid="share-name"]')

    @property
    def error(self) -> Locator:
        """Share error block."""
        return self.page.locator('[data-testid="share-error"]')

    @property
    def edit_button(self) -> Locator:
        """Edit button (should not be present on shared page)."""
        return self.page.locator('[data-action="profile-edit"]')

    def expect_person_visible(self, name_substring: str) -> None:
        """Assert the shared person name contains the given substring."""
        with step("проверка: персона видна на share"):
            expect(self.person_name).to_contain_text(name_substring)

    def expect_error_visible(self) -> None:
        """Assert the share error block is visible."""
        with step("проверка: ошибка share видна"):
            expect(self.error).to_be_visible()

    def expect_no_edit_controls(self) -> None:
        """Assert no edit button is present on the shared page."""
        with step("проверка: нет контролов редактирования"):
            expect(self.edit_button).to_have_count(0)
