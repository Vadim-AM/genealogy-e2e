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

from tests.timeouts import TIMEOUTS, set_playwright_default_expect_timeout

from tests.api_paths import API
from tests.constants import TestConfig

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# Shared secret для `/api/_test/*` endpoints (upstream commit 4a3f326). Backend
# при `GENEALOGY_TEST_TOKEN=<value>` гейтит каждый _test/* через
# `X-Test-Token` header через `hmac.compare_digest`. На production env не
# задан — endpoints возвращают 503. Ниже мы автоматически инжектим header
# во все httpx-запросы к `/api/_test/*` через monkey-patch — никакой
# дополнительной правки в тестах не нужно.
_E2E_TEST_TOKEN = os.environ.get("E2E_TEST_TOKEN", TestConfig.TEST_TOKEN_DEFAULT)

_orig_httpx_request = httpx.Client.request


def _origin_for(client_base_url: str, request_url: str) -> str:
    """Derive same-origin header value: scheme://host[:port]."""
    src = client_base_url or request_url
    src = str(src)
    if "://" not in src:
        return src
    scheme, rest = src.split("://", 1)
    host = rest.split("/", 1)[0]
    return f"{scheme}://{host}"


def _patched_request(self, method, url, **kwargs):
    """Inject suite-required headers into every httpx-request:

    1. `X-Test-Token` for `/api/_test/*` (commit 4a3f326).
    2. `Origin` for mutating methods — backend's CSRF middleware
       checks Origin/Referer on every POST/PATCH/PUT/DELETE
       independently of IS_TESTING (commit 1c6cec0).

    Suite tests don't need to know about either header.
    """
    url_str = str(url) if url is not None else ""
    headers = dict(kwargs.get("headers") or {})

    if "/api/_test/" in url_str:
        headers.setdefault("X-Test-Token", _E2E_TEST_TOKEN)

    if str(method).upper() in ("POST", "PATCH", "PUT", "DELETE"):
        client_base = str(getattr(self, "base_url", "") or "")
        headers.setdefault("Origin", _origin_for(client_base, url_str))

    kwargs["headers"] = headers
    return _orig_httpx_request(self, method, url, **kwargs)


httpx.Client.request = _patched_request

# Apply the timeout multiplier to Playwright's `expect()` once per session.
set_playwright_default_expect_timeout()


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
    _wait_for_health(url, timeout=TIMEOUTS.health_gate)
    return url


def _wait_for_health(base_url: str, *, timeout: float) -> None:
    """Block until /api/health responds 200, or raise.

    Single retry loop. We do not swallow exceptions in the inner request —
    httpx's own connect/read timeout is short (`api_short`), which is what
    we want during startup polling: many fast attempts, fail loud overall.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = httpx.get(f"{base_url}/api/health", timeout=TIMEOUTS.api_short)
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
    httpx.post(
        f"{uvicorn_server}{API.TEST_RESET}", timeout=TIMEOUTS.api_request
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
def signup_unverified(uvicorn_server: str) -> Callable[..., str]:
    """Factory: signup без verify-email — для тестов которые покрывают
    pre-verification path (login до verify, change-email-flow, etc.).

    Возвращает email (verification token остаётся в MockSender).
    """

    def _do(
        email: str = "unverified@e2e.example.com",
        password: str = TestConfig.DEFAULT_PASSWORD,
        full_name: str = "Тестовый Пользователь",
    ) -> str:
        with httpx.Client(base_url=uvicorn_server, timeout=TIMEOUTS.api_request) as c:
            c.post(
                API.TEST_RESET_SIGNUP_RATE, timeout=TIMEOUTS.api_short
            ).raise_for_status()
            r = c.post(
                API.SIGNUP,
                json={"email": email, "password": password, "full_name": full_name},
            )
            r.raise_for_status()
        return email

    return _do


@pytest.fixture
def login_existing(uvicorn_server: str) -> Callable[..., dict[str, str]]:
    """Factory: login существующего user'а, возвращает cookies.

    Используется для multi-device сценариев (один user, несколько
    параллельных sessions) — `signup_via_api` уже включает один login.
    """

    def _do(email: str, password: str = TestConfig.DEFAULT_PASSWORD) -> dict[str, str]:
        with httpx.Client(base_url=uvicorn_server, timeout=TIMEOUTS.api_request) as c:
            r = c.post(
                API.LOGIN,
                json={"email": email, "password": password},
            )
            r.raise_for_status()
            return dict(r.cookies)

    return _do


@pytest.fixture
def read_email_token(uvicorn_server: str) -> Callable[[str], str]:
    """Factory: read latest token из MockSender для address.

    Используется в session-invalidation, password-reset, change-email
    flows — где нужно подобрать новый token после reset/forgot/etc.
    """

    def _read(email: str) -> str:
        with httpx.Client(base_url=uvicorn_server, timeout=TIMEOUTS.api_request) as c:
            r = c.get(API.TEST_LAST_EMAIL, params={"to": email})
            r.raise_for_status()
            return _extract_token_from_email(r.json().get("text_body") or "")

    return _read


@pytest.fixture
def create_invite(uvicorn_server: str) -> Callable[..., str]:
    """Factory: owner создаёт invite, возвращает invite token.

    Используется в role-permission тестах для setup viewer/editor.
    """

    def _do(owner: "AuthUser", *, role: str = "viewer", name: str = "Гость") -> str:
        r = httpx.post(
            f"{uvicorn_server}{API.TENANT_INVITES}",
            json={"name": name, "role": role},
            cookies=owner.cookies,
            headers={"X-Tenant-Slug": owner.slug},
            timeout=TIMEOUTS.api_request,
        )
        r.raise_for_status()
        return r.json()["token"]

    return _do


@pytest.fixture
def tenant_client(uvicorn_server: str):
    """Factory: httpx.Client pre-wired для tenant'а (cookies + slug header).

    Используй когда тест делает много API-вызовов от имени одного user'а:
    исключает повторение `cookies=user.cookies`, `headers={"X-Tenant-
    Slug": user.slug}`, `timeout=...` на каждом httpx-вызове.

        def test_x(owner_user, tenant_client, base_url):
            api = tenant_client(owner_user)
            r = api.get("/api/people/demo-self")
            r.raise_for_status()
            api.patch("/api/people/demo-self", json={"summary": "..."})

    Несколько user'ов в одном тесте — несколько вызовов factory.
    Все клиенты автоматически закрываются на teardown.
    """

    clients: list[httpx.Client] = []

    def _make(user: "AuthUser") -> httpx.Client:
        c = httpx.Client(
            base_url=uvicorn_server,
            cookies=user.cookies,
            headers={"X-Tenant-Slug": user.slug},
            timeout=TIMEOUTS.api_request,
        )
        clients.append(c)
        return c

    yield _make
    for c in clients:
        c.close()


@pytest.fixture
def accept_invite(uvicorn_server: str) -> Callable[..., None]:
    """Factory: accept invite by token, using user's session cookies.

    Endpoint: POST /api/account/tenant/invites/{token}/accept.
    """

    def _do(invite_token: str, *, cookies: dict[str, str]) -> None:
        r = httpx.post(
            f"{uvicorn_server}{API.tenant_invite_accept(invite_token)}",
            cookies=cookies,
            timeout=TIMEOUTS.api_request,
        )
        r.raise_for_status()

    return _do


@pytest.fixture
def signup_via_api(uvicorn_server: str) -> Callable[..., AuthUser]:
    """Factory: full signup → verify → login → onboarding-complete via API.

    Linear flow. Any deviation from the canonical path raises AssertionError
    via `raise_for_status()` or explicit assert — never silently degrades.
    """

    def _do(
        email: str = TestConfig.DEFAULT_OWNER_EMAIL,
        password: str = TestConfig.DEFAULT_PASSWORD,
        full_name: str = "Тестовый Пользователь",
        **profile: Any,
    ) -> AuthUser:
        with httpx.Client(base_url=uvicorn_server, timeout=TIMEOUTS.api_request) as c:
            # Reset slowapi signup throttle before each signup. Not optional —
            # if the endpoint is missing we want tests to ERROR, not silently
            # hit the 1/minute cap mid-suite.
            c.post(API.TEST_RESET_SIGNUP_RATE, timeout=TIMEOUTS.api_short).raise_for_status()

            # 1. Signup. `full_name` is required by the form (see /signup) and
            # propagates into the demo-self person's `name` field — search and
            # tree-rendering tests rely on it.
            r = c.post(
                API.SIGNUP,
                json={
                    "email": email,
                    "password": password,
                    "full_name": full_name,
                    **profile,
                },
            )
            r.raise_for_status()
            assert r.json().get("status") == "verification_sent", \
                f"signup did not enter verification flow: {r.json()}"

            # 2. Read verification token from MockSender
            mail = c.get(API.TEST_LAST_EMAIL, params={"to": email})
            mail.raise_for_status()
            token = _extract_token_from_email(mail.json()["text_body"] or "")

            # 3. Verify (token в body — commit d860de8 убрал из query
            # чтобы не утекало в access logs).
            c.post(API.VERIFY_EMAIL, json={"token": token}).raise_for_status()

            # 4. Login → tenant_slug + cookies
            r = c.post(API.LOGIN, json={"email": email, "password": password})
            r.raise_for_status()
            data = r.json()
            slug = data["tenant_slug"]
            cookies = dict(r.cookies)

            # 5. Onboarding-complete (suppresses the auto-tour overlay)
            c.post(
                API.ONBOARDING_COMPLETE,
                cookies=cookies,
                headers={"X-Tenant-Slug": slug},
                timeout=TIMEOUTS.api_short,
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
def grant_ai_consent(tenant_client):
    """Helper: stamp ai_consent_at для user → unblocks /api/enrich/* gate.

    Backend (commit 19fdd41) гейтирует все /api/enrich/* endpoints на
    PlatformUser.ai_consent_at IS NOT NULL. Тесты, которые драйвят
    enrichment flow через API, должны явно поставить consent — иначе
    POST/GET enrich → 403 ai_consent_required.

    Использование:
        def test_x(owner_user, grant_ai_consent, tenant_client):
            grant_ai_consent(owner_user)
            api = tenant_client(owner_user)
            api.post(API.enrich(pid), json={...})
    """

    def _grant(user: AuthUser) -> None:
        tenant_client(user).post(API.ACCOUNT_AI_CONSENT).raise_for_status()

    return _grant


@pytest.fixture
def superadmin_user(signup_via_api) -> AuthUser:
    return signup_via_api(email=TestConfig.SUPERADMIN_EMAIL)


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
        with httpx.Client(base_url=uvicorn_server, timeout=TIMEOUTS.api_request) as c:
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
