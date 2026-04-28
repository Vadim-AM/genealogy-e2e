"""Waitlist (/wait) — F-WAIT-*, BUG-COPY-001 регрессия.

Captures email before signup cap. Public, no auth.
"""

from __future__ import annotations

from playwright.sync_api import Page

from tests.messages import PII
from tests.pages.wait_page import WaitPage


def test_wait_page_renders_form(page: Page):
    """F-WAIT-1: /wait → form visible."""
    wait = WaitPage(page).goto()
    wait.expect_visible_form()


def test_wait_submit_email_success(page: Page):
    """F-WAIT-2: submit → success message."""
    wait = WaitPage(page).goto()
    wait.submit_email("waitlist1@e2e.example.com")
    wait.expect_success()


def test_wait_no_owner_personal_data(page: Page):
    """BUG-COPY-001: /wait must not mention owner family names (PII)."""
    page.goto("/wait")
    page.wait_for_load_state("domcontentloaded")
    body = page.content()
    for needle in PII.OWNER_FAMILY_NAMES:
        assert needle not in body, f"BUG-COPY-001 regression: '{needle}' on /wait"


def test_wait_submit_invalid_email_blocks_html5_validity(page: Page):
    """F-WAIT-3: invalid email — input fails HTML5 validity (form does not submit).

    Input has type=email + required: the browser blocks submit and the
    input becomes :invalid. We assert the validity state directly.
    """
    wait = WaitPage(page).goto()
    wait.email.fill("not-an-email")
    wait.submit_btn.click()
    is_valid = page.evaluate("() => document.getElementById('email').checkValidity()")
    assert is_valid is False, "invalid email must fail HTML5 validity check"
    assert (wait.result.text_content() or "").strip() == "", \
        "no result text should appear when submission was blocked client-side"


def test_wait_duplicate_email_does_not_5xx(page: Page):
    """F-WAIT-4: re-submitting an already-subscribed email — must not 5xx.

    Asserts at the HTTP-response boundary. Backend may legitimately silent-
    dedupe or reply "уже подписаны" — either is acceptable; a 5xx is not.
    """
    wait = WaitPage(page).goto()
    with page.expect_response("**/api/waitlist/subscribe") as r1_info:
        wait.submit_email("dupe@e2e.example.com")
    assert r1_info.value.status < 500, f"first subscribe 5xx: {r1_info.value.status}"
    wait.expect_success()

    wait = WaitPage(page).goto()
    with page.expect_response("**/api/waitlist/subscribe") as r2_info:
        wait.submit_email("dupe@e2e.example.com")
    assert r2_info.value.status < 500, f"duplicate subscribe 5xx: {r2_info.value.status}"
