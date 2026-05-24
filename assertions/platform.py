"""Доменные assertion-функции для platform/superadmin тестов."""

from __future__ import annotations

from typing import Any

import pytest

from assertions.base import should
from src.texts import ErrMsg


def tenant_in_list(tenants: list[dict], slug: str) -> None:
    """Тенант с данным slug присутствует в списке."""
    should.any_match(tenants, lambda t: t.get("slug") == slug, ErrMsg.item_not_found)


def field_in_items(items: list[dict], field_name: str) -> None:
    """Поле с данным именем есть в items."""
    should.any_match(items, lambda o: o.get("field_name") == field_name, ErrMsg.item_not_found)


def field_not_in_items(items: list[dict], field_name: str) -> None:
    """Поля с данным именем нет в items."""
    if any(o.get("field_name") == field_name for o in items):
        pytest.fail(ErrMsg.item_not_found)


def json_key_present(data: dict[str, Any], key: str) -> None:
    """Ключ присутствует в JSON-ответе."""
    should.be_in(key, data, ErrMsg.response_field_wrong)
