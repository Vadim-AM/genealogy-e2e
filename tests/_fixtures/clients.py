"""Pre-wired clients: httpx for API, Playwright contexts for browser tests.

`tenant_client(user)` eliminates copy-pasted cookies+slug+timeout boilerplate
on every API call. `auth_context_factory(user)` builds Playwright contexts
with cookies + tenant header + tour-flag seed + Playwright tracing (saved on
failure as Allure attachment).
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

import allure
import httpx
import pytest

from tests.timeouts import TIMEOUTS

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from pathlib import Path

    from playwright.sync_api import Browser, BrowserContext, Page

    from tests._fixtures.users import AuthUser


@pytest.fixture
def tenant_client(uvicorn_server: str) -> Generator[Callable[[AuthUser], httpx.Client]]:
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
def auth_context_factory(
    request: pytest.FixtureRequest, browser: Browser, uvicorn_server: str, tmp_path: Path,
) -> Generator[Callable[..., BrowserContext]]:
    """Factory to build a Playwright BrowserContext with cookies + tenant header.

    `localStorage` flags pre-seeded to silence the optional editor tour
    (init.js:544 → maybeAutoStart). The full ONBOARDING tour is suppressed
    via `onboarding-complete` in `signup_via_api` — there is no defensive
    DOM removal anymore. If the tour appears, the test fails loud — that
    means `onboarding-complete` is broken upstream.

    Playwright tracing is started on every context. On teardown the trace
    is saved and attached to Allure on failure, or silently discarded on
    success.
    """

    created_contexts = []

    def _make(user: AuthUser, *, with_tenant_header: bool = True) -> BrowserContext:
        from tests.settings import settings as _settings

        extra_headers = {"X-Tenant-Slug": user.slug} if with_tenant_header else {}
        video_opts: dict[str, Any] = {}
        if _settings.record_video:
            video_dir = tmp_path / "videos"
            video_dir.mkdir(exist_ok=True)
            video_opts["record_video_dir"] = str(video_dir)
            video_opts["record_video_size"] = {"width": 1280, "height": 720}
        ctx = browser.new_context(
            base_url=uvicorn_server,
            extra_http_headers=extra_headers,
            viewport={"width": 1440, "height": 900},
            **video_opts,
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
        ctx.tracing.start(screenshots=True, snapshots=True, sources=True)
        created_contexts.append(ctx)
        return ctx

    yield _make

    from tests.settings import settings as _settings

    failed = getattr(getattr(request.node, "rep_call", None), "failed", False)
    for i, ctx in enumerate(created_contexts):
        if failed:
            trace_path = tmp_path / f"trace-{i}.zip"
            try:
                ctx.tracing.stop(path=str(trace_path))
            except Exception:
                trace_path = None  # type: ignore[assignment]
            if trace_path and trace_path.exists():
                allure.attach.file(
                    str(trace_path),
                    name=f"playwright-trace-{i}.zip",
                    extension="zip",
                )
            if _settings.record_video:
                for j, page in enumerate(ctx.pages):
                    with contextlib.suppress(Exception):
                        video = page.video
                        if video:
                            video_path = video.path()
                            allure.attach.file(
                                str(video_path),
                                name=f"video-ctx{i}-page{j}.webm",
                                extension="webm",
                            )
        else:
            with contextlib.suppress(Exception):
                ctx.tracing.stop()
        ctx.close()


@pytest.fixture
def owner_page(
    request: pytest.FixtureRequest, auth_context_factory: Callable[..., BrowserContext], owner_user: AuthUser,
) -> Generator[Page]:
    """Authenticated browser page in owner_user's tenant."""
    ctx = auth_context_factory(owner_user)
    page = ctx.new_page()
    request.node._pw_page = page
    yield page
    page.close()
