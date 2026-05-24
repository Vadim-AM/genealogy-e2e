"""First visit after login (этап 5-6 funnel).

Covers: F-FV-1..6 при первом заходе owner'а в свой tenant.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from api import routes
from framework.step import step
from pages.tree_page import TreePage
from src.texts import ErrMsg

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory

# Демо-seed содержит demo-self + 2 родителя вокруг центрального субъекта =
# 2 orbit-карточки в кольцевом виде (карточка центрального субъекта
# рендерится в другом DOM-слоте — `#tab-tree .section-title`).
DEMO_SEED_RING_CARDS = 2


@allure.title("Первый визит отображает дерево с демо-данными")
def test_first_visit_renders_tree_with_demo_seed(owner_page: Page, pages: PageFactory) -> None:
    """F-FV-1, F-FV-2: owner visits / and orbit-view renders the demo ring.

    Concrete count assertion via `.orbit-card` selector — beats the prior
    "loading indicator hid" smoke. Backend seeds 5 persons; orbit shows
    the centered subject plus immediate ring (parents) = 2 cards visible.
    """
    with step("действие: переход на главную"):
        tree = pages.navigate_to(TreePage)
        owner_page.wait_for_load_state("domcontentloaded")

    with step("проверка: orbit-view отрисовал демо-карточки"):
        tree.expect_tree_rendered(min_cards=DEMO_SEED_RING_CARDS)


@allure.title("Авторизованному пользователю видны навигационные вкладки")
def test_first_visit_shows_authed_tabs(owner_page: Page, pages: PageFactory) -> None:
    """F-FV-4: основные навигационные вкладки видны.

    Wave-9: tab `map` скрыт через `hidden=""` (BUG-MAP-001 — фича Map
    спрятана за feature-flag, который пока выключен на дефолте). Проверяем
    остальные 4 вкладки; Map-теста отдельно (xfail) — см. test_map_no_flag.
    """
    with step("действие: переход на главную"):
        tree = pages.navigate_to(TreePage)
        owner_page.wait_for_load_state("domcontentloaded")

    with step("проверка: навигационные вкладки видны"):
        expect(tree.tab_tree, ErrMsg.tab_not_visible).to_be_visible()
        expect(tree.tab_sources, ErrMsg.tab_not_visible).to_be_visible()
        expect(tree.tab_timeline, ErrMsg.tab_not_visible).to_be_visible()
        expect(tree.tab_about, ErrMsg.tab_not_visible).to_be_visible()


@allure.title("Поле поиска отображается в шапке после входа")
def test_first_visit_search_input_visible(owner_page: Page, pages: PageFactory) -> None:
    """F-FV-5: search input is in the header for authed users."""
    _ = pages.navigate_to(TreePage)
    owner_page.wait_for_load_state("domcontentloaded")
    expect(owner_page.locator("#headerSearch"), ErrMsg.element_not_visible).to_be_visible()


@allure.title("Кнопка повтора тура видна на главной после входа")
def test_first_visit_tour_replay_button_visible(owner_page: Page, pages: PageFactory) -> None:
    """F-FV-6: '?' tour replay button is visible."""
    _ = pages.navigate_to(TreePage)
    owner_page.wait_for_load_state("domcontentloaded")
    expect(owner_page.locator("#tourReplayBtn"), ErrMsg.button_not_visible).to_be_visible()


@allure.title("Эндпоинт /me возвращает slug тенанта после авторизации")
def test_me_endpoint_returns_tenant_after_login(owner_user, tenant_client) -> None:
    """F-FV-1 backend check: /api/account/me returns user + tenant slug."""
    with step("действие: запрос /me"):
        api = tenant_client(owner_user)
        r = api.get(routes.ACCOUNT_ME)
        r.raise_for_status()

    with step("проверка: slug тенанта совпадает"):
        assert r.json()["tenant"]["slug"] == owner_user.slug, \
            f"/me tenant slug: expected {owner_user.slug!r}, got {r.json()['tenant']['slug']!r}"
