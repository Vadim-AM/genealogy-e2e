"""Timeout catalogue for the e2e suite.

Дефолтный timeout для httpx (10s × multiplier) встроен в monkey-patch
(fixtures/patch.py). Здесь — только overrides и Playwright-значения.

Для тяжёлых операций (export, enrichment): timeout=TIMEOUTS.api_long.
Для polling loops: time.sleep(TIMEOUTS.polling_interval).
Для всего остального — дефолт, не передавать timeout= явно.

Чтобы увеличить все таймауты для медленного CI:
    E2E_TIMEOUT_MULTIPLIER=2.0 pytest tests/
"""

from __future__ import annotations

from dataclasses import dataclass

from config.settings import settings


@dataclass(frozen=True)
class Timeouts:
    default: float
    api_long: float
    health_gate: float
    enrichment_poll: float
    polling_interval: float
    pw_expect_ms: int
    pw_action_ms: int
    pw_provision_ms: int


def build_timeouts() -> Timeouts:
    """Build timeout values scaled by E2E_TIMEOUT_MULTIPLIER."""
    m = settings.timeout_multiplier
    return Timeouts(
        default=10.0 * m,
        api_long=30.0 * m,
        health_gate=30.0 * m,
        enrichment_poll=30.0 * m,
        polling_interval=0.3 * m,
        pw_expect_ms=int(5_000 * m),
        pw_action_ms=int(10_000 * m),
        pw_provision_ms=int(15_000 * m),
    )


TIMEOUTS = build_timeouts()


def set_playwright_default_expect_timeout() -> None:
    """Apply TIMEOUTS.pw_expect_ms to Playwright's expect() auto-wait default."""
    from playwright.sync_api import expect

    expect.set_options(timeout=TIMEOUTS.pw_expect_ms)
