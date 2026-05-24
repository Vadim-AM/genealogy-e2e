"""INV-SLUG-001a: reserved slugs не назначаются как tenant slugs."""

from __future__ import annotations

import allure
import pytest

from assertions.base import should
from framework.step import step
from src.texts import ErrMsg

_RESERVED_SLUGS = ("admin", "api", "www", "root", "mail", "ftp", "support")


@pytest.mark.parametrize("reserved", _RESERVED_SLUGS)
@allure.title("Зарезервированные slug-и не назначаются при регистрации")
def test_signup_does_not_assign_reserved_slug(signup_via_api, reserved: str) -> None:
    """INV-SLUG-001a: derived slug не совпадает с reserved word."""
    with step(f"действие: signup с email '{reserved}@e2e.example.com'"):
        email = f"{reserved}@e2e.example.com"
        user = signup_via_api(email=email)

    with step(f"проверка: slug не совпадает с reserved '{reserved}'"):
        should.not_equal(user.slug, reserved, ErrMsg.reserved_slug_assigned)
