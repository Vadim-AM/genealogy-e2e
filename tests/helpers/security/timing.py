"""Security timing-attack measurement helpers."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import httpx

from tests.timeouts import TIMEOUTS

if TYPE_CHECKING:
    from collections.abc import Callable

ITERATIONS = 30
RATIO_THRESHOLD = 2.0


def measure(client: httpx.Client, reset_url: str, make_call: Callable[[httpx.Client], object]) -> float:
    """Single iteration: reset signup throttle, measure call duration."""
    httpx.post(reset_url, timeout=TIMEOUTS.api_short).raise_for_status()
    start = time.perf_counter()
    make_call(client)
    return time.perf_counter() - start


def ratio(slow_samples: list[float], fast_samples: list[float]) -> float:
    """Median ratio (slow / fast). Median is robust to jitter outliers."""
    s = sorted(slow_samples)
    f = sorted(fast_samples)
    p50_slow = s[len(s) // 2]
    p50_fast = f[len(f) // 2]
    return p50_slow / p50_fast if p50_fast > 0 else float("inf")
