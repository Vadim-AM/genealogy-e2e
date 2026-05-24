"""INV-SLUG-001a: reserved slugs не назначаются как tenant slugs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
import pytest

from assertions.base import should
from config.constants import unique_email
from framework.step import step
from src.texts import ErrMsg

if TYPE_CHECKING:
    from collections.abc import Callable

    from fixtures.users import AuthUser


_RESERVED_SLUGS = ("admin", "api", "www", "root", "mail", "ftp", "support")


@pytest.mark.parametrize("reserved", _RESERVED_SLUGS)
@allure.title("Зарезервированные slug-и не назначаются при регистрации")
def test_signup_does_not_assign_reserved_slug(signup_via_api: Callable[..., AuthUser], reserved: str) -> None:
    """INV-SLUG-001a: derived slug не совпадает с reserved word."""
    with step(f"действие: signup с email на основе reserved '{reserved}'"):
        email = unique_email(reserved)
        user = signup_via_api(email=email)

    with step(f"проверка: slug не совпадает с reserved '{reserved}'"):
        should.not_equal(user.slug, reserved, ErrMsg.reserved_slug_assigned)
