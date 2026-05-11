"""Root pytest config.

Two responsibilities only:

1. Register fixture plugins (broken out by topic in `tests/_fixtures/`).
2. Apply the suite's domain-marker convention by file path: tests under
   `tests/<domain>/` automatically pick up `@pytest.mark.<domain>`.

Fixture content lives in `tests/_fixtures/`:
  - `patch.py`    — httpx monkey-patch + Playwright `expect()` default
  - `server.py`   — base_url / health gate / reset / AI-mock install
  - `users.py`    — AuthUser + signup / login / invite factories
  - `clients.py`  — tenant_client / auth_context_factory / owner_page
  - `utils.py`    — soft_check
"""

from __future__ import annotations

import pytest

pytest_plugins = (
    "tests._fixtures.patch",
    "tests._fixtures.server",
    "tests._fixtures.users",
    "tests._fixtures.clients",
    "tests._fixtures.utils",
)

_DOMAIN_MARKERS = frozenset({
    "auth", "tree", "platform", "admin",
    "security", "enrichment", "ui",
})


def pytest_collection_modifyitems(items):
    """Auto-apply `@pytest.mark.<domain>` to tests under `tests/<domain>/`.

    Lets the suite filter by domain (`pytest -m auth`) without per-file
    `pytestmark` lines. Tests at the root of `tests/` get no auto marker.
    """
    for item in items:
        domain = item.path.parent.name
        if domain in _DOMAIN_MARKERS:
            item.add_marker(getattr(pytest.mark, domain))
