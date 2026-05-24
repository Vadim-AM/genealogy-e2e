"""POM for /signup."""

from __future__ import annotations

import re
from typing import Self

from playwright.sync_api import Locator, Page, expect

from src.texts import Buttons, Labels, t

from .base import BasePage


class SignupPage(BasePage):
    URL = "/signup"

    def __init__(self, page: Page):
        super().__init__(page)
        self.email = page.get_by_label(t(Labels.EMAIL))
        self.password = page.locator("#password")  # no semantic: get_by_label("Пароль") matches toggle button too
        # `full_name` и `birth_year` поля удалены из signup-формы в commit
        # 814d5f8 (feat(signup): убрать поле ФИО — display_name заполняется
        # из карточки). Backend всё ещё принимает их в JSON-теле от API
        # (signup_via_api fixture отправляет full_name через payload), но в
        # UI они отсутствуют. Тесты, использовавшие SignupPage.full_name и
        # .birth_year, должны быть переписаны либо удалены.
        self.honeypot = page.locator("#website")  # no semantic: hidden honeypot field
        # Stage-0 (RU-бета, Wave-9): отдельные `#agreePrivacy`/`#agreeCrossBorder`
        # удалены из формы — privacy объединён с terms_accepted (см. backend
        # auth_v2/router.py:208-422). Остался один `#agreeTerms` обязательный.
        # API endpoint всё ещё принимает privacy_consent / cross_border_consent
        # / marketing_consent в payload как optional bool (default False),
        # т.е. signup_via_api продолжает работать с 3-field payload.
        self.agree_terms = page.locator("#agreeTerms")  # no semantic: custom checkbox wrapper
        # Backward-compat (старые тесты используют `.agree` как короткий алиас).
        self.agree = self.agree_terms
        self.submit_btn = page.get_by_role("button", name=t(Buttons.SIGNUP))
        self.password_toggle = page.locator("#pwToggle")  # no semantic: icon-only toggle
        self.password_strength = page.locator('[data-testid="signup-pw-meter"]')  # no semantic: custom meter widget
        self.signup_msg = page.locator("#signupMsg")  # no semantic: no ARIA role
        self.email_error = page.locator("#email-err")  # no semantic: dynamic content, no ARIA
        # no semantic: checkbox group container
        self.agree_group = page.locator('[data-testid="signup-agree-group"]')

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
        self.email.fill(email)
        self.password.fill(password)
        if agree:
            self.agree_terms.check()
        return self

    def submit(self) -> Self:
        """Click the signup submit button."""
        self.submit_btn.click()
        return self

    def expect_verification_message(self) -> None:
        """After successful submit `#signupMsg` gets the `success` class added.
        Regex match — survives copy / class additions."""
        expect(self.signup_msg).to_have_class(re.compile(r"\bsuccess\b"))

    def expect_visible_form(self) -> None:
        """Assert email, password and submit button are visible."""
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

    def soft_check_form_basics(self, soft) -> None:
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
