"""Pytest fixtures for the genealogy-e2e browser suite.

Operates against an externally running backend instance (test-instrumented:
must expose `/api/_test/*` endpoints — see `genealogy/backend/app/_test_endpoints.py`,
gated by `IS_TESTING=1`).

Backend resolution:
  - `E2E_BACKEND_URL` — required; points at the running uvicorn (e.g.
    `http://127.0.0.1:8642` for local dev, `http://backend:8642` in Docker).

Two run modes:
  1. Local dev:
       cd genealogy/backend
       GENEALOGY_TESTING=1 uvicorn app.main:app --port 8642 &
       cd genealogy-e2e
       E2E_BACKEND_URL=http://127.0.0.1:8642 pytest tests/

  2. Docker compose:
       docker compose up --abort-on-container-exit e2e
       (compose file points e2e to the `backend` service)
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
    """The base URL for the test-instrumented backend. Overrides pytest-playwright's
    `base_url` fixture so playwright's `page.goto('/path')` hits the live app."""
    url = _resolve_backend_url()
    _wait_for_health(url, timeout=30)
    return url


def _wait_for_health(base_url: str, *, timeout: float) -> None:
    deadline = time.time() + timeout
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            r = httpx.get(f"{base_url}/api/health", timeout=2)
            if r.status_code == 200:
                return
        except Exception as exc:
            last_err = exc
        time.sleep(0.5)
    raise TimeoutError(
        f"backend at {base_url} did not respond on /api/health within {timeout}s; last_err={last_err}"
    )


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
    """Install AI fixture once per session; survives `/reset` (reset doesn't touch ai_client)."""
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
    user_id: int | None = None


def _extract_token_from_email(body: str) -> str:
    match = re.search(r"token=([A-Za-z0-9_\-]+)", body)
    if not match:
        raise AssertionError(f"no verification token in email body: {body[:200]}")
    return match.group(1)


@pytest.fixture
def signup_via_api(uvicorn_server: str) -> Callable[..., AuthUser]:
    """Factory: full signup → verify → login → onboarding-complete via API."""

    def _do(
        email: str = "owner@e2e.example.com",
        password: str = DEFAULT_PASSWORD,
        complete_onboarding: bool = True,
        **profile: Any,
    ) -> AuthUser:
        with httpx.Client(base_url=uvicorn_server, timeout=10) as c:
            try:
                c.post("/api/_test/reset-signup-rate", timeout=3)
            except Exception:
                pass

            body = {"email": email, "password": password, **profile}
            r = c.post("/api/account/signup", json=body)
            if r.status_code != 200:
                raise AssertionError(
                    f"signup failed: status={r.status_code} body={r.text[:500]}"
                )
            if r.json().get("status") == "waitlist_required":
                raise AssertionError(f"Signup hit waitlist for {email}; bump FREE_SIGNUP_LIMIT")

            mail = c.get("/api/_test/last-email", params={"to": email})
            mail.raise_for_status()
            token = _extract_token_from_email(mail.json()["text_body"] or "")

            r = c.post("/api/account/verify-email", params={"token": token})
            r.raise_for_status()

            r = c.post(
                "/api/account/login",
                json={"email": email, "password": password},
            )
            r.raise_for_status()
            data = r.json() if isinstance(r.json(), dict) else {}
            cookies = dict(r.cookies)
            slug = (
                data.get("tenant_slug")
                or (data.get("tenant") or {}).get("slug")
            )
            if not slug:
                me = c.get("/api/account/me", cookies=cookies)
                me.raise_for_status()
                me_data = me.json()
                slug = (
                    me_data.get("tenant_slug")
                    or (me_data.get("tenant") or {}).get("slug")
                )

            if complete_onboarding and slug:
                ob_resp = c.post(
                    "/api/account/onboarding-complete",
                    cookies=cookies,
                    headers={"X-Tenant-Slug": slug},
                    timeout=5,
                )
                if ob_resp.status_code not in (200, 204):
                    raise AssertionError(
                        f"onboarding-complete failed: {ob_resp.status_code} "
                        f"body={ob_resp.text[:200]}"
                    )

            return AuthUser(
                email=email,
                password=password,
                slug=slug,
                cookies=cookies,
                user_id=data.get("user_id") if isinstance(data, dict) else None,
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
    """Factory to build a Playwright BrowserContext with cookies + tenant header
    + tour-disabling localStorage flag."""

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
        try:
            ctx.close()
        except Exception:
            pass


@pytest.fixture
def owner_page(auth_context_factory, owner_user: AuthUser):
    """Authenticated browser page in owner_user's tenant. Defensively dismisses
    any leftover tour overlay on each navigation."""
    ctx = auth_context_factory(owner_user)
    page = ctx.new_page()

    def _dismiss_tour():
        try:
            page.evaluate(
                "document.querySelectorAll('#tourBackdrop, #tourTooltip').forEach(e => e.remove())"
            )
        except Exception:
            pass

    page.on("framenavigated", lambda _frame: _dismiss_tour())
    page.on("load", lambda: _dismiss_tour())

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
# Soft-assert helper
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def soft_check():
    """Yields Playwright `expect` for `expect.soft(...)` usage."""
    from playwright.sync_api import expect

    yield expect
