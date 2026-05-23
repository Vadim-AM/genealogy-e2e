"""Sharing journey — owner creates a public link, an anonymous visitor
sees the card read-only, owner revokes, the link dies.

BUG-SHARE-PG-001 is fixed: `share_token` is platform-scoped and the
public view resolves the owning tenant by the token's `tenant_slug`, so
the anonymous /share/{token} page works with no tenant context at all.
"""

from __future__ import annotations

import allure

from tests.api_paths import API
from tests.messages import TestData
from tests.pages.share_page import SharePage


@allure.title("Публичная ссылка: аноним видит карточку, после отзыва -- нет")
def test_owner_shares_card_anon_views_then_revoke_kills_link(
    owner_user, tenant_client, browser,
):
    """Owner creates a person share link; an anonymous visitor opens it
    and sees the person read-only; owner revokes; the same link then
    shows the dead-link page. Covers create / list / view / revoke."""
    api = tenant_client(owner_user)

    created = api.post(
        API.SHARE_CREATE,
        json={"scope": "person", "person_id": TestData.DEMO_PERSON_ID},
    )
    created.raise_for_status()
    share_id = created.json()["id"]
    share_url = created.json()["url"]
    assert "/share/" in share_url, f"share url missing /share/ segment: {share_url!r}"

    # The owner's list shows the share — without leaking the token url.
    items = api.get(API.SHARE_LIST).json()["items"]
    assert any(s["id"] == share_id for s in items), \
        "created share must appear in the owner's list"
    for s in items:
        assert s.get("url") is None, f"GET /api/share/list leaked a token: {s}"

    # An anonymous visitor — fresh context, no auth, no tenant header —
    # opens the public page and sees the person.
    anon = browser.new_context()
    try:
        page = anon.new_page()
        page.goto(share_url)
        share = SharePage(page)
        share.expect_person_visible(TestData.DEFAULT_FULL_NAME.split()[0])
        share.expect_no_edit_controls()

        # Owner revokes the link.
        api.delete(API.share(share_id)).raise_for_status()

        # The same link is now dead for the anonymous visitor.
        page.goto(share_url)
        share.expect_error_visible()
    finally:
        anon.close()


@allure.title("Список шаринг-ссылок не содержит секретных токенов")
def test_share_list_never_leaks_tokens(owner_user, tenant_client):
    """Security invariant: GET /api/share/list returns the owner's shares
    but never the token url — tokens must not reach logs."""
    api = tenant_client(owner_user)
    created = api.post(
        API.SHARE_CREATE,
        json={"scope": "person", "person_id": TestData.DEMO_PERSON_ID},
    )
    created.raise_for_status()
    assert created.json()["url"], \
        f"create response must carry the share url, got {created.json()!r}"

    listed = api.get(API.SHARE_LIST).json()["items"]
    assert listed, "the created share must appear in the list (empty list)"
    for item in listed:
        assert item.get("url") is None, \
            f"GET /api/share/list leaked a token url: {item}"
