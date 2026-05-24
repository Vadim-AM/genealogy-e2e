"""Signup overflow mock helpers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from config.constants import TestConfig
from pages.signup_page import SignupPage

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
    signup = SignupPage(page)
    signup.fill_required(email=email, password=TestConfig.DEFAULT_PASSWORD)
    signup.submit()
