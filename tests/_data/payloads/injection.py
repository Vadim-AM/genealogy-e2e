"""Injection payloads for XSS and SQL injection tests."""

from __future__ import annotations

XSS_PAYLOADS: list[str] = [
    '<script>alert("xss")</script>',
    '"><img src=x onerror=alert(1)>',
    "<svg/onload=alert(1)>",
    "javascript:alert(1)",
    "{{constructor.constructor('return this')()}}",
    '<a href="javascript:void(0)" onclick="alert(1)">click</a>',
]

SQL_PAYLOADS: list[str] = [
    "'; DROP TABLE people; --",
    "' OR '1'='1",
    "1; SELECT * FROM pg_tables--",
    "' UNION SELECT null,null,null--",
    "1' AND (SELECT 1 FROM pg_sleep(2))--",
]
