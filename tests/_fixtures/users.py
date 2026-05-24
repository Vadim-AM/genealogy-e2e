"""Auth helpers: `AuthUser` dataclass + signup / login / invite factories.

Single source of truth for authenticated test users. Inline signup chains
(post-signup → verify-email → login → onboarding-complete) live here — tests
never re-implement them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx
import pytest

from tests._core import api_paths as routes
from tests._core.constants import EMAIL_TOKEN_RE, TestConfig, unique_email
from tests._core.step import step
from tests._core.timeouts import TIMEOUTS

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class AuthUser:
    email: str
    password: str
    slug: str
    cookies: dict[str, str]


def _extract_token_from_email(body: str) -> str:
    match = EMAIL_TOKEN_RE.search(body)
    if not match:
        raise AssertionError(
            f"no verification token in email body (pattern: {EMAIL_TOKEN_RE.pattern!r}): "
            f"{body[:200]}"
        )
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
                routes.TEST_RESET_SIGNUP_RATE, timeout=TIMEOUTS.api_short
            ).raise_for_status()
            r = c.post(
                routes.SIGNUP,
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
                routes.LOGIN,
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
            r = c.get(routes.TEST_LAST_EMAIL, params={"to": email})
            r.raise_for_status()
            return _extract_token_from_email(r.json().get("text_body") or "")

    return _read


@pytest.fixture
def create_invite(uvicorn_server: str) -> Callable[..., str]:
    """Factory: owner создаёт invite, возвращает invite token.

    Используется в role-permission тестах для setup viewer/editor.
    """

    def _do(owner: AuthUser, *, role: str = "viewer", name: str = "Гость") -> str:
        r = httpx.post(
            f"{uvicorn_server}{routes.TENANT_INVITES}",
            json={"name": name, "role": role},
            cookies=owner.cookies,
            headers={"X-Tenant-Slug": owner.slug},
            timeout=TIMEOUTS.api_request,
        )
        r.raise_for_status()
        return r.json()["token"]  # type: ignore[no-any-return]

    return _do


@pytest.fixture
def accept_invite(uvicorn_server: str) -> Callable[..., None]:
    """Factory: accept invite by token, using user's session cookies.

    Endpoint: POST /api/account/tenant/invites/{token}/accept.
    """

    def _do(invite_token: str, *, cookies: dict[str, str]) -> dict[str, str]:
        r = httpx.post(
            f"{uvicorn_server}{routes.tenant_invite_accept(invite_token)}",
            cookies=cookies,
            timeout=TIMEOUTS.api_request,
        )
        r.raise_for_status()
        # Backend deletes the old session and issues a new one bound to
        # the accepted tenant. The caller's dict is mutated in-place so
        # subsequent API calls use the fresh session automatically.
        cookies.update(r.cookies)
        return cookies

    return _do  # type: ignore[return-value]


@pytest.fixture
def signup_via_api(uvicorn_server: str) -> Callable[..., AuthUser]:
    """Factory: full signup → verify → login → onboarding-complete via routes.

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
            with step(f"reset signup throttle for {email}"):
                c.post(routes.TEST_RESET_SIGNUP_RATE, timeout=TIMEOUTS.api_short).raise_for_status()

            with step(f"signup {email}"):
                payload = {
                    "email": email,
                    "password": password,
                    "full_name": full_name,
                    "terms_accepted": True,
                    "privacy_consent": True,
                    "cross_border_consent": True,
                    **profile,
                }
                r = c.post(routes.SIGNUP, json=payload)
                r.raise_for_status()
                assert r.json().get("status") == "verification_sent", \
                    f"signup did not enter verification flow: {r.json()}"

            with step(f"read verification token for {email}"):
                mail = c.get(routes.TEST_LAST_EMAIL, params={"to": email})
                mail.raise_for_status()
                token = _extract_token_from_email(mail.json()["text_body"] or "")

            with step(f"verify email {email}"):
                c.post(routes.VERIFY_EMAIL, json={"token": token}).raise_for_status()

            with step(f"login {email}"):
                r = c.post(routes.LOGIN, json={"email": email, "password": password})
                r.raise_for_status()
                data = r.json()
                slug = data["tenant_slug"]
                cookies = dict(r.cookies)

            with step(f"onboarding-complete {slug}"):
                c.post(
                    routes.ONBOARDING_COMPLETE,
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
def owner_user(signup_via_api: Callable[..., AuthUser]) -> AuthUser:
    """Create and return a fully verified owner user."""
    return signup_via_api()  # type: ignore[no-any-return]


@pytest.fixture
def superadmin_user(signup_via_api: Callable[..., AuthUser]) -> AuthUser:
    """Create and return a fully verified superadmin user."""
    return signup_via_api(email=TestConfig.SUPERADMIN_EMAIL)  # type: ignore[no-any-return]


@pytest.fixture
def grant_ai_consent(tenant_client: Callable[[AuthUser], httpx.Client]) -> Callable[[AuthUser], None]:
    """Helper: stamp ai_consent_at для user → unblocks /api/enrich/* gate.

    Backend (commit 19fdd41) гейтирует все /api/enrich/* endpoints на
    PlatformUser.ai_consent_at IS NOT NULL. Тесты, которые драйвят
    enrichment flow через API, должны явно поставить consent — иначе
    POST/GET enrich → 403 ai_consent_required.

    Использование:
        def test_x(owner_user, grant_ai_consent, tenant_client):
            grant_ai_consent(owner_user)
            api = tenant_client(owner_user)
            api.post(routes.enrich(pid), json={...})
    """

    def _grant(user: AuthUser) -> None:
        tenant_client(user).post(routes.ACCOUNT_AI_CONSENT).raise_for_status()

    return _grant


def setup_and_verify_mfa(api: httpx.Client) -> str:
    """Setup + verify TOTP for the given client. Returns plaintext secret."""
    import pyotp

    setup = api.post(routes.MFA_SETUP).json()
    code = pyotp.TOTP(setup["secret"]).now()
    api.post(routes.MFA_VERIFY, json={"code": code}).raise_for_status()
    return setup["secret"]  # type: ignore[no-any-return]


@pytest.fixture
def admin_login_via_api(uvicorn_server: str) -> Callable[[], dict[str, str]]:
    """Login as legacy admin (password). Returns admin_token cookie dict."""

    def _login() -> dict[str, str]:
        with httpx.Client(base_url=uvicorn_server, timeout=TIMEOUTS.api_request) as c:
            r = c.post(routes.ADMIN_LOGIN, json={"password": TestConfig.ADMIN_PASSWORD})
            r.raise_for_status()
            return dict(r.cookies)

    return _login
