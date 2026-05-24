"""TC-10.02 — Map tab disabled by default (Wave-9 product state).

Map tab помечен `hidden` атрибутом прямо в `index.html:108`
(`<button class="tab" data-tab="map" hidden>`). Никакой JS не снимает
этот hidden — Map-фича включается через **специальную** ветку (feature
flag / role-based unhide), которая пока не реализована.

Старый тест проверял `.leaflet-attribution-flag` (политически
чувствительный флажок справа от ссылки «Leaflet») — это было важно
**когда** карта была видна. Сейчас:

- Map tab hidden by default → leaflet никогда не монтируется в default
  flow → атрибуция тоже не появляется → flag-element никогда не
  визуализируется.

Контракт сейчас: map tab `hidden` атрибут установлен. Этот регрессионный
pin ловит обратный случай — если кто-то случайно уберёт `hidden` без
enable feature flag, фича утечёт в prod в недо-готовом виде.

Историческая защита BUG-003 (CSS `.leaflet-attribution-flag { display:
none !important }`) сохранена в `/css/leaflet.css` — когда Map-feature
будет включена в default, добавить отдельный test на attribution-flag
hidden state.
"""

from __future__ import annotations

import allure
from playwright.sync_api import Page, expect

from tests._core.step import step
from tests.pages.tree_page import TreePage


@allure.title("Вкладка 'Карта' скрыта по умолчанию до включения фичи")
def test_map_tab_is_hidden_by_default(owner_page: Page):
    """TC-10.02 (Wave-9): map tab `<button data-tab="map">` has `hidden`
    attribute → not visible in tab strip until feature ships.

    Реальный контракт: map disabled by default. Если кто-то уберёт
    `hidden` — фича утекает в prod без готовности.
    """
    with step("действие: переход на главную"):
        tree = TreePage(owner_page).goto()

    with step("проверка: tab map в DOM, но скрыт через hidden"):
        expect(tree.tab_map).to_have_count(1)
        expect(tree.tab_map).to_be_hidden()
        expect(tree.tab_map).to_have_attribute("hidden", "")
