"""Доменные assertion-функции для auth/session тестов."""

from __future__ import annotations

from http import HTTPStatus

from assertions.base import should
from src.texts import ErrMsg


def session_valid(status_code: int) -> None:
    """Сессия валидна (GET /api/account/me → 200)."""
    should.be_equal(status_code, HTTPStatus.OK, ErrMsg.session_should_be_valid)


def session_expired(status_code: int) -> None:
    """Сессия невалидна (GET /api/account/me → 401)."""
    should.be_equal(status_code, HTTPStatus.UNAUTHORIZED, ErrMsg.session_should_be_expired)


def playwright_response_ok(response, what: str = ErrMsg.status_mismatch) -> None:
    """Playwright Response.ok (status 2xx)."""
    should.playwright_ok(response, what)
