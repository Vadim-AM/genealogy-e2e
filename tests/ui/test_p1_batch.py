"""P1 batch — мелкие UI-проверки которые расширяют partial → covered."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, Route, expect

from api import routes
from assertions.base import should
from framework.step import step
from pages.add_relative_modal import AddRelativeModal
from pages.confirm_dialog import ConfirmDialog
from pages.profile_panel import ProfilePanel, open_editor_for
from pages.tree_page import TreePage
from src.texts import AboutTab, ErrMsg, Placeholders, TestData, t

if TYPE_CHECKING:
    from fixtures.page_factory import PageFactory


@allure.title("Древо: минимапа видна авторизованному пользователю")
def test_minimap_visible_on_tree_tab_for_authed_owner(pages: PageFactory) -> None:
    """TC-04.05: `#minimap.visible` на desktop когда auth user открыл."""
    tree = pages.navigate_to(TreePage)

    expect(tree.minimap, ErrMsg.minimap_not_visible).to_be_visible()
    expect(tree.minimap, ErrMsg.wrong_css_class).to_have_class(re.compile(r"\bvisible\b"))


@allure.title("Древо: легенда веток скрыта при менее чем 3 поколениях")
def test_branch_legend_is_hidden_when_tree_has_less_than_3_generations(
    pages: PageFactory,
) -> None:
    """TC-04.09 (negative): demo seed = subject + 2 родителя = 2 поколения,."""
    tree = pages.navigate_to(TreePage)

    expect(tree.branch_legend, ErrMsg.element_should_be_hidden).not_to_be_visible()


@allure.title("Редактор: ArrowDown открывает выпадающий список пола")
def test_custom_select_opens_on_arrow_down_keyboard(owner_page: Page) -> None:
    """TC-25.06: focus на trigger custom-select + ArrowDown открывает."""
    with step("подготовка: открыть редактор персоны"):
        editor = open_editor_for(owner_page)

    with step("действие: фокус на gender select и ArrowDown"):
        expect(editor.custom_select_wrapper("gender"), ErrMsg.dropdown_not_visible).to_be_visible()
        editor.focus_custom_select("gender")
        editor.press_key("ArrowDown")

    with step("проверка: dropdown открылся"):
        expect(editor.custom_select_dropdown_locator("gender"), ErrMsg.dropdown_not_visible).to_be_visible()


@allure.title("Редактор: Escape закрывает выпадающий список")
def test_custom_select_closes_on_escape_keyboard(owner_page: Page) -> None:
    """TC-25.06 (продолжение): Esc после открытия закрывает dropdown."""
    with step("подготовка: открыть редактор и dropdown"):
        editor = open_editor_for(owner_page)
        editor.focus_custom_select("gender")
        editor.press_key("ArrowDown")
        dropdown = editor.custom_select_dropdown_locator("gender")
        expect(dropdown, ErrMsg.dropdown_not_visible).to_be_visible()

    with step("действие: нажать Escape"):
        editor.press_key("Escape")

    with step("проверка: dropdown закрылся"):
        expect(dropdown, ErrMsg.dropdown_should_be_closed).not_to_be_visible()


@allure.title("Диалог подтверждения: Escape отменяет удаление персоны")
def test_confirm_dialog_escape_cancels(owner_page: Page) -> None:
    """TC-20.02 (Esc): открываем confirmDialog через delete-flow на."""
    with step("подготовка: открыть editor и listener на DELETE"):
        editor = open_editor_for(owner_page, person_id="demo-grandpa")
        delete_responses: list[int] = []
        owner_page.on(
            "response",
            lambda r: (
                delete_responses.append(r.status) if routes.PEOPLE in r.url and r.request.method == "DELETE" else None
            ),
        )

    with step("действие: открыть confirm-dialog через delete"):
        editor.delete()
        dialog = ConfirmDialog(owner_page)
        dialog.expect_visible()

    with step("действие: нажать Escape"):
        dialog.dismiss_via_escape()

    with step("проверка: диалог закрыт и DELETE не ушёл"):
        dialog.expect_hidden()
        should.be_empty(delete_responses, ErrMsg.delete_should_not_fire)


@allure.title("Профиль: кнопка добавления родителей скрыта при двух имеющихся")
def test_add_parent_button_hidden_when_two_parents_exist(owner_page: Page) -> None:
    """TC-05.06: demo seed имеет subject + 2 родителя → кнопка."""
    with step("действие: открыть профиль demo-персоны"):
        panel = ProfilePanel.navigate_to(owner_page, TestData.DEMO_PERSON_ID)

    with step("проверка: кнопка + Родители отсутствует в DOM"):
        # add_relative_button даёт scoped Locator — `.first` не нужен,
        # filter по тексту уже сужает. Контракт: count == 0 при limit hit.
        add_parent = panel.add_relative_button("Родители")
        should.be_equal(add_parent.count(), 0, ErrMsg.add_parent_should_be_removed)


@allure.title("Вкладки Sources и Timeline содержат декоративный футер-орнамент")
def test_footer_ornament_present_in_sources_and_timeline_tabs(pages: PageFactory) -> None:
    """TC-04.07: Каждый из tab-sources / tab-timeline содержит."""
    with step("действие: загрузить главную"):
        tree = pages.navigate_to(TreePage)

    with step("проверка: footer-ornament в sources и timeline"):
        should.be_equal(tree.sources_footer_ornament.count(), 1, ErrMsg.footer_ornament_wrong)
        should.be_equal(tree.timeline_footer_ornament.count(), 1, ErrMsg.footer_ornament_wrong)
        # Три bullet'а как design-decision (· · · — index.html:164,183).
        expect(tree.sources_footer_ornament, ErrMsg.wrong_text_content).to_contain_text("•")


@allure.title("Таймлайн: отображаются 5 кнопок-фильтров по веткам")
def test_timeline_river_filters_render_five_branches(pages: PageFactory) -> None:
    """TC-12.02: после переключения на Timeline tab — 5 кнопок-фильтров."""
    with step("действие: переключиться на timeline"):
        tree = pages.navigate_to(TreePage)
        tree.switch_tab("timeline")

    with step("проверка: 5 фильтров в правильном порядке"):
        expect(tree.river_filters, ErrMsg.wrong_count).to_have_count(5)

        expected_branches = ["all", "maternal", "paternal", "other", "historical"]
        actual_branches = tree.river_filter_branches()
        should.be_equal(actual_branches, expected_branches, ErrMsg.filter_order_wrong)

    with step("проверка: active по умолчанию = all"):
        expect(tree.river_filters.nth(0), ErrMsg.wrong_css_class).to_have_class(re.compile(r"\bactive\b"))


@allure.title("О проекте: placeholder виден когда about_text не заполнен")
def test_about_tab_shows_placeholder_when_about_text_is_empty(pages: PageFactory) -> None:
    """TC-13.05: на чистом demo seed about_text не заполнен →."""
    with step("действие: открыть вкладку About"):
        tree = pages.navigate_to(TreePage)
        tree.expect_authed_state()
        tree.switch_tab("about")

    with step("проверка: placeholder виден с текстом-подсказкой"):
        expect(tree.about_placeholder, ErrMsg.element_not_visible).to_be_visible()
        expect(tree.about_placeholder, ErrMsg.wrong_text_content).to_contain_text(t(AboutTab.FAMILY_TREE_KEYWORD))


@allure.title("Родственник: при 409-конфликте модалка остаётся открытой")
def test_add_relative_shows_error_on_409_conflict(owner_page: Page) -> None:
    """TC-09.10: при попытке создать дубликат person backend возвращает."""

    with step("подготовка: подменить API на 409 через route"):

        def conflict_handler(route: Route) -> None:
            route.fulfill(
                status=409,
                content_type="application/json",
                body=json.dumps({"detail": "Duplicate person"}),
            )

        # Перехватываем все POST на person/relationship create endpoints.
        owner_page.route("**/api/admin/people", conflict_handler)
        owner_page.route("**/api/admin/relationships**", conflict_handler)
        owner_page.route("**/api/relationships", conflict_handler)

    with step("действие: открыть профиль и добавить родственника"):
        panel = ProfilePanel.navigate_to(owner_page, TestData.DEMO_PERSON_ID)
        panel.click_add_sibling()

        modal = AddRelativeModal(owner_page)
        modal.expect_visible()
        modal.fill_and_save(surname="Дубликат", given="Тест")

    with step("проверка: модалка осталась открытой при 409"):
        expect(modal.container, ErrMsg.modal_not_visible).to_be_visible()


@allure.title("Редактор: стрелки + Enter выбирают опцию в выпадающем списке")
def test_custom_select_arrow_down_then_enter_selects_option(owner_page: Page) -> None:
    """TC-25.06 (extension): ArrowDown открывает dropdown и фокусирует."""
    with step("подготовка: открыть редактор и dropdown"):
        editor = open_editor_for(owner_page)
        editor.focus_custom_select("gender")
        editor.press_key("ArrowDown")
        dropdown = editor.custom_select_dropdown_locator("gender")
        expect(dropdown, ErrMsg.dropdown_not_visible).to_be_visible()

    with step("действие: ArrowDown + Enter для выбора опции"):
        editor.press_key("ArrowDown")
        editor.press_key("Enter")

    with step("проверка: dropdown закрылся и native select обновился"):
        expect(dropdown, ErrMsg.dropdown_should_be_closed).not_to_be_visible()
        selected_value = editor.native_gender_value()
        should.be_true(selected_value, ErrMsg.native_select_not_synced)


@allure.title("Диалог подтверждения: Enter подтверждает удаление")
def test_confirm_dialog_enter_confirms_delete(owner_page: Page) -> None:
    """TC-20.02 (Enter): Enter в открытом confirmDialog → resolve(true)."""
    with step("подготовка: открыть confirm-dialog через delete"):
        editor = open_editor_for(owner_page, person_id="demo-grandpa")
        editor.delete()
        dialog = ConfirmDialog(owner_page)
        dialog.expect_visible()

    with (
        step("действие: подтвердить Enter и проверить DELETE"),
        owner_page.expect_request(
            lambda req: bool(re.search(rf"{routes.PEOPLE}/[^/?]+", req.url) and req.method == "DELETE")
        ),
    ):
        dialog.confirm()


@allure.title("Диалог подтверждения: клик по фону отменяет удаление")
def test_confirm_dialog_backdrop_click_cancels(owner_page: Page) -> None:
    """TC-20.02 (backdrop): click на overlay вне `.confirm-dialog`."""
    with step("подготовка: открыть editor и listener на DELETE"):
        editor = open_editor_for(owner_page, person_id="demo-grandpa")
        delete_responses: list[int] = []
        owner_page.on(
            "response",
            lambda r: (
                delete_responses.append(r.status) if routes.PEOPLE in r.url and r.request.method == "DELETE" else None
            ),
        )

    with step("действие: открыть confirm-dialog"):
        editor.delete()
        dialog = ConfirmDialog(owner_page)
        dialog.expect_visible()

    with step("действие: кликнуть по backdrop"):
        dialog.dismiss_via_backdrop()

    with step("проверка: диалог закрыт и DELETE не ушёл"):
        dialog.expect_hidden()
        should.be_empty(delete_responses, ErrMsg.delete_should_not_fire)


@allure.title("Таймлайн: клик по фильтру переключает активную ветку")
def test_timeline_river_filter_click_switches_active(pages: PageFactory) -> None:
    """TC-12.02 (extension): click `[data-testid="river-filter-btn"][data-branch=maternal]`."""
    with step("подготовка: переключиться на timeline"):
        tree = pages.navigate_to(TreePage)
        tree.expect_authed_state()
        tree.switch_tab("timeline")

    with step("действие: кликнуть по фильтру maternal"):
        all_btn = tree.river_filter_btn("all")
        maternal_btn = tree.river_filter_btn("maternal")
        expect(all_btn, ErrMsg.wrong_css_class).to_have_class(re.compile(r"\bactive\b"))
        tree.click_river_filter("maternal")

    with step("проверка: active переключился на maternal"):
        expect(maternal_btn, ErrMsg.wrong_css_class).to_have_class(re.compile(r"\bactive\b"))
        expect(all_btn, ErrMsg.wrong_css_class).not_to_have_class(re.compile(r"\bactive\b"))


@allure.title("Источники: поле поиска и фильтр-кнопки присутствуют")
def test_sources_tab_renders_search_input_and_filter_buttons(pages: PageFactory) -> None:
    """TC-11.02 (structural): после переключения на sources tab UI."""
    with step("действие: переключиться на sources"):
        tree = pages.navigate_to(TreePage)
        tree.expect_authed_state()
        tree.switch_tab("sources")

    with step("проверка: поле поиска с placeholder"):
        expect(tree.sources_search, ErrMsg.input_not_visible).to_be_visible()
        placeholder = tree.sources_search_placeholder()
        should.be_true(placeholder and t(Placeholders.SEARCH) in placeholder, ErrMsg.search_placeholder_wrong)

    with step("проверка: фильтр all активен по умолчанию"):
        expect(tree.sources_filter_all, ErrMsg.button_not_visible).to_be_visible()
        expect(tree.sources_filter_all, ErrMsg.wrong_css_class).to_have_class(re.compile(r"\bactive\b"))


@allure.title("Древо: минимапа скрыта на мобильном viewport (375px)")
def test_minimap_hidden_on_mobile_viewport(owner_page: Page, pages: PageFactory) -> None:
    """TC-04.06: media-query `@media (max-width: 720px) { .minimap {."""
    with step("действие: установить mobile viewport и открыть древо"):
        owner_page.set_viewport_size({"width": 375, "height": 800})
        tree = pages.navigate_to(TreePage)

    with step("проверка: minimap скрыт через display:none"):
        display = tree.minimap_computed_display()
        should.be_equal(display, "none", ErrMsg.element_should_be_hidden)


@allure.title("О проекте: placeholder контактов виден при пустых данных")
def test_about_contact_box_shows_placeholder_when_contacts_empty(pages: PageFactory) -> None:
    """TC-13.04 (negative): default seed → contact_text + contact_email пустые."""
    with step("действие: открыть вкладку About"):
        tree = pages.navigate_to(TreePage)
        tree.expect_authed_state()
        tree.switch_tab("about")

    with step("проверка: контактные данные пусты"):
        should.be_equal((tree.contact_text.text_content() or "").strip(), "", ErrMsg.contact_text_not_empty)
        should.be_equal((tree.contact_email.text_content() or "").strip(), "", ErrMsg.contact_text_not_empty)

    with step("проверка: placeholder контактов виден"):
        expect(tree.contact_box_placeholder, ErrMsg.element_not_visible).to_be_visible()


@allure.title("Древо: клик по карточке орбиты центрирует на персону")
def test_clicking_orbit_card_recenters_orbit_to_clicked_person(pages: PageFactory) -> None:
    """TC-04.08 / TC-05.01: click на не-центральную orbit-card →."""
    with step("подготовка: открыть главную и найти не-центральную карту"):
        tree = pages.navigate_to(TreePage)
        target_card = tree.non_center_orbit_card()
        expect(target_card, ErrMsg.orbit_card_not_visible).to_be_visible()
        target_pid = should.not_none(
            tree.orbit_card_person_id(target_card), ErrMsg.orbit_card_missing_pid
        )

    with step("действие: кликнуть по не-центральной карте"):
        tree.click_orbit_card(target_card)

    with step("проверка: центр орбиты переместился на кликнутую персону"):
        new_center = tree.orbit_center_for_person(target_pid)
        expect(new_center, ErrMsg.orbit_card_not_visible).to_be_visible()
