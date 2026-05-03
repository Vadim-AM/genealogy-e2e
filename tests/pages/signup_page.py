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
        # `full_name` и `birth_year` поля удалены из signup-формы в commit
        # 814d5f8 (feat(signup): убрать поле ФИО — display_name заполняется
        # из карточки). Backend всё ещё принимает их в JSON-теле от API
        # (signup_via_api fixture отправляет full_name через payload), но в
        # UI они отсутствуют. Тесты, использовавшие SignupPage.full_name и
        # .birth_year, должны быть переписаны либо удалены.
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
        full_name: str | None = None,  # accepted for backward-compat, ignored (поле удалено в I4)
        birth_year: int | None = None,  # accepted for backward-compat, ignored
        agree: bool = True,
    ) -> "SignupPage":
        """Заполняет минимально-валидную signup форму.

        `agree=True` ставит ВСЕ 3 обязательных consent (terms / privacy /
        cross-border) — без любого из них Pydantic-validator вернёт 422
        «Необходимо принять условия использования» (P0.4 ФЗ-156).
        marketing_consent опциональный, default OFF.

        Для negative-проверок `agree=False` — оставляем все consent
        неотмеченными (используется в тестах валидации формы).

        Параметры `full_name` и `birth_year` — приняты для совместимости
        со старыми тест-вызовами (поля удалены из формы commit 814d5f8 «I4:
        убрать поле ФИО — display_name заполняется из карточки»). UI их
        больше не показывает; через JSON API всё ещё доходят (см. backend
        SignupRequest.full_name).
        """
        del full_name, birth_year  # silence unused — параметры for API-compat
        self.email.fill(email)
        self.password.fill(password)
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
        """Smoke for X-SU-1..11: input attrs, autocomplete, required.

        После I4 (commit 814d5f8) форма не имеет full_name / birth_year
        полей — display_name берётся из первой карточки tenant'а.
        Соответствующие проверки удалены.
        """
        soft(self.email).to_have_attribute("type", "email")
        soft(self.email).to_have_attribute("autocomplete", "email")
        soft(self.email).to_have_attribute("required", "")
        soft(self.password).to_have_attribute("type", "password")
        soft(self.password).to_have_attribute("autocomplete", "new-password")
        soft(self.honeypot).to_have_attribute("tabindex", "-1")
        soft(self.submit_btn).to_have_attribute("type", "submit")
        # 4 consent чекбокса — 3 required, 1 optional (P0.4 ФЗ-156, май 2026)
        soft(self.agree_terms).to_have_attribute("required", "")
        soft(self.agree_privacy).to_have_attribute("required", "")
        soft(self.agree_cross_border).to_have_attribute("required", "")
