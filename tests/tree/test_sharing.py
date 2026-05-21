"""Sharing — share-link lifecycle (create → list → revoke).

The share trigger button is feature-flagged off in product, and the
public view (`GET /api/share/view/{token}`) is currently broken on
PostgreSQL — BUG-SHARE-PG-001: the `share_token` table is unreachable
from the anonymous, tenant-less view path (`UndefinedTable`). So the
owner→anon UI journey cannot be green yet.

This covers the working surface — create / list / revoke, all
tenant-scoped — as a backend-invariant lifecycle. The full
window.openShareModal journey + public-view assertions are written once
BUG-SHARE-PG-001 is fixed and the feature is enabled. See memory
`bug-share-view-pg`.
"""

from __future__ import annotations

from tests.api_paths import API
from tests.messages import TestData


def test_share_link_lifecycle_create_list_revoke(owner_user, tenant_client):
    """Owner creates a share link, sees it in the list (with the token
    url NOT leaked), revokes it — and it leaves the active list."""
    api = tenant_client(owner_user)

    created = api.post(
        API.SHARE_CREATE,
        json={"scope": "person", "person_id": TestData.DEMO_PERSON_ID},
    )
    created.raise_for_status()
    share_id = created.json()["id"]
    assert created.json()["url"], "create response must carry the share url"

    listed = api.get(API.SHARE_LIST).json()["items"]
    assert any(s["id"] == share_id for s in listed), \
        "created share must appear in the list"
    # Security invariant: the token url must never reach the list (logs).
    for s in listed:
        assert s.get("url") is None, f"GET /api/share/list leaked a token url: {s}"

    revoked = api.delete(API.share(share_id))
    revoked.raise_for_status()

    after = api.get(API.SHARE_LIST).json()["items"]
    assert not any(s["id"] == share_id for s in after), \
        "revoked share must drop out of the active list"
