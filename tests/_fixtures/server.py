"""Backend URL resolution, health gate, per-test reset, AI-mock install.

All session/autouse fixtures that bind the suite to the external uvicorn
process live here.
"""

from __future__ import annotations

import json
import os
import time
from http import HTTPStatus
from pathlib import Path
from typing import Any

import httpx
import pytest

from tests._core.api_paths import API
from tests._core.settings import settings
from tests._core.timeouts import TIMEOUTS

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "_data" / "fixtures"


def _wait_for_health(base_url: str, *, timeout: float) -> None:
    """Block until /api/health responds 200, or raise."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = httpx.get(f"{base_url}{API.HEALTH}", timeout=TIMEOUTS.api_short)
        if response.status_code == HTTPStatus.OK:
            return
        time.sleep(TIMEOUTS.polling_interval)
    raise TimeoutError(
        f"backend at {base_url} did not respond on {API.HEALTH} within {timeout}s"
    )


@pytest.fixture(scope="session")
def base_url() -> str:
    """Test-instrumented backend URL. Overrides pytest-playwright's `base_url`."""
    url = settings.backend_url.rstrip("/")
    _wait_for_health(url, timeout=TIMEOUTS.health_gate)
    return url


@pytest.fixture(scope="session")
def uvicorn_server(base_url: str) -> str:
    """Alias kept for compatibility with existing tests/POM."""
    return base_url


def _post_reset(uvicorn_server: str) -> None:
    """POST /api/_test/reset to wipe backend state."""
    httpx.post(
        f"{uvicorn_server}{API.TEST_RESET}", timeout=TIMEOUTS.api_request
    ).raise_for_status()


def _set_ai_search_on(uvicorn_server: str) -> None:
    """Enable AI search via /api/_test/set-platform-setting."""
    httpx.post(
        f"{uvicorn_server}{API.TEST_SET_PLATFORM_SETTING}",
        json={"enable_ai_search": True},
        timeout=TIMEOUTS.api_short,
    ).raise_for_status()


@pytest.fixture(scope="session", autouse=True)
def _baseline_reset(uvicorn_server: str, tmp_path_factory: pytest.TempPathFactory) -> None:
    """One global `/api/_test/reset` for the whole run — a single clean
    baseline, NOT per-test (that was the parallelization blocker and the
    O(n) wedge tax). Tenants then accumulate across the run on purpose:
    a dirty multi-tenant backend ≈ production, and that's where
    cross-tenant/workspace leak bugs surface.

    Under xdist, session fixtures run once *per worker* against the SHARED
    backend — so a naive per-worker reset would nuke other workers'
    in-flight tenants. Gate it to exactly once via a filelock on the
    common root tmp dir (canonical pytest-xdist "do it once" pattern).
    `PYTEST_XDIST_WORKER` (not the xdist `worker_id` fixture) so this also
    works under `-p no:xdist` in the serial pass.
    """
    if os.environ.get("PYTEST_XDIST_WORKER") is None:
        _post_reset(uvicorn_server)  # master / no xdist
        return
    from filelock import FileLock

    root = tmp_path_factory.getbasetemp().parent  # shared across workers
    flag = root / "e2e_baseline_reset.done"
    with FileLock(str(flag) + ".lock"):
        if not flag.is_file():
            _post_reset(uvicorn_server)
            flag.write_text("done")


@pytest.fixture(scope="session", autouse=True)
def install_mock_ai(_baseline_reset: None, uvicorn_server: str) -> None:
    """Install AI fixture (survives `/reset` — not touched by it). After
    `_baseline_reset` so ordering is deterministic; idempotent, so the
    once-per-xdist-worker re-POST is harmless."""
    fixture = json.loads((FIXTURES_DIR / "ai_responses.json").read_text())
    httpx.post(
        f"{uvicorn_server}{API.TEST_INSTALL_MOCK_AI}",
        json=fixture,
        timeout=TIMEOUTS.api_request,
    ).raise_for_status()


@pytest.fixture(scope="session", autouse=True)
def _ai_search_on_session(install_mock_ai: None, uvicorn_server: str) -> None:
    """platform_settings.enable_ai_search → True once per session.

    Beta DB default is False (migration `r6s7t8u9v0w1`), but most e2e
    scenarios need AI available. The parallel pass has no per-test reset,
    so setting it once sticks. Also the one-time sanity-check that
    set-platform-setting actually reaches `/config/features` (replaces the
    old `_verify_ai_search_default`)."""
    _set_ai_search_on(uvicorn_server)
    f = httpx.get(f"{uvicorn_server}{API.CONFIG_FEATURES}", timeout=TIMEOUTS.api_short)
    f.raise_for_status()
    assert f.json().get("ai_search_enabled") is True, (
        f"session sanity failed: {API.CONFIG_FEATURES} still reports "
        f"{f.json()}. Either set-platform-setting не записал в БД, либо "
        "ENABLE_AI_SEARCH env override стоит на False."
    )


@pytest.fixture(autouse=True)
def reset_state(request: pytest.FixtureRequest, uvicorn_server: str) -> None:
    """Per-test global wipe — ONLY for `serial`-marked tests.

    Serial tests run single-worker (`-m serial -p no:xdist`), so the
    classic isolate-by-wiping-everything is safe and kept. Parallel tests
    (`-m "not serial" -n auto`) are isolated by a unique tenant/identity
    instead (owner_user → unique_email); a global wipe there would corrupt
    other workers — so this is a no-op for them. The `serial` marker is
    auto-applied in root conftest (fixture-based)."""
    if request.node.get_closest_marker("serial") is None:
        return
    _post_reset(uvicorn_server)


@pytest.fixture(autouse=True)
def _ai_search_on_serial(request: pytest.FixtureRequest, reset_state: None, uvicorn_server: str) -> None:
    """Serial group keeps per-test reset, which wipes platform_settings →
    `enable_ai_search` back to the False DB default. Re-enable it for
    serial tests; `test_ai_disabled_flow.py`'s file-local autouse flips it
    back to False AFTER this (file-local > conftest autouse ordering).
    No-op for parallel tests (the session fixture already set it, and no
    per-test reset wiped it). Depends on `reset_state` to run after it."""
    if request.node.get_closest_marker("serial") is None:
        return
    _set_ai_search_on(uvicorn_server)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, Any], base_url: str) -> dict[str, Any]:
    return {
        **browser_context_args,
        "base_url": base_url,
        "viewport": {"width": 1440, "height": 900},
        "ignore_https_errors": True,
    }
