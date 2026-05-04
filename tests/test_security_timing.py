"""TC-SEC-3, TC-SEC-4: timing-based account enumeration на signup и login.

**Сценарий attack:** злоумышленник POST'ит `/api/account/signup` или
`/api/account/login` с разными email'ами и измеряет latency. Если
backend для существующего email возвращает быстрее (короткий
hash-comparison + raise) чем для нового (полный flow: hash + DB
insert + mail dispatch), разница в timing позволяет перебрать базу
даже когда **content** ответа одинаковый.

**Контракт безопасности:** медианное время ответа на existing и new
email должно быть в пределах **2×** друг от друга. Reference values
после equal-work фикса (commit `c39863b`) — около 1.0-1.3×.

**Run 2 (28.04, до фикса):**
- signup: ≈ **9×** разница p50 (existing ≈5ms, new ≈37ms).
- login:  ≈ **14×** разница p50 (non-existent ≈2ms, existent ≈33ms).

**Equal-work fix** (применимо к обоим):
- Всегда выполнять password-hash (даже когда user отсутствует).
- Всегда отправлять mail (или dummy queue task).
- Использовать `hmac.compare_digest` или фиксированный sleep
  для выравнивания.

**Caveat — CI/jitter:** GitHub runners шумные, single-iteration
latency может варьироваться. Тесты помечены `@pytest.mark.slow`
и активируются только под `RUN_SLOW=1` env (или явный select),
чтобы не флакать дефолтный CI. Локально/при ручной верификации
прогон стабильный (30 iterations × 2× threshold).
"""

from __future__ import annotations

import os
import time
import uuid

import httpx
import pytest

from tests.timeouts import TIMEOUTS


_ITERATIONS = 30
_RATIO_THRESHOLD = 2.0

# Тесты затратные (60+ HTTP roundtrip'ов) и чувствительны к runner jitter,
# но это не повод их скипать — timing-attack это security regression,
# должно ловиться. Помечены `@pytest.mark.slow` для отдельной фильтрации
# (`pytest -m "not slow"` исключит), но по умолчанию запускаются вместе
# с остальным suite.
pytestmark = pytest.mark.slow


def _measure(client: httpx.Client, reset_url: str, make_call) -> float:
    """Single iteration: reset signup throttle, measure call duration."""
    httpx.post(reset_url, timeout=TIMEOUTS.api_short).raise_for_status()
    start = time.perf_counter()
    make_call(client)
    return time.perf_counter() - start


def _ratio(slow_samples: list[float], fast_samples: list[float]) -> float:
    """Median ratio (slow / fast). Median is robust to jitter outliers."""
    s = sorted(slow_samples)
    f = sorted(fast_samples)
    p50_slow = s[len(s) // 2]
    p50_fast = f[len(f) // 2]
    return p50_slow / p50_fast if p50_fast > 0 else float("inf")


def test_signup_no_timing_account_enumeration(uvicorn_server: str, signup_via_api):
    """TC-SEC-3: signup p50 latency for existing ≈ new email (ratio < 3×).

    Was xfail under BUG-SEC-003 (≈9× ratio in Run 2) until upstream
    commit `c39863b` ("fix(auth-v2): equal-work для anti-enumeration"
    — added always-run password hash + dummy delay). Now plain
    regression.

    Pre-seeds one verified user, then alternates batches of POSTs for
    that email vs throw-away new emails. Reset slowapi between calls
    so the rate-limit doesn't dominate latency.
    """
    reset_url = f"{uvicorn_server}/api/_test/reset-signup-rate"

    existing_email = f"timing-existing-{uuid.uuid4().hex[:8]}@e2e.example.com"
    signup_via_api(email=existing_email)

    payload_template = {
        "password": "test_password_8plus",
        "full_name": "Тестовый Пользователь",
    }

    def call_existing(c: httpx.Client) -> None:
        c.post("/api/account/signup", json={**payload_template, "email": existing_email})

    def call_new(c: httpx.Client) -> None:
        c.post(
            "/api/account/signup",
            json={**payload_template, "email": f"timing-new-{uuid.uuid4().hex[:8]}@e2e.example.com"},
        )

    with httpx.Client(base_url=uvicorn_server, timeout=TIMEOUTS.api_request) as c:
        latencies_existing = [_measure(c, reset_url, call_existing) for _ in range(_ITERATIONS)]
        latencies_new = [_measure(c, reset_url, call_new) for _ in range(_ITERATIONS)]

    ratio = _ratio(latencies_new, latencies_existing)
    p50_new_ms = sorted(latencies_new)[_ITERATIONS // 2] * 1000
    p50_existing_ms = sorted(latencies_existing)[_ITERATIONS // 2] * 1000

    assert ratio < _RATIO_THRESHOLD, (
        f"signup timing leaks account existence: "
        f"new p50={p50_new_ms:.1f}ms, existing p50={p50_existing_ms:.1f}ms, "
        f"ratio={ratio:.1f}× (must be <{_RATIO_THRESHOLD}×)"
    )


def test_login_no_timing_account_enumeration(uvicorn_server: str, signup_via_api):
    """TC-SEC-4: login p50 latency for wrong-password ≈ non-existent (ratio < 3×).

    Both branches return 401, but slow branch does bcrypt verify, fast
    branch returns immediately on user-not-found. Equal-work fix: dummy
    bcrypt for missing user.
    """
    reset_url = f"{uvicorn_server}/api/_test/reset-signup-rate"

    existing_email = f"timing-login-{uuid.uuid4().hex[:8]}@e2e.example.com"
    signup_via_api(email=existing_email)

    def call_existing_wrong_pwd(c: httpx.Client) -> None:
        c.post(
            "/api/account/login",
            json={"email": existing_email, "password": "wrong-password-here"},
        )

    def call_nonexistent(c: httpx.Client) -> None:
        c.post(
            "/api/account/login",
            json={
                "email": f"timing-nope-{uuid.uuid4().hex[:8]}@e2e.example.com",
                "password": "wrong-password-here",
            },
        )

    with httpx.Client(base_url=uvicorn_server, timeout=TIMEOUTS.api_request) as c:
        latencies_existing = [_measure(c, reset_url, call_existing_wrong_pwd) for _ in range(_ITERATIONS)]
        latencies_nonexistent = [_measure(c, reset_url, call_nonexistent) for _ in range(_ITERATIONS)]

    ratio = _ratio(latencies_existing, latencies_nonexistent)
    p50_existing_ms = sorted(latencies_existing)[_ITERATIONS // 2] * 1000
    p50_nonexistent_ms = sorted(latencies_nonexistent)[_ITERATIONS // 2] * 1000

    assert ratio < _RATIO_THRESHOLD, (
        f"login timing leaks account existence: "
        f"existing-wrong-pwd p50={p50_existing_ms:.1f}ms, "
        f"non-existent p50={p50_nonexistent_ms:.1f}ms, "
        f"ratio={ratio:.1f}× (must be <{_RATIO_THRESHOLD}×)"
    )
