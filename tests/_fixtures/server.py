"""Backend URL resolution, health gate, per-test reset, AI-mock install.

All session/autouse fixtures that bind the suite to the external uvicorn
process live here.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import httpx
import pytest

from tests.api_paths import API
from tests.timeouts import TIMEOUTS

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _resolve_backend_url() -> str:
    url = os.environ.get("E2E_BACKEND_URL")
    if not url:
        pytest.exit(
            "E2E_BACKEND_URL is not set. Point it at a test-instrumented backend "
            "(GENEALOGY_TESTING=1) — e.g. `E2E_BACKEND_URL=http://127.0.0.1:8642 pytest`. "
            "See README for details.",
            returncode=2,
        )
    return url.rstrip("/")


def _wait_for_health(base_url: str, *, timeout: float) -> None:
    """Block until /api/health responds 200, or raise."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = httpx.get(f"{base_url}{API.HEALTH}", timeout=TIMEOUTS.api_short)
        if response.status_code == 200:
            return
        time.sleep(TIMEOUTS.polling_interval)
    raise TimeoutError(
        f"backend at {base_url} did not respond on {API.HEALTH} within {timeout}s"
    )


@pytest.fixture(scope="session")
def base_url() -> str:
    """Test-instrumented backend URL. Overrides pytest-playwright's `base_url`."""
    url = _resolve_backend_url()
    _wait_for_health(url, timeout=TIMEOUTS.health_gate)
    return url


@pytest.fixture(scope="session")
def uvicorn_server(base_url: str) -> str:
    """Alias kept for compatibility with existing tests/POM."""
    return base_url


@pytest.fixture(autouse=True)
def reset_state(uvicorn_server: str) -> None:
    """Wipe DB rows + tenants/ + rate limits + MockSender + site_config between tests."""
    httpx.post(
        f"{uvicorn_server}{API.TEST_RESET}", timeout=TIMEOUTS.api_request
    ).raise_for_status()


@pytest.fixture(scope="session", autouse=True)
def _verify_ai_search_default(install_mock_ai, uvicorn_server: str) -> None:
    """Sanity-check (session-scope): после set-platform-setting endpoint
    видит включённый AI search. Bara один раз за session, иначе кэш или env
    override проявятся на первом же тесте.

    Не на каждый тест: per-test эту fixture (`_default_ai_search_on` ниже)
    делает только POST set-platform-setting — выполняется быстро (~ms).
    Сюжет с кешем/env override стабильно проявляется при первом запросе.
    """
    httpx.post(
        f"{uvicorn_server}{API.TEST_SET_PLATFORM_SETTING}",
        json={"enable_ai_search": True},
        timeout=TIMEOUTS.api_short,
    ).raise_for_status()
    f = httpx.get(f"{uvicorn_server}{API.CONFIG_FEATURES}", timeout=TIMEOUTS.api_short)
    f.raise_for_status()
    assert f.json().get("ai_search_enabled") is True, (
        f"session sanity failed: {API.CONFIG_FEATURES} still reports "
        f"{f.json()}. Either set-platform-setting не записал в БД, либо "
        "ENABLE_AI_SEARCH env override стоит на False."
    )


@pytest.fixture(autouse=True)
def _default_ai_search_on(reset_state, uvicorn_server: str) -> None:
    """Default platform_settings.enable_ai_search → True перед каждым тестом.

    В бета-режиме (Phase B+C) дефолт в БД = False (server_default в
    миграции `r6s7t8u9v0w1`), но большинство e2e сценариев (enrichment_flow,
    consent_enforcement, regressions) требуют, чтобы AI был доступен.
    Тесты, которые специально проверяют OFF-режим (test_ai_disabled_flow.py),
    свои autouse override → False — они выполняются ПОСЛЕ этой фикстуры
    (file-local autouse > conftest autouse в pytest ordering).

    Sanity-check вынесен в session-scoped `_verify_ai_search_default`
    выше — экономит ~319 GET-запросов на полный прогон.
    """
    httpx.post(
        f"{uvicorn_server}{API.TEST_SET_PLATFORM_SETTING}",
        json={"enable_ai_search": True},
        timeout=TIMEOUTS.api_short,
    ).raise_for_status()


@pytest.fixture(scope="session", autouse=True)
def install_mock_ai(uvicorn_server: str) -> None:
    """Install AI fixture once per session (survives `/reset` — not touched by it)."""
    fixture = json.loads((FIXTURES_DIR / "ai_responses.json").read_text())
    httpx.post(
        f"{uvicorn_server}{API.TEST_INSTALL_MOCK_AI}",
        json=fixture,
        timeout=TIMEOUTS.api_request,
    ).raise_for_status()


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict, base_url: str) -> dict:
    return {
        **browser_context_args,
        "base_url": base_url,
        "viewport": {"width": 1440, "height": 900},
        "ignore_https_errors": True,
    }
