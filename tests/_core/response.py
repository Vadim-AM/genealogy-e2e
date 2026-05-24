"""Fluent response assertions with rich error context.

    expect_response(r).status(HTTPStatus.OK).json_has("tenant_slug")
    expect_response(r, label="signup").status(HTTPStatus.OK).json_eq("status", "verification_sent")
"""
from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    import httpx

T = TypeVar("T", bound=BaseModel)


class ResponseExpectation:
    __slots__ = ("_label", "_r")

    def __init__(self, response: httpx.Response, *, label: str = "") -> None:
        self._r = response
        self._label = label

    def _ctx(self, detail: str) -> str:
        r = self._r
        parts = [
            f"{self._label}: " if self._label else "",
            detail,
            f"\n  {r.request.method} {r.request.url}",
            f"\n  status={r.status_code}",
            f"\n  body={r.text[:300]!r}" if r.text else "",
        ]
        return "".join(parts)

    def status(self, *codes: int | HTTPStatus) -> ResponseExpectation:
        """Assert the response status code is one of the expected values."""
        assert self._r.status_code in codes, self._ctx(
            f"expected status {codes[0] if len(codes) == 1 else codes}, "
            f"got {self._r.status_code}"
        )
        return self

    def status_ok(self) -> ResponseExpectation:
        """Assert the response status code is in the 2xx range."""
        assert 200 <= self._r.status_code < 300, self._ctx(
            f"expected 2xx, got {self._r.status_code}"
        )
        return self

    def json_has(self, *keys: str) -> ResponseExpectation:
        """Assert the response JSON body contains all specified keys."""
        data = self._r.json()
        missing = [k for k in keys if k not in data]
        assert not missing, self._ctx(
            f"missing keys {missing} in {sorted(data)}"
        )
        return self

    def json_eq(self, key: str, value: Any) -> ResponseExpectation:
        """Assert a specific key in the response JSON equals the expected value."""
        data = self._r.json()
        actual = data.get(key, "<MISSING>")
        assert actual == value, self._ctx(
            f"{key}: expected {value!r}, got {actual!r}"
        )
        return self

    def schema(self, model: type[T]) -> T:
        """Parse JSON and validate against a Pydantic model, returning the typed instance."""
        try:
            data = self._r.json()
        except Exception as exc:
            msg = self._ctx(f"response is not JSON: {exc}")
            raise AssertionError(msg) from exc
        try:
            return model.model_validate(data)
        except Exception as exc:
            msg = self._ctx(f"schema validation failed ({model.__name__}): {exc}")
            raise AssertionError(msg) from exc

    def list_schema(self, model: type[T]) -> list[T]:
        """Parse JSON array and validate each item against a Pydantic model."""
        try:
            data = self._r.json()
        except Exception as exc:
            msg = self._ctx(f"response is not JSON: {exc}")
            raise AssertionError(msg) from exc
        assert isinstance(data, list), self._ctx(
            f"expected JSON array, got {type(data).__name__}"
        )
        try:
            return [model.model_validate(item) for item in data]
        except Exception as exc:
            msg = self._ctx(f"list schema validation failed ({model.__name__}): {exc}")
            raise AssertionError(msg) from exc

    @property
    def data(self) -> Any:
        """Return raw parsed JSON."""
        return self._r.json()


def expect_response(r: httpx.Response, *, label: str = "") -> ResponseExpectation:
    """Create a fluent assertion chain for an httpx response."""
    return ResponseExpectation(r, label=label)
