"""Доменные assertion-функции для auth/session тестов."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

from assertions.base import should
from src.texts import ErrMsg

if TYPE_CHECKING:
    from playwright.sync_api import Response


def session_valid(status_code: int) -> None:
    """Сессия валидна (GET /api/account/me → 200)."""
    should.be_equal(status_code, HTTPStatus.OK, ErrMsg.session_should_be_valid)


def session_expired(status_code: int) -> None:
    """Сессия невалидна (GET /api/account/me → 401)."""
    should.be_equal(status_code, HTTPStatus.UNAUTHORIZED, ErrMsg.session_should_be_expired)


def playwright_response_ok(response: Response, what: str = ErrMsg.status_mismatch) -> None:
    """Playwright Response.ok (status 2xx)."""
    should.playwright_ok(response, what)
