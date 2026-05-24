"""POM for the sources-block inside the person editor.

Selectors from js/components/sources-block.js. The block lets an editor
attach historical references (sources) to a person — search an existing
source or type a new name and create it on link.

Layout:
    .editor-section.sources-block
      #sourceSearchInput   ← search / new-source name
      #sourceDropdown      ← autocomplete results
      #sourceTypeSelect    ← source type (default: document)
      #linkSourceBtn       ← "Привязать"
      #personSourcesList   ← attached sources
        .sources-item[data-link-id] > .sources-item-name
                              .sources-item-remove (× unlink)
"""

from __future__ import annotations

from playwright.sync_api import Page, expect


class SourcesBlock:
    """Drives the sources-block: create+link a source, unlink one."""

    def __init__(self, page: Page):
        self.page = page
        self.search = page.locator("#sourceSearchInput")
        self.btn_link = page.locator("#linkSourceBtn")
        self.list = page.locator("#personSourcesList")
        self.items = self.list.locator('[data-testid="source-item"]')

    def create_and_link(self, *, name: str) -> None:
        """Type a new source name and click Привязать. With no dropdown
        pick, the block auto-creates the source (default type) and links
        it to the person."""
        self.search.fill(name)
        self.btn_link.click()

    def expect_attached(self, name: str) -> None:
        """Assert exactly one source is attached with the given name."""
        expect(self.items).to_have_count(1)
        expect(self.items.locator('[data-testid="source-item-name"]')).to_contain_text(name)

    def unlink_first(self) -> None:
        """Click the remove button on the first attached source."""
        self.items.locator('[data-testid="source-item-remove"]').first.click()
