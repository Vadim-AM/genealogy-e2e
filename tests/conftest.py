"""Pytest fixtures for the genealogy-e2e browser suite.

Operates against an externally running backend instance (test-instrumented:
must expose `/api/_test/*` endpoints under `IS_TESTING=1` — see
`genealogy/backend/app/_test_endpoints.py`).

Backend resolution:
  - `E2E_BACKEND_URL` — required; points at the running uvicorn (e.g.
    `http://127.0.0.1:8642` for local dev, `http://backend:8642` in Docker).

Run modes:
  1. Local dev:
       cd genealogy/backend
       GENEALOGY_TESTING=1 uvicorn app.main:app --port 8642 &
       cd genealogy-e2e
       E2E_BACKEND_URL=http://127.0.0.1:8642 pytest tests/

  2. Docker compose:
       docker compose up --abort-on-container-exit e2e

Design rules (28.04 review):
- No branching in fixture body. Each step has one happy path; failure is
  surfaced via assert/raise_for_status — fixture aborts, dependent tests ERROR.
- No `try/except` around backend calls. Test infrastructure must fail loudly.
- All slug/cookie/status fields read with single canonical name (after Wave 2
  contract fix). Until then, single name only — if backend renames a field,
  fixture fails and contract issue surfaces immediately.
"""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

DEFAULT_PASSWORD = "test_password_8plus"


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


# ─────────────────────────────────────────────────────────────────────────
# Server URL & health gate
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def base_url() -> str:
    """Test-instrumented backend URL. Overrides pytest-playwright's `base_url`."""
    url = _resolve_backend_url()
    _wait_for_health(url, timeout=30)
    return url


def _wait_for_health(base_url: str, *, timeout: float) -> None:
    """Block until /api/health responds 200, or raise.

    Single retry loop — `time.sleep` between attempts. We do not swallow
    exceptions: the last exception (if any) is re-raised inside the timeout
    error so failure mode is observable.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = httpx.get(f"{base_url}/api/health", timeout=2)
        if response.status_code == 200:
            return
        time.sleep(0.5)
    raise TimeoutError(f"backend at {base_url} did not respond on /api/health within {timeout}s")


@pytest.fixture(scope="session")
def uvicorn_server(base_url: str) -> str:
    """Alias kept for compatibility with existing tests/POM."""
    return base_url


# ─────────────────────────────────────────────────────────────────────────
# Per-test isolation + AI mock
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_state(uvicorn_server: str) -> None:
    """Wipe DB rows + tenants/ + rate limits + MockSender + site_config between tests."""
    httpx.post(f"{uvicorn_server}/api/_test/reset", timeout=10).raise_for_status()


@pytest.fixture(scope="session", autouse=True)
def install_mock_ai(uvicorn_server: str) -> None:
    """Install AI fixture once per session (survives `/reset` — not touched by it)."""
    fixture = json.loads((FIXTURES_DIR / "ai_responses.json").read_text())
    httpx.post(
        f"{uvicorn_server}/api/_test/install-mock-ai",
        json=fixture,
        timeout=10,
    ).raise_for_status()


# ─────────────────────────────────────────────────────────────────────────
# Playwright context defaults
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict, base_url: str) -> dict:
    return {
        **browser_context_args,
        "base_url": base_url,
        "viewport": {"width": 1440, "height": 900},
        "ignore_https_errors": True,
    }


# ─────────────────────────────────────────────────────────────────────────
# Auth helpers
# ─────────────────────────────────────────────────────────────────────────


@dataclass
class AuthUser:
    email: str
    password: str
    slug: str
    cookies: dict[str, str]


def _extract_token_from_email(body: str) -> str:
    match = re.search(r"token=([A-Za-z0-9_\-]+)", body)
    if not match:
        raise AssertionError(f"no verification token in email body: {body[:200]}")
    return match.group(1)


@pytest.fixture
def signup_via_api(uvicorn_server: str) -> Callable[..., AuthUser]:
    """Factory: full signup → verify → login → onboarding-complete via API.

    Linear flow. Any deviation from the canonical path raises AssertionError
    via `raise_for_status()` or explicit assert — never silently degrades.
    """

    def _do(
        email: str = "owner@e2e.example.com",
        password: str = DEFAULT_PASSWORD,
        **profile: Any,
    ) -> AuthUser:
        with httpx.Client(base_url=uvicorn_server, timeout=10) as c:
            # Reset slowapi signup throttle before each signup. Not optional —
            # if the endpoint is missing we want tests to ERROR, not silently
            # hit the 1/minute cap mid-suite.
            c.post("/api/_test/reset-signup-rate", timeout=3).raise_for_status()

            # 1. Signup
            r = c.post(
                "/api/account/signup",
                json={"email": email, "password": password, **profile},
            )
            r.raise_for_status()
            assert r.json().get("status") == "verification_sent", \
                f"signup did not enter verification flow: {r.json()}"

            # 2. Read verification token from MockSender
            mail = c.get("/api/_test/last-email", params={"to": email})
            mail.raise_for_status()
            token = _extract_token_from_email(mail.json()["text_body"] or "")

            # 3. Verify
            c.post("/api/account/verify-email", params={"token": token}).raise_for_status()

            # 4. Login → tenant_slug + cookies
            r = c.post(
                "/api/account/login",
                json={"email": email, "password": password},
            )
            r.raise_for_status()
            data = r.json()
            slug = data["tenant_slug"]
            cookies = dict(r.cookies)

            # 5. Onboarding-complete (suppresses the auto-tour overlay)
            c.post(
                "/api/account/onboarding-complete",
                cookies=cookies,
                headers={"X-Tenant-Slug": slug},
                timeout=5,
            ).raise_for_status()

            return AuthUser(
                email=email,
                password=password,
                slug=slug,
                cookies=cookies,
            )

    return _do


@pytest.fixture
def owner_user(signup_via_api) -> AuthUser:
    return signup_via_api()


@pytest.fixture
def superadmin_user(signup_via_api) -> AuthUser:
    return signup_via_api(email="super@e2e.example.com")


@pytest.fixture
def auth_context_factory(browser, uvicorn_server: str):
    """Factory to build a Playwright BrowserContext with cookies + tenant header.

    `localStorage` flags pre-seeded to silence the optional editor tour
    (init.js:544 → maybeAutoStart). The full ONBOARDING tour is suppressed
    via `onboarding-complete` in `signup_via_api` — there is no defensive
    DOM removal anymore. If the tour appears, the test fails loud — that
    means `onboarding-complete` is broken upstream.
    """

    created_contexts = []

    def _make(user: AuthUser, *, with_tenant_header: bool = True):
        extra_headers = {"X-Tenant-Slug": user.slug} if with_tenant_header else {}
        ctx = browser.new_context(
            base_url=uvicorn_server,
            extra_http_headers=extra_headers,
            viewport={"width": 1440, "height": 900},
        )
        for name, value in user.cookies.items():
            ctx.add_cookies(
                [{"name": name, "value": value, "url": uvicorn_server}]
            )
        ctx.add_init_script(
            "try { localStorage.setItem('v1', '1'); "
            "localStorage.setItem('genealogy_tour_v1', '1'); } catch (e) {}"
        )
        created_contexts.append(ctx)
        return ctx

    yield _make
    for ctx in created_contexts:
        ctx.close()


@pytest.fixture
def owner_page(auth_context_factory, owner_user: AuthUser):
    """Authenticated browser page in owner_user's tenant."""
    ctx = auth_context_factory(owner_user)
    page = ctx.new_page()
    yield page
    page.close()


@pytest.fixture
def admin_login_via_api(uvicorn_server: str) -> Callable[[], dict[str, str]]:
    """Login as legacy admin (password). Returns admin_token cookie dict."""

    def _login() -> dict[str, str]:
        with httpx.Client(base_url=uvicorn_server, timeout=10) as c:
            r = c.post("/api/admin/login", json={"password": "test_admin_password"})
            r.raise_for_status()
            return dict(r.cookies)

    return _login


# ─────────────────────────────────────────────────────────────────────────
# Soft-assert helper (for genuine "report multiple independent facts" cases)
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def soft_check():
    """Yields Playwright `expect` for `expect.soft(...)` usage.

    Use ONLY for smoke blocks asserting >=3 independent facts at once
    (e.g. "all 5 nav tabs visible"). For functional flow — hard `expect`.
    """
    from playwright.sync_api import expect

    yield expect
