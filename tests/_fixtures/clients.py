"""Pre-wired clients: httpx for API, Playwright contexts for browser tests.

`tenant_client(user)` eliminates copy-pasted cookies+slug+timeout boilerplate
on every API call. `auth_context_factory(user)` builds Playwright contexts
with cookies + tenant header + tour-flag seed.
"""

from __future__ import annotations

import httpx
import pytest

from tests._fixtures.users import AuthUser
from tests.timeouts import TIMEOUTS


@pytest.fixture
def tenant_client(uvicorn_server: str):
    """Factory: httpx.Client pre-wired для tenant'а (cookies + slug header).

    Используй когда тест делает много API-вызовов от имени одного user'а:
    исключает повторение `cookies=user.cookies`, `headers={"X-Tenant-
    Slug": user.slug}`, `timeout=...` на каждом httpx-вызове.

        def test_x(owner_user, tenant_client, base_url):
            api = tenant_client(owner_user)
            r = api.get(API.person(TestData.DEMO_PERSON_ID))
            r.raise_for_status()
            api.patch(API.person(pid), json={"summary": "..."})

    Несколько user'ов в одном тесте — несколько вызовов factory.
    Все клиенты автоматически закрываются на teardown.
    """

    clients: list[httpx.Client] = []

    def _make(user: AuthUser) -> httpx.Client:
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
        # Seed localStorage:
        # - tour flags: silence editor tour + onboarding;
        # - cookie consent: banner overlay intercepts pointer events
        #   на первый visit (cookie-consent.js mount async) и валит клики
        #   в неконтролируемом порядке (race с auto-wait). Pre-seed
        #   `genealogy_cookie_consent='necessary'` — banner не рендерится
        #   (getConsentLevel() returns non-null → init exit early).
        ctx.add_init_script(
            "try { localStorage.setItem('v1', '1'); "
            "localStorage.setItem('genealogy_tour_v1', '1'); "
            "localStorage.setItem('genealogy_cookie_consent', 'necessary'); "
            "localStorage.setItem('genealogy_cookie_consent_ts', String(Date.now())); "
            "} catch (e) {}"
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
