"""Signup overflow mock helpers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from config.constants import TestConfig

if TYPE_CHECKING:
    from playwright.sync_api import Page, Route


def mock_signup_overflow(page: Page, *, email: str, subscribed: bool = True) -> None:
    """Перехватить POST /api/account/signup и вернуть waitlist_required.

    Frontend (signup.html:515) смотрит на `j.status === 'waitlist_required'`
    -> openWaitlistModal({email, subscribed: !!j.waitlist_subscribed}).
    """

    def handler(route: Route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "status": "waitlist_required",
                "email": email,
                "waitlist_subscribed": subscribed,
            }),
        )

    page.route("**/api/account/signup", handler)


def fill_and_submit(page: Page, email: str) -> None:
    """Fill signup form fields and click submit."""
    page.locator("#email").fill(email)
    page.locator("#password").fill(TestConfig.DEFAULT_PASSWORD)
    # Wave-9: privacy/cross-border объединены с terms_accepted; в форме
    # остался только `#agreeTerms`.
    page.locator("#agreeTerms").check()
    page.locator("#signupBtn").click()
