"""Platform domain fixtures — WebAuthn virtual authenticator helpers."""

from __future__ import annotations


def localhost_url(base_url: str) -> str:
    """Replace 127.0.0.1 with localhost for WebAuthn RP-id compatibility."""
    return base_url.replace("127.0.0.1", "localhost")


def make_localhost_context(browser, superadmin_user, base_url: str):
    """BrowserContext pointing at http://localhost with superadmin cookies."""
    url = localhost_url(base_url)
    ctx = browser.new_context(
        base_url=url,
        viewport={"width": 1440, "height": 900},
    )
    for name, value in superadmin_user.cookies.items():
        ctx.add_cookies(
            [{"name": name, "value": value, "url": url}]
        )
    return ctx


def add_virtual_authenticator(page) -> str:
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
