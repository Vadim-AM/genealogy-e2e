"""Security boundary tests — TC-SEC-1, TC-SEC-2.

Verifies the public/private surface separation and the security HTTP headers
required for the beta launch.
"""

from __future__ import annotations

import re

import httpx
import pytest

from tests.timeouts import TIMEOUTS


# ─────────────────────────────────────────────────────────────────────────
# TC-SEC-1: Anonymous → 401 на закрытых endpoints
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/people",
        "/api/account/tenant/invites",
        "/api/admin/invites",
        "/api/platform/metrics",
    ],
)
def test_anonymous_get_returns_401_on_private_endpoints(base_url: str, endpoint: str):
    """TC-SEC-1: GET <private> без cookies → 401.

    Public surface is allowed (e.g. `/api/tree` returns 200 with the demo
    showcase) — those are tested separately in `test_landing.py`.
    """
    r = httpx.get(f"{base_url}{endpoint}", timeout=TIMEOUTS.api_request)
    assert r.status_code == 401, \
        f"GET {endpoint} returned {r.status_code} {r.text[:200]} (expected 401)"


def test_anonymous_get_tree_returns_200_minimal_showcase(base_url: str):
    """TC-SEC-1 inverse: /api/tree IS public — guest sees the showcase tree."""
    r = httpx.get(f"{base_url}/api/tree", timeout=TIMEOUTS.api_request)
    assert r.status_code == 200, \
        f"GET /api/tree returned {r.status_code} (must be public 200)"


# ─────────────────────────────────────────────────────────────────────────
# TC-SEC-2: Security headers
# ─────────────────────────────────────────────────────────────────────────


REQUIRED_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
}


def test_security_headers_present_on_api_responses(base_url: str):
    """TC-SEC-2: required security headers on every response.

    Picks `/api/account/me` (anonymous → 401) — headers must be set on every
    response, including error ones, so attackers cannot get a privileged
    response without protection.
    """
    r = httpx.get(f"{base_url}/api/account/me", timeout=TIMEOUTS.api_request)
    # Auth state irrelevant — we test headers, not body.
    headers = {k.lower(): v for k, v in r.headers.items()}

    for header, expected in REQUIRED_HEADERS.items():
        actual = headers.get(header)
        assert actual == expected, \
            f"{header}: expected {expected!r}, got {actual!r}"


def test_csp_header_disables_inline_event_handlers(base_url: str):
    """TC-SEC-2 / BUG-SEC-002: CSP must include `script-src-attr 'none'`
    so inline `onclick=` event handlers cannot execute (XSS hardening)."""
    r = httpx.get(f"{base_url}/api/account/me", timeout=TIMEOUTS.api_request)
    csp = r.headers.get("content-security-policy", "")
    assert csp, "Content-Security-Policy header missing"
    # Look for the directive — quoted 'none' may or may not appear depending
    # on serialisation. Use a regex tolerant of single-quotes / spacing.
    assert re.search(r"script-src-attr\s+'none'", csp), \
        f"CSP missing `script-src-attr 'none'`: {csp[:200]}"


# ─────────────────────────────────────────────────────────────────────────
# TC-CSP-2 / BUG-CSP-001: inline event handlers in served HTML
# ─────────────────────────────────────────────────────────────────────────


def test_landing_html_has_no_inline_event_handlers(base_url: str):
    """TC-CSP-2: served `/` HTML doesn't contain any `on<ident>=` attribute.

    CSP header alone не достаточно: оно блокирует только runtime (handler
    не выполнится), но HTML с inline `onload=` всё равно ломает функцию
    (например, fonts.css media=print → media=all переключение). Тест
    ловит **факт** наличия inline event handlers в shipped HTML — это
    регрессия BUG-SEC-002 sweep.
    """
    r = httpx.get(f"{base_url}/", timeout=TIMEOUTS.api_request)
    r.raise_for_status()
    html = r.text

    # Match `on<lowercase-ident>=` as HTML attribute (whitespace before,
    # `=` after). Exclude false positives like `name="oncall"` because
    # those have `=` after `name`, not after the `on*` substring.
    pattern = re.compile(r'\s(on[a-z]+)\s*=', re.IGNORECASE)
    matches = pattern.findall(html)
    unique = sorted(set(m.lower() for m in matches))

    assert not matches, (
        f"inline event handlers found in /: {unique}. CSP `script-src-attr "
        f"'none'` blocks them at runtime, but the HTML still ships them — "
        f"this is a BUG-SEC-002 sweep regression. Use addEventListener "
        f"instead of inline `on*=` attributes."
    )


def test_hsts_header_only_on_https(base_url: str):
    """TC-SEC-2: HSTS is conditional on the request being HTTPS.

    Local dev runs over HTTP; the header MUST NOT appear here (otherwise
    it would lock browsers into a stale config). On HTTPS deploys the
    header is added by `security_headers` middleware.
    """
    assert base_url.startswith("http://"), \
        "this test assumes local dev (HTTP); HTTPS path is verified by deployment smoke"
    r = httpx.get(f"{base_url}/api/account/me", timeout=TIMEOUTS.api_request)
    assert "strict-transport-security" not in {k.lower() for k in r.headers.keys()}, \
        "HSTS must not be sent on HTTP responses (only HTTPS)"
