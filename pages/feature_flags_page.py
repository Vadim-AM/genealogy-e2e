"""POM for Feature Flags section on /platform/dashboard.

Selectors from platform-dashboard.html — the Feature Flags section
renders groups (`[data-testid="ff-group"]`), each with a title and
toggle inputs. Toggle inputs use `#ff_<flag_name>` IDs.
"""

from __future__ import annotations

from typing import Self

from playwright.sync_api import Locator, Page, expect

from framework.step import step

from .base import BasePage


class FeatureFlagsPage(BasePage):
    """Drives the Feature Flags section on the platform dashboard."""

    URL = "/platform/dashboard"

    def __init__(self, page: Page):
        super().__init__(page)

    @property
    def section(self) -> Locator:
        """no semantic: layout container"""
        return self.page.locator("#feature_flags_section")

    @property
    def groups(self) -> Locator:
        """no semantic: data-testid element, no role"""
        return self.page.locator('[data-testid="ff-group"]')

    @property
    def group_titles(self) -> Locator:
        """no semantic: data-testid element, no role"""
        return self.page.locator('[data-testid="ff-group-title"]')

    @property
    def ai_search_toggle(self) -> Locator:
        """no semantic: form input without label"""
        return self.page.locator("#ff_enable_ai_search")

    @property
    def beta_cap_input(self) -> Locator:
        """no semantic: form input without label"""
        return self.page.locator("#set_beta_cap")

    @property
    def help_icons(self) -> Locator:
        """no semantic: data-testid element, no role"""
        return self.page.locator('#feature_flags_section [data-testid="ff-help"]')

    def expect_section_visible(self) -> None:
        """Assert the Feature Flags section is visible."""
        with step("проверка: секция Feature Flags видима"):
            expect(self.section).to_be_visible()

    def wait_for_settings_loaded(self) -> None:
        """Wait for loadSettings() to populate inputs.

        CSP-safe locator assertion (not wait_for_function); beta_cap_input
        receives a value only after loadSettings() completes.
        """
        with step("ожидание: загрузка настроек"):
            expect(self.beta_cap_input).not_to_have_value("")

    def group_title_texts(self) -> set[str]:
        """Return the set of visible group title texts."""
        return {h.inner_text().strip() for h in self.group_titles.all()}

    def ai_search_row(self) -> Locator:
        """Return the .ff-row ancestor of the AI search toggle."""
        return self.page.locator(
            "#ff_enable_ai_search >> xpath=ancestor::div[contains(@class, 'ff-row')]"
        ).first

    def ai_search_data_flag(self) -> str | None:
        """Return the data-flag attribute of the AI search toggle."""
        return self.ai_search_toggle.get_attribute("data-flag")

    def is_ai_search_checked(self) -> bool:
        """Return whether the AI search toggle is checked."""
        return self.ai_search_toggle.is_checked()

    def click_ai_search_toggle(self) -> Self:
        """Click the AI search toggle."""
        with step("действие: переключить AI search"):
            self.ai_search_toggle.click()
        return self

    def help_tooltip_texts(self) -> list[str]:
        """Return the list of title attributes from help icons."""
        return [
            (self.help_icons.nth(i).get_attribute("title") or "").strip()
            for i in range(self.help_icons.count())
        ]
