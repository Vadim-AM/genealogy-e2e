"""P1 batch — мелкие UI-проверки которые расширяют partial → covered.

Группа: TC-04.05 minimap, TC-04.09 branch legend (negative), TC-05.06
limit 2 родителя, TC-25.06 keyboard nav в custom select, TC-20.02
confirmDialog Esc/Enter, TC-09.10 conflict 409 при дубликате.

Тесты намеренно мелкие и быстрые — каждый проверяет один контракт.
Если testbed усложняется (нужны 3+ поколений / step-up MFA / file
fixtures) — TC переходит в P2 / другой батч.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, Route, expect

from tests._core.messages import AboutTab, Placeholders, TestData, t
from tests._core.step import step
from tests.pages.base import custom_select_for, wait_for_authed_shell
from tests.pages.confirm_dialog import ConfirmDialog
from tests.pages.person_editor import AddRelativeModal, PersonEditor
from tests.pages.profile_panel import ProfilePanel, open_editor_for
from tests.pages.tree_page import TreePage

if TYPE_CHECKING:
    from tests._fixtures.page_factory import PageFactory

# ─────────────────────────────────────────────────────────────────────────
# TC-04.05 — Minimap visible на tree tab у logged-in юзера (desktop)
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Древо: минимапа видна авторизованному пользователю")
def test_minimap_visible_on_tree_tab_for_authed_owner(pages: PageFactory):
    """TC-04.05: `#minimap.visible` на desktop когда auth user открыл
    tree tab. Минимап скрыт для guest (init.js:369-370) и при open
    editor (`body.editor-active .minimap`); проверяем default state.

    owner_page фикстура использует viewport 1440×900 (desktop) — на
    мобиле minimap скрыт через media-query `@media (max-width:...)`.
    """
    tree = pages.navigate_to(TreePage)

    expect(tree.minimap).to_be_visible()
    expect(tree.minimap).to_have_class(re.compile(r"\bvisible\b"))


# ─────────────────────────────────────────────────────────────────────────
# TC-04.09 — Branch legend СКРЫТ если в дереве <3 поколений (negative)
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Древо: легенда веток скрыта при менее чем 3 поколениях")
def test_branch_legend_is_hidden_when_tree_has_less_than_3_generations(
    pages: PageFactory,
):
    """TC-04.09 (negative): demo seed = subject + 2 родителя = 2 поколения,
    legend остаётся `display:none` (orbit.js:362). Positive case
    (≥3 generations + visible legend) требует расширенного seed-set —
    отдельный тест когда появятся такие фикстуры.
    """
    tree = pages.navigate_to(TreePage)

    expect(tree.branch_legend).not_to_be_visible()


# ─────────────────────────────────────────────────────────────────────────
# TC-25.06 — Custom select: ArrowDown открывает dropdown
# ─────────────────────────────────────────────────────────────────────────


def _open_editor(owner_page: Page, person_id: str = TestData.DEMO_PERSON_ID) -> PersonEditor:
    return open_editor_for(owner_page, person_id)


@allure.title("Редактор: ArrowDown открывает выпадающий список пола")
def test_custom_select_opens_on_arrow_down_keyboard(owner_page: Page):
    """TC-25.06: focus на trigger custom-select + ArrowDown открывает
    dropdown. Проверяем для gender select в person-editor.
    select.js:101 — Enter / Space / ArrowDown открывают dropdown когда
    `!isOpen`.
    """
    with step("подготовка: открыть редактор персоны"):
        _open_editor(owner_page)

    with step("действие: фокус на gender select и ArrowDown"):
        wrapper = custom_select_for(owner_page, "gender")
        expect(wrapper).to_be_visible()
        wrapper.focus()
        owner_page.keyboard.press("ArrowDown")

    with step("проверка: dropdown открылся"):
        dropdown = wrapper.locator('[data-testid="custom-select-dropdown"]')
        expect(dropdown).to_be_visible()


@allure.title("Редактор: Escape закрывает выпадающий список")
def test_custom_select_closes_on_escape_keyboard(owner_page: Page):
    """TC-25.06 (продолжение): Esc после открытия закрывает dropdown.
    select.js:122 — `else if (e.key === 'Escape')` закрытие.
    """
    with step("подготовка: открыть редактор и dropdown"):
        _open_editor(owner_page)
        wrapper = custom_select_for(owner_page, "gender")
        wrapper.focus()
        owner_page.keyboard.press("ArrowDown")
        dropdown = wrapper.locator('[data-testid="custom-select-dropdown"]')
        expect(dropdown).to_be_visible()

    with step("действие: нажать Escape"):
        owner_page.keyboard.press("Escape")

    with step("проверка: dropdown закрылся"):
        expect(dropdown).not_to_be_visible()


# ─────────────────────────────────────────────────────────────────────────
# TC-20.02 — confirmDialog Esc=cancel, Enter=confirm
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Диалог подтверждения: Escape отменяет удаление персоны")
def test_confirm_dialog_escape_cancels(owner_page: Page):
    """TC-20.02 (Esc): открываем confirmDialog через delete-flow на
    non-root persona (TestData.DELETABLE_PERSON_ID = "demo-grandpa"),
    Esc должен resolve(false) — модалка закрывается, DELETE не уходит.

    Note: на demo-self (subject root) кнопки delete нет, поэтому
    используем grandpa. Если seed изменится — тест падает информативно.
    """
    with step("подготовка: открыть editor и listener на DELETE"):
        editor = _open_editor(owner_page, person_id="demo-grandpa")
        delete_responses: list[int] = []
        owner_page.on(
            "response",
            lambda r: delete_responses.append(r.status)
            if "/api/people/" in r.url and r.request.method == "DELETE"
            else None,
        )

    with step("действие: открыть confirm-dialog через delete"):
        editor.btn_delete.click()
        dialog = ConfirmDialog(owner_page)
        dialog.expect_visible()

    with step("действие: нажать Escape"):
        dialog.dismiss_via_escape()

    with step("проверка: диалог закрыт и DELETE не ушёл"):
        dialog.expect_hidden()
        assert not delete_responses, (
            f"Esc должен отменить delete; backend получил DELETE: {delete_responses}"
        )


# ─────────────────────────────────────────────────────────────────────────
# TC-09.10 — Conflict 409 при дубликате (UI-isolated через mock)
# ─────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────
# TC-05.06 — Кнопка «+ Родители» прячется когда уже 2 parents
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Профиль: кнопка добавления родителей скрыта при двух имеющихся")
def test_add_parent_button_hidden_when_two_parents_exist(owner_page: Page):
    """TC-05.06: demo seed имеет subject + 2 родителя → кнопка
    «+ Родители» (`.profile-family-group:has-text(Родители) .profile-rel-add`)
    либо отсутствует в DOM, либо not_visible. RELATIVE_LIMITS.parents=2.
    """
    with step("действие: открыть профиль demo-персоны"):
        panel = ProfilePanel.navigate_to(owner_page, TestData.DEMO_PERSON_ID)

    with step("проверка: кнопка + Родители отсутствует в DOM"):
        # add_relative_button даёт scoped Locator — `.first` не нужен,
        # filter по тексту уже сужает. Контракт: count == 0 при limit hit.
        add_parent = panel.add_relative_button("Родители")
        assert add_parent.count() == 0, (
            "demo seed имеет 2 родителя, кнопка `+ Родители` должна быть удалена "
            f"из DOM (RELATIVE_LIMITS.parents=2); найдено {add_parent.count()} "
            "кнопок"
        )


# ─────────────────────────────────────────────────────────────────────────
# TC-04.07 — Footer-ornament • • • в табах sources / timeline
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Вкладки Sources и Timeline содержат декоративный футер-орнамент")
def test_footer_ornament_present_in_sources_and_timeline_tabs(owner_page: Page, pages: PageFactory):
    """TC-04.07: Каждый из tab-sources / tab-timeline содержит
    `.footer-ornament` с тремя bullet-точками. Это design-system
    маркер, регрессия = пустой/неструктурированный footer.
    """
    with step("действие: загрузить главную"):
        pages.navigate_to(TreePage)

    with step("проверка: footer-ornament в sources и timeline"):
        sources_ornament = owner_page.locator('#tab-sources [data-testid="footer-ornament"]')
        timeline_ornament = owner_page.locator('#tab-timeline [data-testid="footer-ornament"]')
        assert sources_ornament.count() == 1, (
            f"#tab-sources должен содержать ровно один footer-ornament; "
            f"got {sources_ornament.count()}"
        )
        assert timeline_ornament.count() == 1, (
            f"#tab-timeline должен содержать ровно один footer-ornament; "
            f"got {timeline_ornament.count()}"
        )
        # Три bullet'а как design-decision (· · · — index.html:164,183).
        expect(sources_ornament).to_contain_text("•")


# ─────────────────────────────────────────────────────────────────────────
# TC-12.02 — Timeline tab: river-filters (5 кнопок)
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Таймлайн: отображаются 5 кнопок-фильтров по веткам")
def test_timeline_river_filters_render_five_branches(owner_page: Page, pages: PageFactory):
    """TC-12.02: после переключения на Timeline tab — 5 кнопок-фильтров
    (`[data-testid="river-filter-btn"]`): Все / По матери / По отцу / Другие / История.
    Default active = «Все» (data-branch=all).
    """
    with step("действие: переключиться на timeline"):
        tree = pages.navigate_to(TreePage)
        tree.switch_tab("timeline")

    with step("проверка: 5 фильтров в правильном порядке"):
        filters = owner_page.locator('#riverFilters button[data-testid^="river-filter"]')
        expect(filters).to_have_count(5)

        expected_branches = ["all", "maternal", "paternal", "other", "historical"]
        actual_branches = [
            filters.nth(i).get_attribute("data-branch")
            for i in range(5)
        ]
        assert actual_branches == expected_branches, (
            f"river-filter порядок изменился; expected {expected_branches}, "
            f"got {actual_branches}"
        )

    with step("проверка: active по умолчанию = all"):
        expect(filters.nth(0)).to_have_class(re.compile(r"\bactive\b"))


# ─────────────────────────────────────────────────────────────────────────
# TC-13.05 — About: empty placeholder когда about_text not set
# ─────────────────────────────────────────────────────────────────────────


@allure.title("О проекте: placeholder виден когда about_text не заполнен")
def test_about_tab_shows_placeholder_when_about_text_is_empty(owner_page: Page, pages: PageFactory):
    """TC-13.05: на чистом demo seed about_text не заполнен →
    `[data-config-empty="about_text"]` блок visible с дефолтным
    текстом «Это семейное древо…». `[data-config-html="about_text"]`
    скрыт через `data-empty-hidden`.
    """
    with step("действие: открыть вкладку About"):
        tree = pages.navigate_to(TreePage)
        wait_for_authed_shell(owner_page)
        tree.switch_tab("about")

    with step("проверка: placeholder виден с текстом-подсказкой"):
        placeholder = owner_page.locator('[data-config-empty="about_text"]')
        expect(placeholder).to_be_visible()
        expect(placeholder).to_contain_text(t(AboutTab.FAMILY_TREE_KEYWORD))


@allure.title("Родственник: при 409-конфликте модалка остаётся открытой")
def test_add_relative_shows_error_on_409_conflict(owner_page: Page):
    """TC-09.10: при попытке создать дубликат person backend возвращает
    409 Conflict. UI должен показать error (#addRelError) и НЕ
    закрывать модалку silently. Backend response мочим через page.route —
    не зависим от реального duplicate-detection логики backend'а.

    Endpoint create-relative — POST /api/relationships (см.
    add-relative-modal.js). Modal остаётся открыта при non-200 ответе.
    """

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
        expect(modal.container).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────
# TC-25.06 (extension) — keyboard ↓ navigation + Enter selection
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Редактор: стрелки + Enter выбирают опцию в выпадающем списке")
def test_custom_select_arrow_down_then_enter_selects_option(owner_page: Page):
    """TC-25.06 (extension): ArrowDown открывает dropdown и фокусирует
    первый option; повторный ArrowDown переходит к следующему; Enter
    выбирает highlighted option и закрывает dropdown. Native select
    `data-field=gender` обновляется (form submission корректность).
    """
    with step("подготовка: открыть редактор и dropdown"):
        _open_editor(owner_page)
        wrapper = custom_select_for(owner_page, "gender")
        wrapper.focus()
        owner_page.keyboard.press("ArrowDown")
        dropdown = wrapper.locator('[data-testid="custom-select-dropdown"]')
        expect(dropdown).to_be_visible()

    with step("действие: ArrowDown + Enter для выбора опции"):
        owner_page.keyboard.press("ArrowDown")
        owner_page.keyboard.press("Enter")

    with step("проверка: dropdown закрылся и native select обновился"):
        expect(dropdown).not_to_be_visible()
        native = owner_page.locator('select[data-field="gender"]')
        selected_value = native.evaluate("(el) => el.value")
        assert selected_value, (
            f"select[data-field=gender] value не установлен после Enter; "
            f"got {selected_value!r}. Native select должен sync'аться с custom UI "
            f"для form submission."
        )


# ─────────────────────────────────────────────────────────────────────────
# TC-20.02 (extension) — Enter=confirm, click backdrop=cancel
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Диалог подтверждения: Enter подтверждает удаление")
def test_confirm_dialog_enter_confirms_delete(owner_page: Page):
    """TC-20.02 (Enter): Enter в открытом confirmDialog → resolve(true)
    → backend получает DELETE. confirm-dialog.js:138 — `Enter → cleanup(true)`.
    Делаем delete на demo-grandpa и проверяем что DELETE действительно
    ушёл — через `expect_request` (network ждёт fetch'а явно).
    """
    with step("подготовка: открыть confirm-dialog через delete"):
        editor = _open_editor(owner_page, person_id="demo-grandpa")
        editor.btn_delete.click()
        dialog = ConfirmDialog(owner_page)
        dialog.expect_visible()

    with step("действие: подтвердить Enter и проверить DELETE"), \
         owner_page.expect_request(
             lambda req: bool(re.search(r"/api/people/[^/?]+", req.url)
             and req.method == "DELETE")
         ):
        dialog.confirm()


@allure.title("Диалог подтверждения: клик по фону отменяет удаление")
def test_confirm_dialog_backdrop_click_cancels(owner_page: Page):
    """TC-20.02 (backdrop): click на overlay вне `.confirm-dialog`
    закрывает с resolve(false). Backend не получает DELETE.

    Note: реализация confirm-dialog.js может либо использовать
    backdrop-click handler, либо нет. Если контракт «не поддерживается»,
    тест fail'ится явно.
    """
    with step("подготовка: открыть editor и listener на DELETE"):
        editor = _open_editor(owner_page, person_id="demo-grandpa")
        delete_responses: list[int] = []
        owner_page.on(
            "response",
            lambda r: delete_responses.append(r.status)
            if "/api/people/" in r.url and r.request.method == "DELETE"
            else None,
        )

    with step("действие: открыть confirm-dialog"):
        editor.btn_delete.click()
        dialog = ConfirmDialog(owner_page)
        dialog.expect_visible()

    with step("действие: кликнуть по backdrop"):
        dialog.dismiss_via_backdrop()

    with step("проверка: диалог закрыт и DELETE не ушёл"):
        dialog.expect_hidden()
        assert not delete_responses, (
            f"Backdrop click должен отменить delete; backend получил DELETE: "
            f"{delete_responses}"
        )


# ─────────────────────────────────────────────────────────────────────────
# TC-12.02 (extension) — click filter button переключает active
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Таймлайн: клик по фильтру переключает активную ветку")
def test_timeline_river_filter_click_switches_active(owner_page: Page, pages: PageFactory):
    """TC-12.02 (extension): click `[data-testid="river-filter-btn"][data-branch=maternal]`
    → active class переходит с дефолтного `all` на `maternal`.
    Контракт: только одна кнопка active в каждый момент.
    """
    with step("подготовка: переключиться на timeline"):
        tree = pages.navigate_to(TreePage)
        wait_for_authed_shell(owner_page)
        tree.switch_tab("timeline")

    with step("действие: кликнуть по фильтру maternal"):
        all_btn = owner_page.locator('[data-testid="river-filter-all"]')
        maternal_btn = owner_page.locator('[data-testid="river-filter-maternal"]')
        expect(all_btn).to_have_class(re.compile(r"\bactive\b"))
        maternal_btn.click()

    with step("проверка: active переключился на maternal"):
        expect(maternal_btn).to_have_class(re.compile(r"\bactive\b"))
        expect(all_btn).not_to_have_class(re.compile(r"\bactive\b"))


# ─────────────────────────────────────────────────────────────────────────
# TC-11.02 — Sources tab: search input + filter buttons присутствуют
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Источники: поле поиска и фильтр-кнопки присутствуют")
def test_sources_tab_renders_search_input_and_filter_buttons(owner_page: Page, pages: PageFactory):
    """TC-11.02 (structural): после переключения на sources tab UI
    содержит search input (#evidenceSearch) с placeholder «Поиск...»
    и хотя бы одну `.filter-btn[data-filter=all]` (default active).
    """
    with step("действие: переключиться на sources"):
        tree = pages.navigate_to(TreePage)
        wait_for_authed_shell(owner_page)
        tree.switch_tab("sources")

    with step("проверка: поле поиска с placeholder"):
        search = owner_page.locator("#evidenceSearch")
        expect(search).to_be_visible()
        placeholder = search.get_attribute("placeholder")
        assert placeholder and t(Placeholders.SEARCH) in placeholder, (
            f"#evidenceSearch placeholder should contain {t(Placeholders.SEARCH)!r}; "
            f"got {placeholder!r}"
        )

    with step("проверка: фильтр all активен по умолчанию"):
        all_btn = owner_page.locator('.filter-btn[data-filter="all"]')
        expect(all_btn).to_be_visible()
        expect(all_btn).to_have_class(re.compile(r"\bactive\b"))


# ─────────────────────────────────────────────────────────────────────────
# TC-04.06 — Minimap скрыт на mobile (viewport ≤ 720px)
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Древо: минимапа скрыта на мобильном viewport (375px)")
def test_minimap_hidden_on_mobile_viewport(owner_page: Page, pages: PageFactory):
    """TC-04.06: media-query `@media (max-width: 720px) { .minimap {
    display:none !important; } }` (css/inline.css). Меняем viewport
    на 375×800 (iPhone SE-class) и проверяем computed display.
    """
    with step("действие: установить mobile viewport и открыть древо"):
        owner_page.set_viewport_size({"width": 375, "height": 800})
        tree = pages.navigate_to(TreePage)

    with step("проверка: minimap скрыт через display:none"):
        display = tree.minimap.evaluate("(el) => getComputedStyle(el).display")
        assert display == "none", (
            f"#minimap должен быть display:none на mobile (≤720px); "
            f"got {display!r}. Если правило @media (max-width:720px) удалено "
            f"в css/inline.css — регрессия mobile UX."
        )


# ─────────────────────────────────────────────────────────────────────────
# TC-04.08 / TC-05.01 — Click на orbit-card открывает orbit-view (SPA)
# ─────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────
# TC-13.04 — Контактная info из site_config: empty → скрыта
# ─────────────────────────────────────────────────────────────────────────


@allure.title("О проекте: placeholder контактов виден при пустых данных")
def test_about_contact_box_shows_placeholder_when_contacts_empty(owner_page: Page, pages: PageFactory):
    """TC-13.04 (negative): default seed → contact_text + contact_email пустые
    → `#contactBoxPlaceholder` (auth-only подсказка owner'у) показывается.

    Wave-9 markup (index.html:214-227): `.contact-box` всегда в DOM,
    `<p data-config-text="contact_text">` и `<a data-config-text="contact_email">`
    рендерят значения site_config. Когда оба empty — JS убирает `hidden`
    с `#contactBoxPlaceholder` (auth-only визуально подсказывает owner'у
    заполнить контакты).

    Positive case (contact_text задан) требует PATCH /api/site/config —
    отдельный тест.
    """
    with step("действие: открыть вкладку About"):
        tree = pages.navigate_to(TreePage)
        wait_for_authed_shell(owner_page)
        tree.switch_tab("about")

    with step("проверка: контактные данные пусты"):
        contact_text_p = owner_page.locator('[data-testid="contact-text"]')
        contact_email_a = owner_page.locator('[data-testid="contact-email"]')
        assert (contact_text_p.text_content() or "").strip() == "", \
            f"expected empty contact_text on default seed; got {contact_text_p.text_content()!r}"
        assert (contact_email_a.text_content() or "").strip() == "", \
            f"expected empty contact_email on default seed; got {contact_email_a.text_content()!r}"

    with step("проверка: placeholder контактов виден"):
        placeholder = owner_page.locator("#contactBoxPlaceholder")
        expect(placeholder).to_be_visible()


@allure.title("Древо: клик по карточке орбиты центрирует на персону")
def test_clicking_orbit_card_recenters_orbit_to_clicked_person(owner_page: Page, pages: PageFactory):
    """TC-04.08 / TC-05.01: click на не-центральную orbit-card →
    orbitNavigateTo(pid) → дерево перерендеривается так что
    `.orbit-zone-center .orbit-center-card[data-person-id]` указывает
    на нового центра. Это re-center логика, **не** SPA-навигация в
    profile (последняя триггерится отдельным data-action="open-profile").
    """
    with step("подготовка: открыть главную и найти не-центральную карту"):
        pages.navigate_to(TreePage)
        target_card = owner_page.locator(
            '#treeContainer [data-testid="orbit-card"][data-person-id]:not([data-testid="orbit-center-card"])'
        ).first
        expect(target_card).to_be_visible()
        target_pid = target_card.get_attribute("data-person-id")
        assert target_pid, "non-center orbit card has no data-person-id attribute"

    with step("действие: кликнуть по не-центральной карте"):
        target_card.click()

    with step("проверка: центр орбиты переместился на кликнутую персону"):
        new_center = owner_page.locator(
            f'.orbit-zone-center [data-testid="orbit-center-card"][data-person-id=\'{target_pid}\']'
        )
        expect(new_center).to_be_visible()
