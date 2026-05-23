"""Photo upload helper."""

from __future__ import annotations

from playwright.sync_api import Page

from tests._data.media.jpeg import MIN_JPEG_BYTES


def upload_jpeg(page: Page, *, name: str = "test.jpg") -> None:
    """Отдать минимальный JPEG в `#photoFileInput`. Playwright обходит
    file-chooser dialog через CDP -- input может быть hidden.
    """
    page.locator("#photoFileInput").set_input_files(
        files=[{"name": name, "mimeType": "image/jpeg", "buffer": MIN_JPEG_BYTES}]
    )
