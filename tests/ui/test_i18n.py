"""TC-i18N-1 / BUG-i18N-001: backend возвращает error detail на английском."""

from __future__ import annotations

from http import HTTPStatus

import allure
import httpx

from api import routes
from assertions.base import should
from config.constants import unique_email
from framework.response import expect_response
from framework.step import step
from helpers.ui.i18n_checks import has_cyrillic
from src.texts import ErrMsg


@allure.title("i18n: ошибка входа с неверным паролем приходит на русском")
def test_login_wrong_credentials_error_detail_in_russian(uvicorn_server: str) -> None:
    """Login с несуществующим email → response detail должен быть на русском."""
    with step("действие: отправить login с неверными credentials"), httpx.Client(base_url=uvicorn_server) as c:
        r = c.post(
            routes.LOGIN,
            json={
                "email": unique_email("i18n"),
                "password": "any-password-here",
            },
            headers={"Accept-Language": "ru"},
        )

    with step("проверка: ошибка содержит кириллицу"):
        expect_response(r, label="login with unknown user").status(HTTPStatus.UNAUTHORIZED)
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}  # noqa: drift
        detail = body.get("detail") or body.get("message") or ""

        should.be_true(has_cyrillic(detail), ErrMsg.error_not_russian)


@allure.title("i18n: ошибка валидации при регистрации приходит на русском")
def test_signup_validation_error_detail_in_russian(uvicorn_server: str) -> None:
    """Signup с слишком коротким паролем → 422 с detail на русском."""
    with step("действие: отправить signup с коротким паролем"), httpx.Client(base_url=uvicorn_server) as c:
        c.post(routes.TEST_RESET_SIGNUP_RATE).raise_for_status()
        r = c.post(
            routes.SIGNUP,
            json={
                "email": unique_email("i18n-sg"),
                "password": "short",
                "full_name": "Тест",
            },
            headers={"Accept-Language": "ru"},
        )

    with step("проверка: validation detail на русском"):
        expect_response(
            r,
            label="signup with short password",
        ).status(HTTPStatus.UNPROCESSABLE_ENTITY)
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}  # noqa: drift

        # Backend форматирует validation detail двумя способами:
        #   - Pydantic 422 → `detail: list[{msg, loc, type}]`
        #   - Custom validator → `detail: str` (например "Value error, Пароль …")
        # Принимаем обе формы — критично что текст содержит кириллицу (rule #4).
        detail = body.get("detail")
        if isinstance(detail, list):
            msgs = [item.get("msg", "") for item in detail if isinstance(item, dict)]
            should.be_true(any(has_cyrillic(m) for m in msgs), ErrMsg.error_not_russian)
        else:
            should.be_true(has_cyrillic(str(detail)), ErrMsg.error_not_russian)
