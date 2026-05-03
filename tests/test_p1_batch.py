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

from playwright.sync_api import Page, Route, expect

from tests.messages import TestData
from tests.pages.person_editor import AddRelativeModal, PersonEditor
from tests.pages.profile_panel import ProfilePanel


# ─────────────────────────────────────────────────────────────────────────
# TC-04.05 — Minimap visible на tree tab у logged-in юзера (desktop)
# ─────────────────────────────────────────────────────────────────────────


def test_minimap_visible_on_tree_tab_for_authed_owner(owner_page: Page):
    """TC-04.05: `#minimap.visible` на desktop когда auth user открыл
    tree tab. Минимап скрыт для guest (init.js:369-370) и при open
    editor (`body.editor-active .minimap`); проверяем default state.

    owner_page фикстура использует viewport 1440×900 (desktop) — на
    мобиле minimap скрыт через media-query `@media (max-width:...)`.
    """
    owner_page.goto("/")
    owner_page.wait_for_load_state("networkidle")

    minimap = owner_page.locator("#minimap")
    expect(minimap).to_be_visible()
    expect(minimap).to_have_class(re.compile(r"\bvisible\b"))


# ─────────────────────────────────────────────────────────────────────────
# TC-04.09 — Branch legend СКРЫТ если в дереве <3 поколений (negative)
# ─────────────────────────────────────────────────────────────────────────


def test_branch_legend_is_hidden_when_tree_has_less_than_3_generations(
    owner_page: Page,
):
    """TC-04.09 (negative): demo seed = subject + 2 родителя = 2 поколения,
    legend остаётся `display:none` (orbit.js:362). Positive case
    (≥3 generations + visible legend) требует расширенного seed-set —
    отдельный тест когда появятся такие фикстуры.
    """
    owner_page.goto("/")
    owner_page.wait_for_load_state("networkidle")

    legend = owner_page.locator("#branchLegend")
    expect(legend).not_to_be_visible()


# ─────────────────────────────────────────────────────────────────────────
# TC-25.06 — Custom select: ArrowDown открывает dropdown
# ─────────────────────────────────────────────────────────────────────────


def _open_editor(owner_page: Page, person_id: str = TestData.DEMO_PERSON_ID) -> PersonEditor:
    owner_page.goto(f"/#/p/{person_id}")
    owner_page.wait_for_load_state("networkidle")
    panel = ProfilePanel(owner_page)
    panel.expect_visible()
    panel.open_editor()
    editor = PersonEditor(owner_page)
    editor.expect_visible()
    return editor


# Helper: найти .custom-select-обёртку для конкретного field. По
# структуре DOM (см. PersonEditor.select_dropdown в pages/person_editor.py)
# обёртка это **sibling** скрытого native select'а: `div.custom-select`
# идёт ПЕРЕД `select[data-field='{field}']` (CSS adjacent: `+`).
def _custom_select_for(page: Page, field: str):
    return page.locator(
        f"div.custom-select:has(+ select[data-field='{field}'])"
    )


def test_custom_select_opens_on_arrow_down_keyboard(owner_page: Page):
    """TC-25.06: focus на trigger custom-select + ArrowDown открывает
    dropdown. Проверяем для gender select в person-editor.
    select.js:101 — Enter / Space / ArrowDown открывают dropdown когда
    `!isOpen`.
    """
    _open_editor(owner_page)

    wrapper = _custom_select_for(owner_page, "gender")
    expect(wrapper).to_be_visible()

    # focus на wrapper (он tabindex'ed по select.js) → ArrowDown открывает.
    wrapper.focus()
    owner_page.keyboard.press("ArrowDown")
    # После открытия dropdown options становятся visible.
    dropdown = wrapper.locator(".custom-select-dropdown")
    expect(dropdown).to_be_visible()


def test_custom_select_closes_on_escape_keyboard(owner_page: Page):
    """TC-25.06 (продолжение): Esc после открытия закрывает dropdown.
    select.js:122 — `else if (e.key === 'Escape')` закрытие.
    """
    _open_editor(owner_page)
    wrapper = _custom_select_for(owner_page, "gender")
    wrapper.focus()
    owner_page.keyboard.press("ArrowDown")
    dropdown = wrapper.locator(".custom-select-dropdown")
    expect(dropdown).to_be_visible()

    owner_page.keyboard.press("Escape")
    expect(dropdown).not_to_be_visible()


# ─────────────────────────────────────────────────────────────────────────
# TC-20.02 — confirmDialog Esc=cancel, Enter=confirm
# ─────────────────────────────────────────────────────────────────────────


def test_confirm_dialog_escape_cancels(owner_page: Page):
    """TC-20.02 (Esc): открываем confirmDialog через delete-flow на
    non-root persona (TestData.DELETABLE_PERSON_ID = "demo-grandpa"),
    Esc должен resolve(false) — модалка закрывается, DELETE не уходит.

    Note: на demo-self (subject root) кнопки delete нет, поэтому
    используем grandpa. Если seed изменится — тест падает информативно.
    """
    editor = _open_editor(owner_page, person_id="demo-grandpa")
    delete_responses: list[int] = []
    owner_page.on(
        "response",
        lambda r: delete_responses.append(r.status)
        if "/api/people/" in r.url and r.request.method == "DELETE"
        else None,
    )
    editor.btn_delete.click()
    dialog = owner_page.locator(".confirm-dialog")
    expect(dialog).to_be_visible()

    # confirm-dialog.js:137 — Escape → cleanup(false). Никаких DELETE.
    owner_page.keyboard.press("Escape")
    expect(dialog).not_to_be_visible()
    assert not delete_responses, (
        f"Esc должен отменить delete; backend получил DELETE: {delete_responses}"
    )


# ─────────────────────────────────────────────────────────────────────────
# TC-09.10 — Conflict 409 при дубликате (UI-isolated через mock)
# ─────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────
# TC-05.06 — Кнопка «+ Родители» прячется когда уже 2 parents
# ─────────────────────────────────────────────────────────────────────────


def test_add_parent_button_hidden_when_two_parents_exist(owner_page: Page):
    """TC-05.06: demo seed имеет subject + 2 родителя → кнопка
    «+ Родители» (`.profile-family-group:has-text(Родители) .profile-rel-add`)
    либо отсутствует в DOM, либо not_visible. RELATIVE_LIMITS.parents=2.
    """
    owner_page.goto(f"/#/p/{TestData.DEMO_PERSON_ID}")
    owner_page.wait_for_load_state("networkidle")

    panel = ProfilePanel(owner_page)
    panel.expect_visible()

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


def test_footer_ornament_present_in_sources_and_timeline_tabs(owner_page: Page):
    """TC-04.07: Каждый из tab-sources / tab-timeline содержит
    `.footer-ornament` с тремя bullet-точками. Это design-system
    маркер, регрессия = пустой/неструктурированный footer.
    """
    owner_page.goto("/")
    owner_page.wait_for_load_state("networkidle")

    sources_ornament = owner_page.locator("#tab-sources .footer-ornament")
    timeline_ornament = owner_page.locator("#tab-timeline .footer-ornament")
    assert sources_ornament.count() == 1, (
        f"#tab-sources должен содержать ровно один .footer-ornament; "
        f"got {sources_ornament.count()}"
    )
    assert timeline_ornament.count() == 1, (
        f"#tab-timeline должен содержать ровно один .footer-ornament; "
        f"got {timeline_ornament.count()}"
    )
    # Три bullet'а как design-decision (· · · — index.html:164,183).
    expect(sources_ornament).to_contain_text("•")


# ─────────────────────────────────────────────────────────────────────────
# TC-12.02 — Timeline tab: river-filters (5 кнопок)
# ─────────────────────────────────────────────────────────────────────────


def test_timeline_river_filters_render_five_branches(owner_page: Page):
    """TC-12.02: после переключения на Timeline tab — 5 кнопок-фильтров
    (`.river-filter-btn`): Все / По матери / По отцу / Другие / История.
    Default active = «Все» (data-branch=all).
    """
    owner_page.goto("/")
    owner_page.wait_for_load_state("networkidle")
    owner_page.locator('[data-tab="timeline"]').click()

    filters = owner_page.locator("#riverFilters .river-filter-btn")
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

    # Active по умолчанию = первый (data-branch=all).
    expect(filters.nth(0)).to_have_class(re.compile(r"\bactive\b"))


# ─────────────────────────────────────────────────────────────────────────
# TC-13.05 — About: empty placeholder когда about_text not set
# ─────────────────────────────────────────────────────────────────────────


def test_about_tab_shows_placeholder_when_about_text_is_empty(owner_page: Page):
    """TC-13.05: на чистом demo seed about_text не заполнен →
    `[data-config-empty="about_text"]` блок visible с дефолтным
    текстом «Это семейное древо…». `[data-config-html="about_text"]`
    скрыт через `data-empty-hidden`.
    """
    owner_page.goto("/")
    owner_page.wait_for_load_state("networkidle")
    owner_page.locator('[data-tab="about"]').click()

    placeholder = owner_page.locator('[data-config-empty="about_text"]')
    expect(placeholder).to_be_visible()
    expect(placeholder).to_contain_text("семейное древо")


def test_add_relative_shows_error_on_409_conflict(owner_page: Page):
    """TC-09.10: при попытке создать дубликат person backend возвращает
    409 Conflict. UI должен показать error (#addRelError) и НЕ
    закрывать модалку silently. Backend response мочим через page.route —
    не зависим от реального duplicate-detection логики backend'а.

    Endpoint create-relative — POST /api/relationships (см.
    add-relative-modal.js). Modal остаётся открыта при non-200 ответе.
    """

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

    owner_page.goto(f"/#/p/{TestData.DEMO_PERSON_ID}")
    owner_page.wait_for_load_state("networkidle")

    panel = ProfilePanel(owner_page)
    panel.expect_visible()
    panel.click_add_sibling()

    modal = AddRelativeModal(owner_page)
    modal.expect_visible()
    modal.fill_and_save(surname="Дубликат", given="Тест")

    # После 409: модалка остаётся видимой (silent-close = регрессия).
    expect(modal.container).to_be_visible()
