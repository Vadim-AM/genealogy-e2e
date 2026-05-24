"""Fluent response assertions with rich error context.

    expect_response(r).status(200).json_has("tenant_slug")
    expect_response(r, label="signup").status(200).json_eq("status", "verification_sent")
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx


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

    def status(self, *codes: int) -> ResponseExpectation:
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

    @property
    def data(self) -> Any:
        return self._r.json()


def expect_response(r: httpx.Response, *, label: str = "") -> ResponseExpectation:
    """Create a fluent assertion chain for an httpx response."""
    return ResponseExpectation(r, label=label)
