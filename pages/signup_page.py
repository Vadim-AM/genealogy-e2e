"""POM for /signup."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Self

from playwright.sync_api import Locator, Page, expect

if TYPE_CHECKING:
    from playwright.sync_api import Expect

from framework.step import step
from src.texts import Buttons, Labels, t

from .base import BasePage


class SignupPage(BasePage):
    URL = "/signup"

    def __init__(self, page: Page):
        super().__init__(page)

    # ── Locator properties ──────────────────────────────────────────

    @property
    def email(self) -> Locator:
        """Поле email."""
        return self.page.get_by_label(t(Labels.EMAIL))

    @property
    def password(self) -> Locator:
        """no semantic: get_by_label("Пароль") matches toggle button too"""
        return self.page.locator("#password")

    @property
    def honeypot(self) -> Locator:
        """no semantic: hidden honeypot field"""
        return self.page.locator("#website")

    @property
    def agree_terms(self) -> Locator:
        """no semantic: custom checkbox wrapper

        Stage-0 (RU-бета, Wave-9): отдельные #agreePrivacy/#agreeCrossBorder
        удалены из формы — privacy объединён с terms_accepted (см. backend
        auth_v2/router.py:208-422). Остался один #agreeTerms обязательный.
        """
        return self.page.locator("#agreeTerms")

    @property
    def agree(self) -> Locator:
        """Backward-compat alias for agree_terms."""
        return self.agree_terms

    @property
    def submit_btn(self) -> Locator:
        """Кнопка отправки формы регистрации."""
        return self.page.get_by_role("button", name=t(Buttons.SIGNUP))

    @property
    def password_toggle(self) -> Locator:
        """no semantic: icon-only toggle"""
        return self.page.locator("#pwToggle")

    @property
    def password_strength(self) -> Locator:
        """no semantic: custom meter widget"""
        return self.page.locator('[data-testid="signup-pw-meter"]')

    @property
    def signup_msg(self) -> Locator:
        """no semantic: no ARIA role"""
        return self.page.locator("#signupMsg")

    @property
    def email_error(self) -> Locator:
        """no semantic: dynamic content, no ARIA"""
        return self.page.locator("#email-err")

    @property
    def agree_group(self) -> Locator:
        """no semantic: checkbox group container"""
        return self.page.locator('[data-testid="signup-agree-group"]')

    def fill_required(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None = None,  # accepted for backward-compat, ignored (поле удалено в I4)
        birth_year: int | None = None,  # accepted for backward-compat, ignored
        agree: bool = True,
    ) -> Self:
        """Заполняет минимально-валидную signup форму.

        `agree=True` ставит обязательный `#agreeTerms` — без него
        Pydantic-validator возвращает 422 «Необходимо принять условия
        использования». Privacy / cross-border consent объединены с
        terms_accepted на бэке (Wave-9, см. backend router.py:417).

        `agree=False` — оставляем checkbox неотмеченным (используется в
        тестах валидации формы).

        Параметры `full_name` и `birth_year` — приняты для совместимости
        со старыми тест-вызовами (поля удалены из формы commit 814d5f8).
        UI их больше не показывает; через JSON API всё ещё доходят.
        """
        del full_name, birth_year  # silence unused — параметры for API-compat
        with step("действие: заполнить форму регистрации"):
            self.email.fill(email)
            self.password.fill(password)
            if agree:
                self.agree_terms.check()
        return self

    def fill_credentials(self, *, email: str, password: str) -> Self:
        """Fill email and password without checking agree or submitting."""
        with step("действие: заполнить email и пароль"):
            self.email.fill(email)
            self.password.fill(password)
        return self

    def submit(self) -> Self:
        """Click the signup submit button."""
        with step("действие: отправить регистрацию"):
            self.submit_btn.click()
        return self

    def submit_by_id(self) -> Self:
        """Click the signup submit button by element ID (for non-semantic tests)."""
        with step("действие: отправить регистрацию (по ID)"):
            self.submit_btn_by_id.click()
        return self

    def expect_verification_message(self) -> None:
        """After successful submit `#signupMsg` gets the `success` class added.
        Regex match — survives copy / class additions."""
        with step("проверка: сообщение верификации"):
            expect(self.signup_msg).to_have_class(re.compile(r"\bsuccess\b"))

    def expect_visible_form(self) -> None:
        """Assert email, password and submit button are visible."""
        with step("проверка: форма регистрации видима"):
            expect(self.email).to_be_visible()
            expect(self.password).to_be_visible()
            expect(self.submit_btn).to_be_visible()

    @property
    def form(self) -> Locator:
        """Return the signup form locator."""
        return self.page.locator("#signupForm")  # no semantic: form element by ID

    @property
    def submit_btn_by_id(self) -> Locator:
        """Return the signup submit button by ID (for non-semantic tests)."""
        return self.page.locator("#signupBtn")  # no semantic: submit button without accessible name

    def check_password_validity(self) -> bool:
        """Return the HTML5 checkValidity() result for the password field."""
        return self.page.evaluate("() => document.getElementById('password').checkValidity()")

    def fill_honeypot_via_js(self, *, email: str, password: str, honeypot: str) -> None:
        """Fill form fields including the hidden honeypot via JS evaluate.

        The honeypot field is visually hidden (tabindex=-1), so we use
        JS to set all values simultaneously. The checkbox is also set via JS.
        """
        self.page.evaluate(
            f"""
            document.querySelector('#email').value = {email!r};
            document.querySelector('#password').value = {password!r};
            document.querySelector('#website').value = {honeypot!r};
            document.querySelector('#agreeTerms').checked = true;
            """
        )

    def remove_password_minlength(self) -> None:
        """Remove the HTML5 minlength attribute from the password field.

        Useful for testing server-side validation (zxcvbn) without native
        browser validation blocking the submit.
        """
        self.page.evaluate("document.getElementById('password').removeAttribute('minlength')")

    def mock_overflow_response(self, *, email: str, subscribed: bool = True) -> None:
        """Intercept POST /api/account/signup and return waitlist_required."""

        def _handler(route) -> None:
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "status": "waitlist_required",
                    "email": email,
                    "waitlist_subscribed": subscribed,
                }),
            )

        with step("действие: мок overflow ответа"):
            self.page.route("**/api/account/signup", _handler)

    def soft_check_form_basics(self, soft: Expect) -> None:
        """Smoke for X-SU-1..11: input attrs, autocomplete, required.

        После Wave-9 форма имеет один consent (`#agreeTerms`); privacy /
        cross-border объединены с terms_accepted на бэке.
        """
        soft(self.email).to_have_attribute("type", "email")
        soft(self.email).to_have_attribute("autocomplete", "email")
        soft(self.email).to_have_attribute("required", "")
        soft(self.password).to_have_attribute("type", "password")
        soft(self.password).to_have_attribute("autocomplete", "new-password")
        soft(self.honeypot).to_have_attribute("tabindex", "-1")
        soft(self.submit_btn).to_have_attribute("type", "submit")
        soft(self.agree_terms).to_have_attribute("required", "")
