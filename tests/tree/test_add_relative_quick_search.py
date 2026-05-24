"""FEATURE-PARENT-SEARCH-001: inline-autocomplete + linked-chip в модалке добавления родственника."""

from __future__ import annotations

import allure
from playwright.sync_api import Page, expect

from api import routes
from assertions.base import should
from framework.step import step
from helpers.tree.tree_api import people_count, seed_person
from helpers.tree.tree_navigation import open_demo_self_profile
from pages.person_editor import AddRelativeModal
from src.texts import ErrMsg, LinkedChip, TestData, t


@allure.title("Привязка существующего сиблинга создаёт только связь, не персону")
def test_link_existing_sibling_creates_only_relationship(
    owner_page: Page, owner_user, tenant_client
) -> None:
    """Привязка существующего person'а создаёт только relationship, не дубликат."""
    with step("подготовка: создание существующей персоны"):
        api = tenant_client(owner_user)
        existing_id = seed_person(
            api,
            pid="link-sib-existing",
            name="Прохор Иванов",
            surname="Иванов",
            given_name="Прохор",
        )
        count_before = people_count(api)

    with step("действие: поиск и привязка через автоподсказку"):
        panel = open_demo_self_profile(owner_page)
        panel.click_add_sibling()

        modal = AddRelativeModal(owner_page)
        modal.expect_visible()

        modal.search_existing(surname="Иван")
        modal.expect_dropdown_open()
        expect(modal.row_by_person_id(existing_id), ErrMsg.search_results_not_visible).to_be_visible()

        modal.pick_existing(existing_id)
        modal.expect_linked_to(existing_id)
        modal.expect_field_readonly("surname")
        modal.expect_field_readonly("given_name")

    with step("проверка: linked-chip содержит ожидаемые keywords"):
        expect(modal.linked_chip, ErrMsg.wrong_text_content).to_contain_text(t(LinkedChip.TITLE_KEYWORD))
        expect(modal.linked_chip, ErrMsg.wrong_text_content).to_contain_text(t(LinkedChip.HINT_KEYWORD))

    with step("действие: Save и проверка что POST /people не было"):
        post_people_count = 0

        def _track(response):
            nonlocal post_people_count
            if response.request.method == "POST" and response.url.endswith(
                routes.PEOPLE
            ):
                post_people_count += 1

        owner_page.on("response", _track)

        with owner_page.expect_response("**/api/relationships") as rel_info:
            modal.btn_save.click()
        rel_resp = rel_info.value
        should.playwright_ok(rel_resp, ErrMsg.pw_response_not_ok)
        should.be_equal(rel_resp.request.method, "POST", ErrMsg.pw_response_status_wrong)

        expect(modal.overlay, ErrMsg.overlay_should_be_closed).not_to_be_visible()
        should.be_equal(post_people_count, 0, ErrMsg.people_post_not_expected)

    with step("проверка: people-count не вырос"):
        should.be_equal(people_count(api), count_before, ErrMsg.person_count_wrong)


@allure.title("Отвязка привязанной персоны возвращает форму в режим создания")
def test_unlink_existing_returns_to_create_mode(
    owner_page: Page, owner_user, tenant_client
) -> None:
    """Отвязка возвращает форму в create-mode, правка + Save создаёт нового."""
    with step("подготовка: создание существующей персоны"):
        api = tenant_client(owner_user)
        existing_id = seed_person(
            api,
            pid="unlink-existing",
            name="Семён Семёнов",
            surname="Семёнов",
            given_name="Семён",
        )
        count_before = people_count(api)

    with step("действие: привязка существующего через автоподсказку"):
        panel = open_demo_self_profile(owner_page)
        panel.click_add_sibling()

        modal = AddRelativeModal(owner_page)
        modal.expect_visible()
        modal.search_existing(surname="Семён")
        modal.expect_dropdown_open()
        modal.pick_existing(existing_id)
        modal.expect_linked_to(existing_id)
        modal.expect_field_readonly("surname")

    with step("действие: отвязка и правка фамилии"):
        modal.unlink_existing()
        modal.expect_not_linked()
        expect(modal.surname, ErrMsg.wrong_attribute).not_to_have_attribute("readonly", "readonly")
        modal.surname.fill("Семёнов-Новый")

    with step("действие: сохранение нового человека"):
        with owner_page.expect_response(
            lambda r: routes.PEOPLE in r.url and r.request.method == "POST"
        ) as person_info:
            modal.btn_save.click()
        should.playwright_ok(person_info.value, ErrMsg.pw_response_not_ok)

    with step("проверка: ровно один новый person создан"):
        expect(modal.overlay, ErrMsg.overlay_should_be_closed).not_to_be_visible()
        should.be_equal(people_count(api), count_before + 1, ErrMsg.person_count_wrong)


@allure.title("Автоподсказка исключает текущую персону из списка")
def test_dropdown_excludes_self(owner_page: Page, owner_user, tenant_client) -> None:
    """Dropdown исключает currentPerson из результатов поиска."""
    with step("действие: поиск по подстроке имени текущей персоны"):
        panel = open_demo_self_profile(owner_page)
        panel.click_add_sibling()

        modal = AddRelativeModal(owner_page)
        modal.expect_visible()
        modal.search_existing(given="Польз")

    with step("проверка: текущая персона исключена из результатов"):
        expect(
            modal.row_by_person_id(TestData.DEMO_PERSON_ID),
            ErrMsg.element_should_be_hidden,
        ).not_to_be_visible()


@allure.title("Стрелка вниз и Enter выбирают кандидата из автоподсказки")
def test_keyboard_arrow_down_enter_picks_first_candidate(
    owner_page: Page, owner_user, tenant_client
) -> None:
    """ArrowDown + Enter выбирает первого кандидата из dropdown."""
    with step("подготовка: создание персоны для клавиатурного выбора"):
        api = tenant_client(owner_user)
        existing_id = seed_person(
            api,
            pid="kbd-existing",
            name="Глеб Глебов",
            surname="Глебов",
            given_name="Глеб",
        )

    with step("действие: открытие модалки и ввод фамилии"):
        panel = open_demo_self_profile(owner_page)
        panel.click_add_sibling()

        modal = AddRelativeModal(owner_page)
        modal.expect_visible()
        modal.search_existing(surname="Глеб")
        modal.expect_dropdown_open()

    with step("действие: выбор через ArrowDown + Enter"):
        modal.pick_first_via_keyboard()
        modal.expect_linked_to(existing_id)


@allure.title("Esc закрывает выпадающий список, но не модалку добавления")
def test_escape_closes_dropdown_keeps_modal(
    owner_page: Page, owner_user, tenant_client
) -> None:
    """Esc закрывает dropdown, но не модалку добавления."""
    with step("подготовка: создание персоны и открытие dropdown"):
        api = tenant_client(owner_user)
        seed_person(
            api,
            pid="esc-existing",
            name="Антон Антонов",
            surname="Антонов",
            given_name="Антон",
        )

        panel = open_demo_self_profile(owner_page)
        panel.click_add_sibling()

        modal = AddRelativeModal(owner_page)
        modal.expect_visible()
        modal.search_existing(surname="Антон")
        modal.expect_dropdown_open()

    with step("действие: нажатие Escape"):
        modal.press_escape()

    with step("проверка: dropdown закрыт, модалка осталась открытой"):
        modal.expect_dropdown_closed()
        expect(modal.container, ErrMsg.modal_not_visible).to_be_visible()
