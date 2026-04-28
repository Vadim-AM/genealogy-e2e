"""Waitlist (/wait) — F-WAIT, BUG-COPY-001 регрессия.

Captures email before signup cap. Public, no auth.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

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
    """BUG-COPY-001: /wait must not mention Данилюк/Макаров (owner PII).

    Per docs/test-plan.md: «упоминание семьи Данилюк/Макаров» нарушает
    privacy posture. Bug marked closed (commit pending) on 2026-04-27 —
    regression guard ensures it stays fixed.
    """
    page.goto("/wait")
    page.wait_for_load_state("domcontentloaded")
    body = page.content()
    for needle in ("Данилюк", "Макаров"):
        assert needle not in body, f"BUG-COPY-001 regression: '{needle}' on /wait"


def test_wait_submit_invalid_email_rejected(page: Page):
    """F-WAIT-3: invalid email is rejected (HTML5 validation or backend 422)."""
    wait = WaitPage(page).goto()
    wait.email.fill("not-an-email")
    wait.submit_btn.click()
    # Either HTML5 validity blocks submit (form stays), or backend returns error
    # in #result. Either way #result must NOT show success.
    page.wait_for_timeout(500)
    result_text = wait.result.text_content() or ""
    assert "успех" not in result_text.lower() and "записал" not in result_text.lower()


def test_wait_duplicate_email_handled_gracefully(page: Page):
    """F-WAIT-4: duplicate email — graceful state, не утечка enumeration."""
    wait = WaitPage(page).goto()
    wait.submit_email("dupe@e2e.example.com")
    wait.expect_success()

    # After successful submit the form may hide; re-navigate for a clean retry.
    wait = WaitPage(page).goto()
    wait.submit_email("dupe@e2e.example.com")
    page.wait_for_timeout(800)
    # Either generic success (silent dedupe) or polite "already signed up" —
    # both acceptable. What's NOT acceptable: a 500 or technical error in UI.
    result_text = (wait.result.text_content() or "").lower()
    technical_failures = ("internal server error", "traceback", "unexpected", "500")
    for marker in technical_failures:
        assert marker not in result_text, f"duplicate-email surfaces technical failure: {result_text}"
