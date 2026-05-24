"""TC-SEC-3, TC-SEC-4: timing-based account enumeration на signup и login."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
import httpx
import pytest

from api import routes
from assertions.base import should
from config.constants import TestConfig, unique_email
from framework.step import step
from helpers.security.timing import ITERATIONS, RATIO_THRESHOLD, measure
from helpers.security.timing import ratio as compute_ratio
from src.texts import ErrMsg

if TYPE_CHECKING:
    from collections.abc import Callable

    from fixtures.users import AuthUser


# Тесты затратные (60+ HTTP roundtrip'ов) и чувствительны к runner jitter,
# но это не повод их скипать — timing-attack это security regression,
# должно ловиться. Помечены `@pytest.mark.slow` для отдельной фильтрации
# (`pytest -m "not slow"` исключит), но по умолчанию запускаются вместе
# с остальным suite.
pytestmark = pytest.mark.slow


@allure.title("Timing: signup не выдаёт существование аккаунта по времени")
def test_signup_no_timing_account_enumeration(uvicorn_server: str, signup_via_api: Callable[..., AuthUser]) -> None:
    """TC-SEC-3: signup p50 latency for existing ≈ new email (ratio < 3×)."""
    with step("подготовка: зарегистрировать существующего пользователя"):
        reset_url = f"{uvicorn_server}{routes.TEST_RESET_SIGNUP_RATE}"

        existing_email = unique_email("timing-existing")
        signup_via_api(email=existing_email)

        payload_template = {
            "password": TestConfig.DEFAULT_PASSWORD,
            "full_name": "Тестовый Пользователь",
        }

    with step("действие: замерить latency для existing и new email"):

        def call_existing(c: httpx.Client) -> None:
            c.post(routes.SIGNUP, json={**payload_template, "email": existing_email})

        def call_new(c: httpx.Client) -> None:
            c.post(
                routes.SIGNUP,
                json={**payload_template, "email": unique_email("timing-new")},
            )

        with httpx.Client(base_url=uvicorn_server) as c:
            latencies_existing = [measure(c, reset_url, call_existing) for _ in range(ITERATIONS)]
            latencies_new = [measure(c, reset_url, call_new) for _ in range(ITERATIONS)]

    with step("проверка: ratio p50 latency < порога"):
        ratio = compute_ratio(latencies_new, latencies_existing)
        should.less(ratio, RATIO_THRESHOLD, ErrMsg.timing_leak)


@allure.title("Timing: login не выдаёт существование аккаунта по времени")
def test_login_no_timing_account_enumeration(uvicorn_server: str, signup_via_api: Callable[..., AuthUser]) -> None:
    """TC-SEC-4: login p50 latency for wrong-password ≈ non-existent (ratio < 3×)."""
    with step("подготовка: зарегистрировать существующего пользователя"):
        reset_url = f"{uvicorn_server}{routes.TEST_RESET_SIGNUP_RATE}"
        existing_email = unique_email("timing-login")
        signup_via_api(email=existing_email)

    with step("действие: замерить latency для existing и nonexistent email"):

        def call_existing_wrong_pwd(c: httpx.Client) -> None:
            c.post(
                routes.LOGIN,
                json={"email": existing_email, "password": "wrong-password-here"},
            )

        def call_nonexistent(c: httpx.Client) -> None:
            c.post(
                routes.LOGIN,
                json={
                    "email": unique_email("timing-nope"),
                    "password": "wrong-password-here",
                },
            )

        with httpx.Client(base_url=uvicorn_server) as c:
            latencies_existing = [measure(c, reset_url, call_existing_wrong_pwd) for _ in range(ITERATIONS)]
            latencies_nonexistent = [measure(c, reset_url, call_nonexistent) for _ in range(ITERATIONS)]

    with step("проверка: ratio p50 latency < порога"):
        ratio = compute_ratio(latencies_existing, latencies_nonexistent)
        should.less(ratio, RATIO_THRESHOLD, ErrMsg.timing_leak)
