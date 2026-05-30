"""Platform domain fixtures — WebAuthn virtual authenticator helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from pages.feature_flags_page import FeatureFlagsPage

if TYPE_CHECKING:
    from collections.abc import Callable

    from playwright.sync_api import Browser, BrowserContext, Page

    from fixtures.users import AuthUser


@pytest.fixture
def feature_flags(
    auth_context_factory: Callable[..., BrowserContext], superadmin_user: AuthUser
) -> FeatureFlagsPage:
    """Open /platform/dashboard as superadmin and return a FeatureFlagsPage POM."""
    ctx = auth_context_factory(superadmin_user, with_tenant_header=False)
    ff = FeatureFlagsPage(ctx.new_page())
    ff.goto()
    return ff


def localhost_url(base_url: str) -> str:
    """Replace 127.0.0.1 with localhost for WebAuthn RP-id compatibility."""
    return base_url.replace("127.0.0.1", "localhost")


def make_localhost_context(browser: Browser, superadmin_user: AuthUser, base_url: str) -> BrowserContext:
    """BrowserContext pointing at http://localhost with superadmin cookies."""
    url = localhost_url(base_url)
    ctx = browser.new_context(
        base_url=url,
        viewport={"width": 1440, "height": 900},
    )
    for name, value in superadmin_user.cookies.items():
        ctx.add_cookies([{"name": name, "value": value, "url": url}])
    return ctx


def add_virtual_authenticator(page: Page) -> str:
    """Register a virtual TouchID authenticator via CDP. Returns authenticatorId."""
    cdp = page.context.new_cdp_session(page)
    cdp.send("WebAuthn.enable", {"enableUI": False})
    result = cdp.send(
        "WebAuthn.addVirtualAuthenticator",
        {
            "options": {
                "protocol": "ctap2",
                "transport": "internal",
                "hasResidentKey": True,
                "hasUserVerification": True,
                "isUserVerified": True,
                "automaticPresenceSimulation": True,
            }
        },
    )
    return result["authenticatorId"]  # type: ignore[no-any-return]
