"""
Обёртка над httpx.Response с цепочкой проверок expect().status().schema().

    from framework.response import expect_response
    expect_response(r).status(HTTPStatus.OK).json_has("tenant_slug")
    expect_response(r, label="signup").status(HTTPStatus.OK).schema(SignupResponse)

Сообщения об ошибках содержат ожидаемое/фактическое и контекст запроса;
токены и пароли маскируются через _sanitize_text.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, NoReturn, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from http import HTTPStatus

    import httpx

T = TypeVar("T", bound=BaseModel)

SENSITIVE_KEYS = frozenset({
    "access_token", "refresh_token", "token", "password",
    "secret", "authorization", "cookie", "session_id",
})


def _sanitize_json(data: Any) -> Any:
    """Маскирует чувствительные значения в JSON-структуре."""
    if isinstance(data, dict):
        return {
            k: "***" if k.lower() in SENSITIVE_KEYS else _sanitize_json(v)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_sanitize_json(item) for item in data]
    return data


def _sanitize_text(text: str) -> str:
    """Маскирует токены/пароли в строке ответа для безопасных отчётов."""
    if not text:
        return text
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return text
    sanitized = _sanitize_json(data)
    try:
        return json.dumps(sanitized, ensure_ascii=False)
    except TypeError:
        return str(sanitized)


class ResponseExpectation:
    """Цепочка проверок ответа; при неудаче — AssertionError с контекстом."""

    __slots__ = ("_label", "_r")

    def __init__(self, response: httpx.Response, *, label: str = "") -> None:
        self._r = response
        self._label = label

    def _fail(self, message: str) -> NoReturn:
        """Поднимает AssertionError с контекстом запроса (без секретов)."""
        r = self._r
        url = getattr(r.request, "url", "?")
        method = getattr(r.request, "method", "?")
        body = _sanitize_text(r.text[:500]) if r.text else ""
        parts = [
            f"{self._label}: " if self._label else "",
            message,
            f"\n  {method} {url}",
            f"\n  status={r.status_code}",
            f"\n  body={body!r}" if body else "",
        ]
        raise AssertionError("".join(parts))

    def status(self, *codes: int | HTTPStatus) -> ResponseExpectation:
        """Проверяет status_code; при несовпадении — AssertionError."""
        if self._r.status_code not in codes:
            self._fail(
                f"expected status {codes[0] if len(codes) == 1 else codes}, "
                f"got {self._r.status_code}"
            )
        return self

    def status_ok(self) -> ResponseExpectation:
        """Проверяет status_code в диапазоне 2xx."""
        if not (200 <= self._r.status_code < 300):
            self._fail(f"expected 2xx, got {self._r.status_code}")
        return self

    def json_has(self, *keys: str) -> ResponseExpectation:
        """Проверяет наличие ключей в JSON-ответе."""
        data = self._r.json()
        if not isinstance(data, dict):
            self._fail(f"expected JSON object, got {type(data).__name__}")
        missing = [k for k in keys if k not in data]
        if missing:
            self._fail(f"missing keys {missing} in {sorted(data)}")
        return self

    def json_eq(self, key: str, value: Any) -> ResponseExpectation:
        """Проверяет значение ключа в JSON-ответе."""
        data = self._r.json()
        if not isinstance(data, dict):
            self._fail(f"expected JSON object, got {type(data).__name__}")
        actual = data.get(key, "<MISSING>")
        if actual != value:
            self._fail(f"{key}: expected {value!r}, got {actual!r}")
        return self

    def schema(self, model: type[T]) -> T:
        """Парсит JSON и валидирует моделью Pydantic; возвращает экземпляр."""
        try:
            data = self._r.json()
        except (json.JSONDecodeError, ValueError) as exc:
            self._fail(f"response is not JSON: {exc}")
        try:
            return model.model_validate(data)
        except (ValueError, TypeError) as exc:
            self._fail(f"schema validation failed ({model.__name__}): {exc}")

    def list_schema(self, model: type[T]) -> list[T]:
        """Парсит JSON-массив и валидирует каждый элемент моделью."""
        try:
            data = self._r.json()
        except (json.JSONDecodeError, ValueError) as exc:
            self._fail(f"response is not JSON: {exc}")
        if not isinstance(data, list):
            self._fail(f"expected JSON array, got {type(data).__name__}")
        try:
            return [model.model_validate(item) for item in data]
        except (ValueError, TypeError) as exc:
            self._fail(f"list schema validation failed ({model.__name__}): {exc}")

    @property
    def data(self) -> Any:
        """Парсит и возвращает raw JSON."""
        return self._r.json()


class ApiResponse:
    """Обёртка над httpx.Response: делегирует атрибуты, добавляет expect()."""

    def __init__(self, response: httpx.Response) -> None:
        self._response = response

    @property
    def status_code(self) -> int:
        """HTTP status code."""
        return self._response.status_code

    @property
    def headers(self) -> Any:
        """Response headers."""
        return self._response.headers

    def json(self, **kwargs: Any) -> Any:
        """Parse response body as JSON."""
        return self._response.json(**kwargs)

    @property
    def text(self) -> str:
        """Raw response body text."""
        return self._response.text

    def expect(self, *, label: str = "") -> ResponseExpectation:
        """Цепочка проверок: .status(code).schema(Model)."""
        return ResponseExpectation(self._response, label=label)

    def raise_for_status(self) -> None:
        """Delegate to httpx raise_for_status."""
        self._response.raise_for_status()


def expect_response(
    r: httpx.Response, *, label: str = "",
) -> ResponseExpectation:
    """Создаёт цепочку проверок для httpx response."""
    return ResponseExpectation(r, label=label)
