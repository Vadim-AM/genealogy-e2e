"""POM for the sources-block inside the person editor.

Selectors from js/components/sources-block.js. The block lets an editor
attach historical references (sources) to a person — search an existing
source or type a new name and create it on link.

Layout:
    .editor-section.sources-block
      #sourceSearchInput   <- search / new-source name
      #sourceDropdown      <- autocomplete results
      #sourceTypeSelect    <- source type (default: document)
      #linkSourceBtn       <- "Привязать"
      #personSourcesList   <- attached sources
        .sources-item[data-link-id] > .sources-item-name
                              .sources-item-remove (x unlink)
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from framework.step import step


class SourcesBlock:
    """Drives the sources-block: create+link a source, unlink one."""

    def __init__(self, page: Page) -> None:
        self.page = page

    @property
    def search(self) -> Locator:
        """Source search input."""
        return self.page.locator("#sourceSearchInput")

    @property
    def btn_link(self) -> Locator:
        """Link source button."""
        return self.page.locator("#linkSourceBtn")

    @property
    def list(self) -> Locator:
        """Attached sources list container."""
        return self.page.locator("#personSourcesList")

    @property
    def items(self) -> Locator:
        """Individual source items in the list."""
        return self.list.locator('[data-testid="source-item"]')

    def create_and_link(self, *, name: str) -> None:
        """Type a new source name and click link. With no dropdown
        pick, the block auto-creates the source (default type) and links
        it to the person."""
        with step("действие: создать и привязать источник"):
            self.search.fill(name)
            self.btn_link.click()

    @property
    def item_names(self) -> Locator:
        """Имена привязанных источников."""
        return self.items.locator('[data-testid="source-item-name"]')

    @property
    def item_remove_btns(self) -> Locator:
        """Кнопки удаления привязанных источников."""
        return self.items.locator('[data-testid="source-item-remove"]')

    def expect_attached(self, name: str) -> None:
        """Assert exactly one source is attached with the given name."""
        with step("проверка: источник привязан"):
            expect(self.items).to_have_count(1)
            expect(self.item_names).to_contain_text(name)

    def unlink_first(self) -> None:
        """Click the remove button on the first attached source."""
        with step("действие: отвязать первый источник"):
            self.item_remove_btns.first.click()
