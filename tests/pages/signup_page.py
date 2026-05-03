"""POM for /signup."""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect

from .base import BasePage


class SignupPage(BasePage):
    URL = "/signup"

    def __init__(self, page: Page):
        super().__init__(page)
        self.email = page.locator("#email")
        self.password = page.locator("#password")
        self.full_name = page.locator("#full_name")
        self.birth_year = page.locator("#birth_year")
        self.honeypot = page.locator("#website")
        # 3 обязательных + 1 опциональный consent (P0.4 ФЗ-156, май 2026):
        # старый единый `#agree` → 4 раздельных. `#agree` legacy остаётся как
        # alias на agreeTerms если форма ещё не мигрирована — но новые тесты
        # должны использовать explicit поля.
        self.agree_terms = page.locator("#agreeTerms")
        self.agree_privacy = page.locator("#agreePrivacy")
        self.agree_cross_border = page.locator("#agreeCrossBorder")
        self.agree_marketing = page.locator("#agreeMarketing")
        # Backward-compat (старые тесты могут ещё использовать `.agree`):
        # делаем алиас на agree_terms, чтобы не сломать вызовы.
        self.agree = self.agree_terms
        self.submit_btn = page.locator("#signupBtn")
        self.password_toggle = page.locator("#pwToggle")
        self.password_strength = page.locator(".pw-meter")
        self.signup_msg = page.locator("#signupMsg")

    def fill_required(
        self,
        *,
        email: str,
        password: str,
        full_name: str = "Тестовый Пользователь",
        birth_year: int | None = None,
        agree: bool = True,
    ) -> "SignupPage":
        """Заполняет минимально-валидную signup форму.

        `agree=True` ставит ВСЕ 3 обязательных consent (terms / privacy /
        cross-border) — без любого из них Pydantic-validator вернёт 422
        «Необходимо принять условия использования» (P0.4 ФЗ-156).
        marketing_consent опциональный, default OFF.

        Для negative-проверок `agree=False` — оставляем все consent
        неотмеченными (используется в тестах валидации формы).
        """
        self.email.fill(email)
        self.password.fill(password)
        self.full_name.fill(full_name)
        if birth_year is not None:
            self.birth_year.fill(str(birth_year))
        if agree:
            self.agree_terms.check()
            self.agree_privacy.check()
            self.agree_cross_border.check()
        return self

    def submit(self) -> "SignupPage":
        self.submit_btn.click()
        return self

    def expect_verification_message(self) -> None:
        """After successful submit `#signupMsg` gets the `success` class added.
        Regex match — survives copy / class additions."""
        expect(self.signup_msg).to_have_class(re.compile(r"\bsuccess\b"))

    def expect_visible_form(self) -> None:
        expect(self.email).to_be_visible()
        expect(self.password).to_be_visible()
        expect(self.submit_btn).to_be_visible()

    def soft_check_form_basics(self, soft) -> None:
        """Smoke for X-SU-1..11: input attrs, autocomplete, required."""
        soft(self.email).to_have_attribute("type", "email")
        soft(self.email).to_have_attribute("autocomplete", "email")
        soft(self.email).to_have_attribute("required", "")
        soft(self.password).to_have_attribute("type", "password")
        soft(self.password).to_have_attribute("autocomplete", "new-password")
        soft(self.full_name).to_have_attribute("required", "")
        soft(self.honeypot).to_have_attribute("tabindex", "-1")
        soft(self.submit_btn).to_have_attribute("type", "submit")
