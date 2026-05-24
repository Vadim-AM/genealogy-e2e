"""i18n text-checking helpers."""

from __future__ import annotations

import re

CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")


def has_cyrillic(s: str) -> bool:
    """Return True if the string contains at least one Cyrillic character."""
    return bool(CYRILLIC_RE.search(s or ""))
