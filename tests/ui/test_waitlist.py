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

from http import HTTPStatus
from typing import TYPE_CHECKING

import allure

from config.constants import unique_email
from framework.step import step
from pages.wait_page import WaitPage
from src.texts import PII

if TYPE_CHECKING:
    from playwright.sync_api import Page

    from fixtures.page_factory import PageFactory


@allure.title("Вейтлист: форма подписки отображается на /wait")
def test_wait_page_renders_form(anon_pages: PageFactory) -> None:
    """F-WAIT-1: /wait → form visible."""
    wait = anon_pages.navigate_to(WaitPage)
    wait.expect_visible_form()


@allure.title("Вейтлист: отправка email успешно добавляет в очередь")
def test_wait_submit_email_success(page: Page, anon_pages: PageFactory) -> None:
    """F-WAIT-2: submit → success message.

    Hardened (Rule 1): the previous `expect_success()`-only assertion was a
    false-green — on a 500 the JS still writes a non-empty error into
    `#result`, so the test passed even when the endpoint was broken. Pin
    the HTTP response so a real waitlist break is actually caught.
    """
    with step("действие: отправить email через waitlist"):
        wait = anon_pages.navigate_to(WaitPage)
        with page.expect_response("**/api/waitlist/subscribe") as r_info:
            wait.submit_email(unique_email("waitlist1"))

    with step("проверка: 200 и success-сообщение"):
        assert r_info.value.status == HTTPStatus.OK, (
            f"subscribe must be 200: {r_info.value.status} {r_info.value.text()[:200]}"
        )
        wait.expect_success()


@allure.title("Вейтлист: на /wait нет персональных данных владельца")
def test_wait_no_owner_personal_data(page: Page, anon_pages: PageFactory) -> None:
    """BUG-COPY-001: /wait must not mention owner family names (PII)."""
    with step("действие: загрузить /wait"):
        _ = anon_pages.navigate_to(WaitPage)
        body = page.content()

    with step("проверка: нет PII владельца"):
        for needle in PII.OWNER_FAMILY_NAMES:
            assert needle not in body, f"BUG-COPY-001 regression: '{needle}' on /wait"


@allure.title("Вейтлист: невалидный email блокируется HTML5-проверкой")
def test_wait_submit_invalid_email_blocks_html5_validity(page: Page, anon_pages: PageFactory) -> None:
    """F-WAIT-3: invalid email — input fails HTML5 validity (form does not submit).

    Input has type=email + required: the browser blocks submit and the
    input becomes :invalid. We assert the validity state directly.
    """
    with step("действие: заполнить невалидный email и отправить"):
        wait = anon_pages.navigate_to(WaitPage)
        wait.email.fill("not-an-email")
        wait.submit_btn.click()

    with step("проверка: HTML5 validity false и result пуст"):
        is_valid = page.evaluate("() => document.getElementById('email').checkValidity()")
        assert is_valid is False, "invalid email must fail HTML5 validity check"
        assert (wait.result.text_content() or "").strip() == "", \
            "no result text should appear when submission was blocked client-side"


@allure.title("Вейтлист: повторная подписка возвращает already_subscribed")
def test_wait_duplicate_email_idempotent_status_field(page: Page, anon_pages: PageFactory) -> None:
    """F-WAIT-4: re-submitting an already-subscribed email — idempotent contract.

    Backend `/api/waitlist/subscribe` returns 200 + JSON `{"status": ...}`:
    - first submission for an email → `status="ok"`
    - any subsequent submission for the same email → `status="already_subscribed"`

    Pin both the HTTP status and the `status` discriminator. Earlier this
    test only checked `<500` which let any 4xx «regression» pass silently.
    """
    with step("действие: первая подписка"):
        email = unique_email("dupe")
        wait = anon_pages.navigate_to(WaitPage)
        with page.expect_response("**/api/waitlist/subscribe") as r1_info:
            wait.submit_email(email)

    with step("проверка: первый submit -> status=ok"):
        r1 = r1_info.value
        assert r1.status == HTTPStatus.OK, f"first subscribe must be 200: {r1.status} {r1.text()[:200]}"
        body1 = r1.json()
        assert body1.get("status") == "ok", (
            f"first subscribe must return status=ok: {body1}"
        )
        wait.expect_success()

    with step("действие: повторная подписка тем же email"):
        wait = anon_pages.navigate_to(WaitPage)
        with page.expect_response("**/api/waitlist/subscribe") as r2_info:
            wait.submit_email(email)

    with step("проверка: дубликат -> status=already_subscribed"):
        r2 = r2_info.value
        assert r2.status == HTTPStatus.OK, f"duplicate subscribe must be 200: {r2.status} {r2.text()[:200]}"
        body2 = r2.json()
        assert body2.get("status") == "already_subscribed", (
            f"duplicate subscribe must return status=already_subscribed: {body2}"
        )
