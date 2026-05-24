"""TC-COPY-3 / BUG-COPY-003: welcome-email должен использовать GENEALOGY_PUBLIC_URL."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
import httpx

from api import routes
from assertions.base import should
from config.constants import unique_email
from framework.response import expect_response
from framework.step import step
from models.auth import EmailResponse
from src.texts import ErrMsg

if TYPE_CHECKING:
    from collections.abc import Callable

    from fixtures.users import AuthUser


@allure.title("Welcome-письмо содержит URL из GENEALOGY_PUBLIC_URL, не прод")
def test_welcome_email_uses_public_url_env_not_hardcoded_prod(
    signup_via_api: Callable[..., AuthUser], uvicorn_server: str
) -> None:
    """Welcome-email должен ссылаться на GENEALOGY_PUBLIC_URL, не на prod-домен."""
    with step("подготовка: signup и получение welcome-email"):
        email = unique_email("welcome")
        signup_via_api(email=email)

        with httpx.Client(base_url=uvicorn_server) as c:
            mail = c.get(routes.TEST_LAST_EMAIL, params={"to": email})
            mail_data = expect_response(mail, label="welcome email").status_ok().schema(EmailResponse)
            text_body = mail_data.text_body or ""
            html_body = mail_data.html_body or ""
            full_body = text_body + html_body

    with step("проверка: URL из GENEALOGY_PUBLIC_URL, не hardcoded prod"):
        public_host = uvicorn_server.split("://", 1)[-1].split(":", 1)[0]
        should.contain(full_body, public_host, ErrMsg.welcome_email_missing_host)
        should.not_contain(full_body, "nasharodoslovnaya.ru", ErrMsg.welcome_email_hardcoded_prod)
