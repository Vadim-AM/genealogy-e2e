"""Базовые assertion-функции — замена голым assert в тестах.

Использование:
    from assertions.base import should

    should.be_equal(actual, expected, "статус тенанта")
    should.contain(text, "keyword", "заголовок содержит ключевое слово")
    should.be_true(config.enabled, "фича включена")
    should.have_length(tree.people, 3, "количество персон")
    should.any_match(items, lambda i: i.id == pid, "персона в дереве")

Для httpx-ответов: `expect_response(r).status(HTTPStatus.OK)`.
Для Playwright-элементов: `expect(locator, ErrMsg.x).to_be_visible()`.
Для всего остального — этот модуль.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any, Callable, Sized

import pytest


def _ctx(what: str) -> str:
    return f" ({what})" if what else ""


class _Should:
    """Универсальные assertion-функции. Импортируй `should` — не класс."""

    @staticmethod
    def be_equal(actual: Any, expected: Any, what: str = "") -> None:
        """actual == expected."""
        if actual != expected:
            pytest.fail(f"ожидали {expected!r}, получили {actual!r}{_ctx(what)}")

    @staticmethod
    def not_equal(actual: Any, expected: Any, what: str = "") -> None:
        """actual != expected."""
        if actual == expected:
            pytest.fail(f"значения не должны совпадать: {actual!r}{_ctx(what)}")

    @staticmethod
    def be_true(value: Any, what: str = "") -> None:
        """Truthiness."""
        if not value:
            pytest.fail(f"ожидали truthy, получили {value!r}{_ctx(what)}")

    @staticmethod
    def be_false(value: Any, what: str = "") -> None:
        """Falsiness."""
        if value:
            pytest.fail(f"ожидали falsy, получили {value!r}{_ctx(what)}")

    @staticmethod
    def be_none(value: Any, what: str = "") -> None:
        """value is None."""
        if value is not None:
            pytest.fail(f"ожидали None, получили {value!r}{_ctx(what)}")

    @staticmethod
    def not_none(value: Any, what: str = "") -> None:
        """value is not None."""
        if value is None:
            pytest.fail(f"значение не должно быть None{_ctx(what)}")

    @staticmethod
    def be_in(item: Any, collection: Any, what: str = "") -> None:
        """item in collection."""
        if item not in collection:
            pytest.fail(f"{item!r} не найден в коллекции{_ctx(what)}")

    @staticmethod
    def contain(text: str, substring: str, what: str = "") -> None:
        """substring in text."""
        if substring not in text:
            pytest.fail(f"{substring!r} не найден в {text[:200]!r}{_ctx(what)}")

    @staticmethod
    def not_contain(text: str, substring: str, what: str = "") -> None:
        """substring not in text."""
        if substring in text:
            pytest.fail(f"{substring!r} не должен быть в тексте{_ctx(what)}")

    @staticmethod
    def have_length(collection: Sized, expected: int, what: str = "") -> None:
        """len(collection) == expected."""
        actual = len(collection)
        if actual != expected:
            pytest.fail(f"ожидали длину {expected}, получили {actual}{_ctx(what)}")

    @staticmethod
    def be_empty(collection: Sized, what: str = "") -> None:
        """len(collection) == 0."""
        if len(collection) != 0:
            pytest.fail(f"коллекция должна быть пустой, содержит {len(collection)}{_ctx(what)}")

    @staticmethod
    def not_empty(collection: Sized, what: str = "") -> None:
        """len(collection) > 0."""
        if len(collection) == 0:
            pytest.fail(f"коллекция не должна быть пустой{_ctx(what)}")

    @staticmethod
    def be_instance(value: Any, expected_type: type, what: str = "") -> None:
        """isinstance(value, expected_type)."""
        if not isinstance(value, expected_type):
            pytest.fail(f"ожидали {expected_type.__name__}, получили {type(value).__name__}{_ctx(what)}")

    @staticmethod
    def any_match(iterable: Any, predicate: Callable, what: str = "") -> None:
        """any(predicate(item) for item in iterable)."""
        if not any(predicate(item) for item in iterable):
            pytest.fail(f"ни один элемент не удовлетворяет условию{_ctx(what)}")

    @staticmethod
    def all_match(iterable: Any, predicate: Callable, what: str = "") -> None:
        """all(predicate(item) for item in iterable)."""
        if not all(predicate(item) for item in iterable):
            pytest.fail(f"не все элементы удовлетворяют условию{_ctx(what)}")

    @staticmethod
    def greater(actual: Any, threshold: Any, what: str = "") -> None:
        """actual > threshold."""
        if not (actual > threshold):
            pytest.fail(f"ожидали > {threshold}, получили {actual}{_ctx(what)}")

    @staticmethod
    def greater_or_equal(actual: Any, threshold: Any, what: str = "") -> None:
        """actual >= threshold."""
        if not (actual >= threshold):
            pytest.fail(f"ожидали >= {threshold}, получили {actual}{_ctx(what)}")

    @staticmethod
    def less(actual: Any, threshold: Any, what: str = "") -> None:
        """actual < threshold."""
        if not (actual < threshold):
            pytest.fail(f"ожидали < {threshold}, получили {actual}{_ctx(what)}")

    @staticmethod
    def playwright_status(response: Any, expected: int | HTTPStatus, what: str = "") -> None:
        """Playwright Response.status == expected."""
        if response.status != expected:
            pytest.fail(f"ожидали статус {int(expected)}, получили {response.status}{_ctx(what)}")

    @staticmethod
    def playwright_ok(response: Any, what: str = "") -> None:
        """Playwright Response.ok (status 2xx)."""
        if not response.ok:
            pytest.fail(f"ожидали 2xx, получили {response.status}{_ctx(what)}")


should = _Should()
