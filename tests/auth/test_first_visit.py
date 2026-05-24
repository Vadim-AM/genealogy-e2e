"""First visit after login (этап 5-6 funnel).

Covers: F-FV-1..6 при первом заходе owner'а в свой tenant.
"""

from __future__ import annotations

import allure
from playwright.sync_api import Page, expect

from tests._core.api_paths import API
from tests._core.step import step
from tests.pages.tree_page import TreePage

# Demo seed has demo-self + 2 parents around the centred subject =
# 2 orbit cards rendered in the ring view (the centred subject card
# is rendered in a different DOM slot — `#tab-tree .section-title`).
DEMO_SEED_RING_CARDS = 2


@allure.title("Первый визит отображает дерево с демо-данными")
def test_first_visit_renders_tree_with_demo_seed(owner_page: Page):
    """F-FV-1, F-FV-2: owner visits / and orbit-view renders the demo ring.

    Concrete count assertion via `.orbit-card` selector — beats the prior
    "loading indicator hid" smoke. Backend seeds 5 persons; orbit shows
    the centered subject plus immediate ring (parents) = 2 cards visible.
    """
    with step("действие: переход на главную"):
        tree = TreePage(owner_page).goto()
        owner_page.wait_for_load_state("domcontentloaded")

    with step("проверка: orbit-view отрисовал демо-карточки"):
        tree.expect_tree_rendered(min_cards=DEMO_SEED_RING_CARDS)


@allure.title("Авторизованному пользователю видны навигационные вкладки")
def test_first_visit_shows_authed_tabs(owner_page: Page):
    """F-FV-4: основные навигационные вкладки видны.

    Wave-9: tab `map` скрыт через `hidden=""` (BUG-MAP-001 — фича Map
    спрятана за feature-flag, который пока выключен на дефолте). Проверяем
    остальные 4 вкладки; Map-теста отдельно (xfail) — см. test_map_no_flag.
    """
    with step("действие: переход на главную"):
        tree = TreePage(owner_page).goto()
        owner_page.wait_for_load_state("domcontentloaded")

    with step("проверка: навигационные вкладки видны"):
        expect(tree.tab_tree).to_be_visible()
        expect(tree.tab_sources).to_be_visible()
        expect(tree.tab_timeline).to_be_visible()
        expect(tree.tab_about).to_be_visible()


@allure.title("Поле поиска отображается в шапке после входа")
def test_first_visit_search_input_visible(owner_page: Page):
    """F-FV-5: search input is in the header for authed users."""
    owner_page.goto("/")
    owner_page.wait_for_load_state("domcontentloaded")
    expect(owner_page.locator("#headerSearch")).to_be_visible()


@allure.title("Кнопка повтора тура видна на главной после входа")
def test_first_visit_tour_replay_button_visible(owner_page: Page):
    """F-FV-6: '?' tour replay button is visible."""
    owner_page.goto("/")
    owner_page.wait_for_load_state("domcontentloaded")
    expect(owner_page.locator("#tourReplayBtn")).to_be_visible()


@allure.title("Эндпоинт /me возвращает slug тенанта после авторизации")
def test_me_endpoint_returns_tenant_after_login(owner_user, tenant_client):
    """F-FV-1 backend check: /api/account/me returns user + tenant slug."""
    with step("действие: запрос /me"):
        api = tenant_client(owner_user)
        r = api.get(API.ACCOUNT_ME)
        r.raise_for_status()

    with step("проверка: slug тенанта совпадает"):
        assert r.json()["tenant"]["slug"] == owner_user.slug, \
            f"/me tenant slug: expected {owner_user.slug!r}, got {r.json()['tenant']['slug']!r}"
