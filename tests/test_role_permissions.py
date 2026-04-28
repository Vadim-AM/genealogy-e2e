"""Role-based access — INV-PERM-003a (viewer cannot read).

После accept invite с role=viewer пользователь должен иметь
**read-only** access к древу и профилям. Run security 28.04 night
выявил, что viewer'ы получают **403** на все GET-эндпоинты:
`/api/people/{id}`, `/api/tree`, etc. — endpoint требует
`require_editor` вместо `require_viewer`.

Симптом для пользователя: семья кликает invite-ссылку, accept проходит
успешно («Готово! Вы добавлены в древо»), но открыв главную видят
только пустую страницу или ошибку — никакой пользы от invite.

Это P0 для UX (invite flow «семья как со-владелец» не работает) и
для бизнес-модели (Researcher tier обещает «до 5 редакторов и
неограниченных читателей» — readers не работают).
"""

from __future__ import annotations

import re
import uuid

import httpx
import pytest

from tests.messages import TestData
from tests.timeouts import TIMEOUTS

DEFAULT_PASSWORD = "test_password_8plus"


def _create_invite_and_accept_as_viewer(
    base_url: str, owner_user, viewer_email: str
):
    """Owner создаёт invite role=viewer, второй user signup'ится и
    accept'ит. Возвращает AuthUser-like dict с cookies+slug viewer'а
    (теперь у него membership в owner_user.tenant)."""
    # 1. Owner создаёт invite role=viewer.
    inv = httpx.post(
        f"{base_url}/api/account/tenant/invites",
        json={"name": "Тётя", "role": "viewer"},
        cookies=owner_user.cookies,
        headers={"X-Tenant-Slug": owner_user.slug},
        timeout=TIMEOUTS.api_request,
    )
    inv.raise_for_status()
    invite_token = inv.json()["token"]

    # 2. Second user signup + verify + login.
    with httpx.Client(base_url=base_url, timeout=TIMEOUTS.api_request) as c:
        c.post("/api/_test/reset-signup-rate", timeout=TIMEOUTS.api_short).raise_for_status()
        c.post(
            "/api/account/signup",
            json={"email": viewer_email, "password": DEFAULT_PASSWORD, "full_name": "Гостевой Зритель"},
        ).raise_for_status()
        mail = c.get("/api/_test/last-email", params={"to": viewer_email}).json()
        token = re.search(r"token=([\w\-]+)", mail["text_body"]).group(1)
        c.post("/api/account/verify-email", params={"token": token}).raise_for_status()

        login = c.post(
            "/api/account/login",
            json={"email": viewer_email, "password": DEFAULT_PASSWORD},
        )
        login.raise_for_status()
        viewer_cookies = dict(login.cookies)

        # 3. Accept invite (через owner's tenant_slug в payload).
        accept = c.post(
            "/api/invites/accept",
            json={"token": invite_token},
            cookies=viewer_cookies,
        )
        accept.raise_for_status()

    return {
        "cookies": viewer_cookies,
        "slug": owner_user.slug,
    }


@pytest.mark.xfail(
    reason="INV-PERM-003a: viewer (через accept invite role=viewer) "
           "получает 403 на GET /api/tree и /api/people/* (Run security "
           "28.04 night). Endpoint'ы require_editor где должно быть "
           "require_viewer. Семья кликает invite — попадает в пустоту. "
           "Fix: разделить read vs write в auth_v2 dependencies. GET — "
           "require_viewer (включает viewer/editor/owner), POST/PATCH/"
           "DELETE — require_editor. См. backend/app/auth_v2/* + "
           "endpoint handlers.",
    strict=False,
)
def test_viewer_can_read_tree(signup_via_api, base_url: str):
    """INV-PERM-003a: viewer's GET /api/tree returns 200 with data."""
    owner = signup_via_api(email=f"perm-owner-{uuid.uuid4().hex[:8]}@e2e.example.com")
    viewer_email = f"perm-viewer-{uuid.uuid4().hex[:8]}@e2e.example.com"

    viewer = _create_invite_and_accept_as_viewer(base_url, owner, viewer_email)

    r = httpx.get(
        f"{base_url}/api/tree",
        cookies=viewer["cookies"],
        headers={"X-Tenant-Slug": viewer["slug"]},
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code == 200, (
        f"viewer GET /api/tree should be 200, got {r.status_code}: {r.text[:200]}"
    )


@pytest.mark.xfail(
    reason="INV-PERM-003a (same): viewer не может читать профили "
           "конкретных person'ов. См. test_viewer_can_read_tree.",
    strict=False,
)
def test_viewer_can_read_person(signup_via_api, base_url: str):
    """INV-PERM-003a: viewer GET /api/people/{id} returns 200."""
    owner = signup_via_api(email=f"perm-o2-{uuid.uuid4().hex[:8]}@e2e.example.com")
    viewer_email = f"perm-v2-{uuid.uuid4().hex[:8]}@e2e.example.com"

    viewer = _create_invite_and_accept_as_viewer(base_url, owner, viewer_email)

    r = httpx.get(
        f"{base_url}/api/people/{TestData.DEMO_PERSON_ID}",
        cookies=viewer["cookies"],
        headers={"X-Tenant-Slug": viewer["slug"]},
        timeout=TIMEOUTS.api_request,
    )
    assert r.status_code == 200, (
        f"viewer GET /api/people/{TestData.DEMO_PERSON_ID} should be 200, "
        f"got {r.status_code}: {r.text[:200]}"
    )
