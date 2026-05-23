"""Tree navigation helpers — opening profiles via hash-routing and search."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.api_paths import API
from tests.messages import TestData
from tests.pages.profile_panel import ProfilePanel
from tests.pages.tree_page import TreePage
from tests.step import step
from tests.timeouts import TIMEOUTS


def open_profile(page: Page, person_id: str) -> ProfilePanel:
    """Navigate к profile через full page load.

    init.js:898 hash route -- **one-shot** at page load (нет hashchange
    listener). Если в одном тесте уже был открыт другой профиль, простой
    `goto("/#/p/Y")` или мутация `location.hash` НЕ перезапустит init.js
    + не подтянет свежий DATA cache.

    Решение: navigate к "/" (clears state), потом goto к /#/p/{id} --
    Playwright делает реальные навигации, init.js перезапускается, DATA
    свежий, routed setTimeout(openProfile(pid)) открывает profile.
    """
    page.goto("/")
    page.wait_for_load_state("domcontentloaded")
    page.goto(f"/#/p/{person_id}")
    page.wait_for_load_state("domcontentloaded")
    panel = ProfilePanel(page)
    panel.expect_visible()
    # Sanity: section-title must contain THIS person's name, not stale demo-self.
    title = page.locator('[data-testid="profile-section-title"]')
    expect(title).not_to_have_text("", timeout=TIMEOUTS.pw_expect_ms)
    return panel


def open_demo_self_profile(page: Page) -> ProfilePanel:
    page.goto(f"/#/p/{TestData.DEMO_PERSON_ID}")
    page.wait_for_load_state("networkidle")
    panel = ProfilePanel(page)
    panel.expect_visible()
    return panel


def search_and_open_profile(owner_page: Page, query: str) -> ProfilePanel:
    """User flow: navigate к /, type в header search, click first result
    -> orbit centers on person, click center card -> profile opens.

    `DATA.people` populated через `loadData()` -> `/api/tree` после mount;
    guard через `expect_response` (CSP блокирует string-`wait_for_function`).
    Search-click переключает orbit, не открывает profile напрямую --
    нужен дополнительный click по `[data-testid="orbit-center-card"]` (это естественный
    пользовательский путь: «нашёл -> перешёл на него в дереве -> открыл
    карточку»).
    """
    with step(f"search and open profile: {query!r}"):
        tree = TreePage(owner_page)
        with owner_page.expect_response(lambda r: "/api/tree" in r.url and r.ok):
            tree.goto()
        tree.search_input.fill(query)
        expect(tree.search_results.first).to_be_visible()
        tree.search_results.first.click()
        center_card = owner_page.locator('[data-testid="orbit-center-card"]')
        expect(center_card).to_contain_text(query)
        center_card.click()
        panel = ProfilePanel(owner_page)
        panel.expect_visible()
        return panel


def search_and_orbit(owner_page: Page, query: str) -> None:
    """User flow: navigate к /, search -> click first result -> orbit centers
    on person, **stay on orbit view** (без открытия profile).

    Используется для проверок, которые читают окружающие `.orbit-card`
    (relation labels к зафокусированному человеку).
    """
    tree = TreePage(owner_page)
    with owner_page.expect_response(lambda r: "/api/tree" in r.url and r.ok):
        tree.goto()
    tree.search_input.fill(query)
    expect(tree.search_results.first).to_be_visible()
    tree.search_results.first.click()
    expect(owner_page.locator('[data-testid="orbit-center-card"]')).to_be_visible()


def click_family_link(panel: ProfilePanel, group_label: str, name_substring: str) -> None:
    """Click `<a data-action="open-profile">name</a>` внутри указанной family group."""
    group = panel.container.locator('[data-testid="profile-family-group"]', has_text=group_label)
    expect(group).to_be_visible()
    link = group.locator('a[data-action="open-profile"]').filter(has_text=name_substring).first
    expect(link).to_be_visible()
    link.click()
    panel.expect_visible()
