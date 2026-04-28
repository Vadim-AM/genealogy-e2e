"""Waitlist (/wait) — F-WAIT-*, BUG-COPY-001 регрессия.

Captures email before signup cap. Public, no auth.

Note on isolation: `WaitlistSubscriber` lives in legacy `genealogy.db`
(via `from ..database import get_session`), not platform.db, so the
`/api/_test/reset` endpoint does not wipe it (only platform tables +
per-tenant DBs). Tests that submit waitlist emails MUST use unique
addresses per-run — otherwise stale rows from earlier runs poison
the contract assertions (e.g. first submit comes back as
`already_subscribed`). When `_test/reset` learns to wipe waitlist
rows, switch back to fixed addresses.
"""

from __future__ import annotations

import uuid

from playwright.sync_api import Page

from tests.messages import PII
from tests.pages.wait_page import WaitPage


def _unique_email(label: str) -> str:
    """`<label>+<8-hex>@e2e.example.com` — never collides between runs."""
    return f"{label}+{uuid.uuid4().hex[:8]}@e2e.example.com"


def test_wait_page_renders_form(page: Page):
    """F-WAIT-1: /wait → form visible."""
    wait = WaitPage(page).goto()
    wait.expect_visible_form()


def test_wait_submit_email_success(page: Page):
    """F-WAIT-2: submit → success message."""
    wait = WaitPage(page).goto()
    wait.submit_email(_unique_email("waitlist1"))
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


def test_wait_duplicate_email_idempotent_status_field(page: Page):
    """F-WAIT-4: re-submitting an already-subscribed email — idempotent contract.

    Backend `/api/waitlist/subscribe` returns 200 + JSON `{"status": ...}`:
    - first submission for an email → `status="ok"`
    - any subsequent submission for the same email → `status="already_subscribed"`

    Pin both the HTTP status and the `status` discriminator. Earlier this
    test only checked `<500` which let any 4xx «regression» pass silently.
    """
    email = _unique_email("dupe")
    wait = WaitPage(page).goto()
    with page.expect_response("**/api/waitlist/subscribe") as r1_info:
        wait.submit_email(email)
    r1 = r1_info.value
    assert r1.status == 200, f"first subscribe must be 200: {r1.status} {r1.text()[:200]}"
    body1 = r1.json()
    assert body1.get("status") == "ok", (
        f"first subscribe must return status=ok: {body1}"
    )
    wait.expect_success()

    wait = WaitPage(page).goto()
    with page.expect_response("**/api/waitlist/subscribe") as r2_info:
        wait.submit_email(email)
    r2 = r2_info.value
    assert r2.status == 200, f"duplicate subscribe must be 200: {r2.status} {r2.text()[:200]}"
    body2 = r2.json()
    assert body2.get("status") == "already_subscribed", (
        f"duplicate subscribe must return status=already_subscribed: {body2}"
    )
