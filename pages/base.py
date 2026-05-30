"""Base page object — shared helpers for every page.

Pattern:
    page = SignupPage(playwright_page).goto()
    page.fill_email("ivan@test").submit()
    page.expect_verification_sent()
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Self

from framework.step import step

if TYPE_CHECKING:
    from playwright.sync_api import Dialog, Locator, Page, Response

_CS_WRAPPER = '[data-testid="custom-select"]:has(+ select[data-field="{}"])'
_CS_TRIGGER = '[data-testid="custom-select-trigger"]'
_CS_OPTION = '[data-testid="custom-select-option"][data-value="{}"]'


def custom_select_for(page: Page, field: str) -> Locator:
    """Return the custom-select wrapper for a native select[data-field]."""
    return page.locator(_CS_WRAPPER.format(field))


class BasePage:
    """Common ground for every page object. Subclass overrides URL + locators."""

    URL: str = "/"

    def __init__(self, page: Page) -> None:
        self.page = page

    def goto(self, *, query: str = "") -> Self:
        """Navigate to the page URL and return self for chaining."""
        with step(f"навигация: переход на {self.URL}"):
            url = self.URL + (f"?{query}" if query else "")
            self.page.goto(url)
        return self

    def goto_and_load(self, *, query: str = "") -> Self:
        """Navigate to the page URL, wait for DOM content loaded, return self."""
        with step(f"навигация: переход и загрузка {self.URL}"):
            self.goto(query=query)
            self.page.wait_for_load_state("domcontentloaded")
        return self

    def goto_with_response(self, *, query: str = "") -> Response:
        """Navigate to the page URL and return the navigation Response."""
        with step(f"навигация: переход на {self.URL} с ответом"):
            url = self.URL + (f"?{query}" if query else "")
            response = self.page.goto(url)
        if response is None:
            raise RuntimeError(f"navigation to {url!r} returned no response")
        return response

    def wait_for_page_load(self) -> None:
        """Wait for the DOM content to be loaded."""
        with step("ожидание: загрузка DOM"):
            self.page.wait_for_load_state("domcontentloaded")

    # ── Document-level measurements (shared by ui/responsive tests) ──

    def page_title(self) -> str:
        """Return the document title."""
        return self.page.title()

    def page_html(self) -> str:
        """Return the full serialized HTML of the page."""
        return self.page.content()

    def html_lang(self) -> str:
        """Return the document's <html lang> attribute value."""
        return str(self.page.evaluate("() => document.documentElement.lang"))

    def seed_local_storage(self, key: str, value: str) -> Self:
        """Pre-seed a localStorage key via init script (before navigation)."""
        self.page.add_init_script(
            f"try {{ localStorage.setItem({json.dumps(key)}, {json.dumps(value)}); }} catch (e) {{}}"
        )
        return self

    def has_horizontal_overflow(self) -> bool:
        """Whether the document overflows horizontally (scrollWidth > clientWidth)."""
        return bool(
            self.page.evaluate(
                "() => document.documentElement.scrollWidth"
                " > document.documentElement.clientWidth"
            )
        )

    def element_size(self, locator: Locator) -> tuple[float, float]:
        """Return (width, height) of a rendered element's bounding box."""
        box = locator.bounding_box()
        if box is None:
            raise RuntimeError("bounding_box() is None — element not rendered")
        return box["width"], box["height"]

    def element_right_edge(self, locator: Locator) -> float:
        """Return the x-coordinate of an element's right edge (x + width)."""
        box = locator.bounding_box()
        if box is None:
            raise RuntimeError("bounding_box() is None — element not rendered")
        return box["x"] + box["width"]

    def watch_dialogs(self) -> list[str]:
        """Register a JS-dialog listener; the returned list fills with any
        alert/confirm/prompt messages — used to detect an executed XSS payload."""
        messages: list[str] = []

        def _on_dialog(dialog: Dialog) -> None:
            messages.append(dialog.message)
            dialog.dismiss()

        self.page.on("dialog", _on_dialog)
        return messages
