"""Module-level side effects applied at suite load.

- Monkey-patches `httpx.Client.request` to inject the test-only `X-Test-Token`
  header on `/api/_test/*` calls and an `Origin` header on mutating methods
  (backend CSRF middleware enforces it independently of `IS_TESTING`).
- Applies `E2E_TIMEOUT_MULTIPLIER` to Playwright's `expect()` default once
  per session.

Loaded as a pytest plugin via root `conftest.py::pytest_plugins`. The module
import itself triggers the patch — there is no fixture to depend on.
"""

from __future__ import annotations

import os

import httpx

from tests.constants import TestConfig
from tests.timeouts import set_playwright_default_expect_timeout

# Shared secret for `/api/_test/*` endpoints (backend gates them with
# `hmac.compare_digest` against `GENEALOGY_TEST_TOKEN`). Not set in
# production → those endpoints return 503.
_E2E_TEST_TOKEN = os.environ.get("E2E_TEST_TOKEN", TestConfig.TEST_TOKEN_DEFAULT)

_orig_httpx_request = httpx.Client.request


def _origin_for(client_base_url: str, request_url: str) -> str:
    """Derive same-origin header value: scheme://host[:port]."""
    src = client_base_url or request_url
    src = str(src)
    if "://" not in src:
        return src
    scheme, rest = src.split("://", 1)
    host = rest.split("/", 1)[0]
    return f"{scheme}://{host}"


def _patched_request(self, method, url, **kwargs):
    """Inject suite-required headers into every httpx-request:

    1. `X-Test-Token` for `/api/_test/*` — bypasses test-endpoint gate.
    2. `Origin` for mutating methods — backend CSRF middleware checks
       Origin/Referer on every POST/PATCH/PUT/DELETE.

    Suite tests don't need to know about either header.
    """
    url_str = str(url) if url is not None else ""
    headers = dict(kwargs.get("headers") or {})

    if "/api/_test/" in url_str:
        headers.setdefault("X-Test-Token", _E2E_TEST_TOKEN)

    if str(method).upper() in ("POST", "PATCH", "PUT", "DELETE"):
        client_base = str(getattr(self, "base_url", "") or "")
        headers.setdefault("Origin", _origin_for(client_base, url_str))

    kwargs["headers"] = headers
    return _orig_httpx_request(self, method, url, **kwargs)


httpx.Client.request = _patched_request

# Apply the timeout multiplier to Playwright's `expect()` once per session.
set_playwright_default_expect_timeout()
