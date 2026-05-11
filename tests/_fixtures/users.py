"""Auth helpers: `AuthUser` dataclass + signup / login / invite factories.

Single source of truth for authenticated test users. Inline signup chains
(post-signup → verify-email → login → onboarding-complete) live here — tests
never re-implement them.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
import pytest

from tests.api_paths import API
from tests.constants import TestConfig, unique_email
from tests.timeouts import TIMEOUTS


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
                json={
                    "email": email,
                    "password": password,
                    "full_name": full_name,
                    # P0.4 (ФЗ-156, май 2026): 3 раздельных consent обязательны.
                    "terms_accepted": True,
                    "privacy_consent": True,
                    "cross_border_consent": True,
                },
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
        # Backend (auth_v2/tenant_invites.py:311) deletes старую session и
        # выпускает новую, привязанную к accepted tenant. Bytes-of-cookies
        # переданные нам from caller — теперь stale (старая session DELETED
        # → 401). Mutate dict in-place: новый Set-Cookie перезаписывает
        # platform_session, остальные cookies caller'а сохраняем.
        for k, v in r.cookies.items():
            cookies[k] = v

    return _do


@pytest.fixture
def signup_via_api(uvicorn_server: str) -> Callable[..., AuthUser]:
    """Factory: full signup → verify → login → onboarding-complete via API.

    Linear flow. Any deviation from the canonical path raises AssertionError
    via `raise_for_status()` or explicit assert — never silently degrades.
    """

    def _do(
        email: str | None = None,
        password: str = TestConfig.DEFAULT_PASSWORD,
        full_name: str = "Тестовый Пользователь",
        **profile: Any,
    ) -> AuthUser:
        # Default email: unique per call. Backend накапливает per-email
        # state (slowapi rate-limit, honeypot counters, sessions) даже
        # после `_test/reset` — фикс waitlist (commit 78f2bc3) добавил
        # per-email rate-limit, который пережил reset на нескольких
        # тестах подряд. Unique email избегает spurious 404 на
        # `/api/_test/last-email` когда `signup` уходит в anti-enum
        # silent success без отправки письма.
        if email is None:
            email = unique_email("owner")
        with httpx.Client(base_url=uvicorn_server, timeout=TIMEOUTS.api_request) as c:
            # Reset slowapi signup throttle before each signup. Not optional —
            # if the endpoint is missing we want tests to ERROR, not silently
            # hit the 1/minute cap mid-suite.
            c.post(API.TEST_RESET_SIGNUP_RATE, timeout=TIMEOUTS.api_short).raise_for_status()

            # 1. Signup. `full_name` is required by the form (see /signup) and
            # propagates into the demo-self person's `name` field — search and
            # tree-rendering tests rely on it.
            # 3 обязательных consent field (Phase 0 P0.4 ФЗ-156, май 2026):
            # terms_accepted, privacy_consent, cross_border_consent — без
            # любого из них Pydantic-валидатор отдаёт 422 «Необходимо
            # принять условия использования». marketing_consent опциональный,
            # default False.
            payload = {
                "email": email,
                "password": password,
                "full_name": full_name,
                "terms_accepted": True,
                "privacy_consent": True,
                "cross_border_consent": True,
                **profile,  # tests могут override консент для negative-проверок
            }
            r = c.post(API.SIGNUP, json=payload)
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
def superadmin_user(signup_via_api) -> AuthUser:
    return signup_via_api(email=TestConfig.SUPERADMIN_EMAIL)


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
def admin_login_via_api(uvicorn_server: str) -> Callable[[], dict[str, str]]:
    """Login as legacy admin (password). Returns admin_token cookie dict."""

    def _login() -> dict[str, str]:
        with httpx.Client(base_url=uvicorn_server, timeout=TIMEOUTS.api_request) as c:
            r = c.post(API.ADMIN_LOGIN, json={"password": TestConfig.ADMIN_PASSWORD})
            r.raise_for_status()
            return dict(r.cookies)

    return _login
