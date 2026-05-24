"""Доменные assertion-функции для tree/person/relationship тестов."""

from __future__ import annotations

from typing import TYPE_CHECKING

from assertions.base import should
from src.texts import ErrMsg

if TYPE_CHECKING:
    from models.person import TreeResponse


def person_exists(tree: TreeResponse, person_id: str) -> None:
    """Персона с данным id присутствует в дереве."""
    should.any_match(tree.people, lambda p: p.id == person_id, ErrMsg.item_not_found)


def person_count(tree: TreeResponse, expected: int) -> None:
    """Количество персон в дереве совпадает с ожидаемым."""
    should.have_length(tree.people, expected, ErrMsg.count_mismatch)


def has_person_with_name(tree: TreeResponse, *substrings: str) -> None:
    """В дереве есть персона, чьё имя содержит все подстроки."""
    should.any_match(
        tree.people,
        lambda p: all(s in (p.name or "") for s in substrings),
        ErrMsg.item_not_found,
    )
