"""Timeout catalogue for the e2e suite.

Single source of truth for every timeout the suite uses, so heavier
environments (CI, Docker, slow networks) can scale them via one env var
instead of editing dozens of files.

Two channels are tunable:
  - `TIMEOUTS.<field>` — float seconds, used in `httpx` calls and custom
    polling loops (enrichment job completion, etc.).
  - `set_playwright_default_expect_timeout()` — applied once at session
    start in `conftest.py`, multiplies the `expect()` auto-wait window.

Usage:
    from tests.timeouts import TIMEOUTS
    httpx.get(url, timeout=TIMEOUTS.api_request)

To bump everything 2× for a slow CI runner:
    E2E_TIMEOUT_MULTIPLIER=2.0 pytest tests/

Field semantics — pick the smallest one that fits the operation:
  - `api_short`   (5s)  — fire-and-forget admin/test endpoints
  - `api_request` (10s) — typical product API call
  - `api_long`    (30s) — exports / bulk operations
  - `health_gate` (30s) — subprocess /api/health bootstrap window
  - `enrichment_poll` (30s) — background job completion
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _multiplier() -> float:
    """Read `E2E_TIMEOUT_MULTIPLIER` (default 1.0) — applied to ALL timeouts.

    Set >1 in CI/Docker/slow networks; <1 only when debugging locally with
    deliberately tight budgets (rare).
    """
    raw = os.environ.get("E2E_TIMEOUT_MULTIPLIER", "1.0")
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(
            f"E2E_TIMEOUT_MULTIPLIER must be a positive float, got {raw!r}"
        ) from exc
    if value <= 0:
        raise ValueError(f"E2E_TIMEOUT_MULTIPLIER must be positive, got {value}")
    return value


@dataclass(frozen=True)
class _Timeouts:
    api_short: float
    api_request: float
    api_long: float
    health_gate: float
    enrichment_poll: float
    # Playwright `expect()` auto-wait window in MILLISECONDS.
    pw_expect_ms: int


def _build() -> _Timeouts:
    m = _multiplier()
    return _Timeouts(
        api_short=5.0 * m,
        api_request=10.0 * m,
        api_long=30.0 * m,
        health_gate=30.0 * m,
        enrichment_poll=30.0 * m,
        pw_expect_ms=int(5_000 * m),
    )


TIMEOUTS = _build()


def set_playwright_default_expect_timeout() -> None:
    """Apply `TIMEOUTS.pw_expect_ms` to Playwright's `expect()` auto-wait
    default. Call once at session start (in conftest)."""
    from playwright.sync_api import expect

    expect.set_options(timeout=TIMEOUTS.pw_expect_ms)
