"""Deep-link routing — TC-AUTH-1.

Direct navigation to `/#/p/{id}` for an authenticated owner must:
- preserve `window.AUTH.authenticated === true` after `/api/tree` finishes
  loading (regression of BUG-AUTH-001 where loadData reset the flag);
- render `.profile-page` for the requested person;
- show the person's name in the tab section title.

Was xfailed under BUG-AUTH-001 reopen until upstream commit `731fbc9`
("fix(auth): expose AUTH on window + in-place resetAUTH") landed in
dev on 28.04. Now a regular regression — keep tests strict.
"""

from __future__ import annotations

import allure
from playwright.sync_api import Page, expect

from tests._core.messages import TestData
from tests._core.step import step
from tests.helpers.auth.auth_ui import wait_for_auth_state


@allure.title("Прямая ссылка на персону сохраняет авторизацию")
def test_deep_link_to_demo_self_preserves_auth(owner_page: Page):
    """TC-AUTH-1: open /#/p/demo-self directly, expect the authed UI to settle."""
    with step("действие: переход по прямой ссылке на персону"):
        owner_page.goto(f"/#/p/{TestData.DEMO_PERSON_ID}")
        owner_page.wait_for_load_state("domcontentloaded")

    with step("проверка: профиль отрисован и авторизация сохранена"):
        # The tab title is overwritten with the opened person's name (profile.js
        # hoists the name into `#tab-tree .section-title`).
        expect(owner_page.locator("#tab-tree .section-title")).not_to_have_text("")
        expect(owner_page.locator('[data-testid="profile-page"]')).to_be_visible()

        # AUTH state must end up authenticated (BUG-AUTH-001 regression).
        wait_for_auth_state(owner_page, expected=True)


@allure.title("Ссылка на несуществующую персону не сбрасывает авторизацию")
def test_deep_link_to_unknown_id_keeps_auth(owner_page: Page):
    """A deep link to a non-existent person must NOT log the user out.

    Tree tab remains visible (no JS crash); AUTH stays authenticated.
    """
    with step("действие: переход по ссылке на несуществующую персону"):
        owner_page.goto("/#/p/no-such-person")
        owner_page.wait_for_load_state("domcontentloaded")

    with step("проверка: вкладка дерева видна и авторизация сохранена"):
        expect(owner_page.locator('[data-tab="tree"]')).to_be_visible()
        wait_for_auth_state(owner_page, expected=True)
