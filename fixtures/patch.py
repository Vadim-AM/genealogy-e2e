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

import contextlib
import itertools
import os
import threading
from typing import Any

import httpx

from config.settings import settings
from config.timeouts import set_playwright_default_expect_timeout

TEST_TOKEN = settings.test_token

# ── Per-client synthetic source IP (parallel pass only) ────────────────
# Under xdist every worker hits the backend from the same host
# (127.0.0.1). The parallel pass has no per-test global reset, so the
# programmatic rate-limit `_buckets` aren't cleared and the `login:<ip>`
# throttle (10/60s — intentionally ON in test mode, a documented
# brute-force invariant we must NOT weaken) fires across workers sharing
# that one IP. Give every `httpx.Client` a distinct synthetic
# `X-Forwarded-For` so each logical client is its own rate-limit
# identity: the throttle stays genuine *per identity* (a single-client
# brute-force test still hits 429), the suite stays green. Needs the e2e
# target booted with `GENEALOGY_TRUST_FORWARDED_FOR=1` (a config flag of
# our test instance — the same one prod uses behind Caddy — not a
# product change).
#
# Gated on `PYTESTXDIST_WORKER`: the serial pass runs `-p no:xdist`
# (var unset) → no injection → real `request.client.host` preserved, so
# serial semantics and the audit-log IP-hash tests are unchanged.
XDIST_WORKER = os.environ.get("PYTESTXDIST_WORKER")  # "gw3" | None


def worker_octet() -> int:
    """Extract numeric worker index from PYTESTXDIST_WORKER and wrap to 0-255."""
    digits = "".join(c for c in (XDIST_WORKER or "") if c.isdigit())
    return (int(digits) if digits else 0) % 256


WORKER_OCTET = worker_octet()
_xff_counter = itertools.count(1)
_xff_lock = threading.Lock()


def next_synthetic_xff() -> str:
    """`10.<worker>.<hi>.<lo>` — unique per (xdist worker, client) for
    the whole run. The backend uses the value verbatim as the rate-limit
    bucket key (`client_ip()`), so it need not be a routable address."""
    with _xff_lock:
        n = next(_xff_counter)
    return f"10.{WORKER_OCTET}.{(n >> 8) & 0xFF}.{n & 0xFF}"


_orig_httpx_request = httpx.Client.request


def origin_for(client_base_url: str, request_url: str) -> str:
    """Derive same-origin header value: scheme://host[:port]."""
    src = client_base_url or request_url
    src = str(src)
    if "://" not in src:
        return src
    scheme, rest = src.split("://", 1)
    host = rest.split("/", 1)[0]
    return f"{scheme}://{host}"


def patched_request(self: httpx.Client, method: str, url: object, **kwargs: Any) -> httpx.Response:
    """Inject suite-required headers into every httpx-request:

    1. `X-Test-Token` for `/api/_test/*` — bypasses test-endpoint gate.
    2. `Origin` for mutating methods — backend CSRF middleware checks
       Origin/Referer on every POST/PATCH/PUT/DELETE.

    Suite tests don't need to know about either header.
    """
    url_str = str(url) if url is not None else ""
    headers = dict(kwargs.get("headers") or {})

    if "/api/_test/" in url_str:
        headers.setdefault("X-Test-Token", TEST_TOKEN)

    if str(method).upper() in ("POST", "PATCH", "PUT", "DELETE"):
        client_base = str(getattr(self, "base_url", "") or "")
        headers.setdefault("Origin", origin_for(client_base, url_str))

    if XDIST_WORKER:
        # One stable synthetic source IP per Client instance (cached on
        # the client). `signup_via_api`/`tenant_client` make a client per
        # test/identity → that flow's login is alone in its bucket.
        # `setdefault` so a test that sets its own X-Forwarded-For
        # (e.g. to drive rate-limit behaviour) keeps control.
        xff = getattr(self, "_e2e_xff", None)
        if xff is None:
            xff = next_synthetic_xff()
            with contextlib.suppress(Exception):
                self._e2e_xff = xff  # type: ignore[attr-defined]
        headers.setdefault("X-Forwarded-For", xff)

    kwargs["headers"] = headers
    return _orig_httpx_request(self, method, url, **kwargs)  # type: ignore[arg-type]


httpx.Client.request = patched_request  # type: ignore[method-assign]

# Apply the timeout multiplier to Playwright's `expect()` once per session.
set_playwright_default_expect_timeout()
