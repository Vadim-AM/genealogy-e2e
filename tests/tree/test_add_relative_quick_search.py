"""FEATURE-PARENT-SEARCH-001 — inline-autocomplete + linked-chip + state-machine.

Что закрывается фичей (upstream branch `feat/add-relative-link-existing`,
commits `f7c2931` Phase A + `c191e46` Phase B):

- На surname/given inputs модалки добавления родственника появляется
  inline-autocomplete dropdown со строками `role="option"
  data-action="pick-existing" data-person-id="..."`. Триггер — `surname +
  given >= 2` символов, debounce 150ms.
- Клик по строке (или ArrowDown+Enter) включает link-mode: появляется
  `.add-rel-linked-chip[data-linked-id="..."]` сверху формы, поля
  становятся `readonly`, кнопка `save-then-edit` скрывается, Save теперь
  идёт через `linkExistingRelative()` (только `POST /api/relationships`,
  без `POST /api/people` → без дубликата).
- `[data-action="unlink-existing"]` на чипе возвращает в create-mode
  (форма editable, поля остаются заполненными — типичный сценарий
  «нашёл похожего, но это другой»).

Был xfail до upstream commit `c56053b` (PR #160 merge:
«inline-autocomplete + linked-chip — FEATURE-PARENT-SEARCH-001»).
Post-merge wave-4b split (`2c27950`) разнёс monolith shell.js (1003
LOC) на 4 sub-модуля; данный контракт остался стабильным (drop
xfail после полного XPASS-прогона на upstream/dev `7dcd427`).
"""

from __future__ import annotations

import allure
from playwright.sync_api import Page, expect

from tests.helpers.tree.tree_api import people_count, seed_person
from tests.helpers.tree.tree_navigation import open_demo_self_profile
from tests.messages import LinkedChip, TestData, t
from tests.pages.person_editor import AddRelativeModal
from tests.pages.profile_panel import ProfilePanel


# ─────────────────────────────────────────────────────────────────────────
# Acceptance tests
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Привязка существующего сиблинга создаёт только связь, не персону")
def test_link_existing_sibling_creates_only_relationship(
    owner_page: Page, owner_user, tenant_client
):
    """Happy path: existing person → link as sibling → POST /api/relationships
    only (НЕ /api/people). People-count не вырос → дубликата нет.

    Sibling (а не parent) — потому что demo-self уже имеет 2 demo-parent'а,
    `+ parent`-кнопка под RELATIVE_LIMITS скрыта.
    """
    api = tenant_client(owner_user)
    existing_id = seed_person(
        api,
        pid="link-sib-existing",
        name="Прохор Иванов",
        surname="Иванов",
        given_name="Прохор",
    )
    count_before = people_count(api)

    panel = open_demo_self_profile(owner_page)
    panel.click_add_sibling()

    modal = AddRelativeModal(owner_page)
    modal.expect_visible()

    modal.search_existing(surname="Иван")
    modal.expect_dropdown_open()
    expect(modal.row_by_person_id(existing_id)).to_be_visible()

    modal.pick_existing(existing_id)
    modal.expect_linked_to(existing_id)
    modal.expect_field_readonly("surname")
    modal.expect_field_readonly("given_name")

    # Linked chip должен содержать lexicon-keywords из catalogue (а не
    # инлайн-строки — выживет copy-edit без правки теста).
    expect(modal.linked_chip).to_contain_text(t(LinkedChip.TITLE_KEYWORD))
    expect(modal.linked_chip).to_contain_text(t(LinkedChip.HINT_KEYWORD))

    # Перехватываем POST /api/relationships, утверждаем что НИ ОДНОГО
    # POST /api/people не было (фронт не должен дублировать).
    post_people_count = 0

    def _track(response):
        nonlocal post_people_count
        if response.request.method == "POST" and response.url.endswith(
            "/api/people"
        ):
            post_people_count += 1

    owner_page.on("response", _track)

    with owner_page.expect_response("**/api/relationships") as rel_info:
        modal.btn_save.click()
    rel_resp = rel_info.value
    assert rel_resp.ok, f"POST /api/relationships failed: {rel_resp.status}"
    assert rel_resp.request.method == "POST", (
        f"expected POST /api/relationships, got {rel_resp.request.method}"
    )

    expect(modal.overlay).not_to_be_visible()
    assert post_people_count == 0, (
        f"link-mode triggered POST /api/people {post_people_count}× — "
        "должен быть строго 0 (дубликата не должно быть)"
    )

    # Конечная проверка: число people в дереве НЕ выросло.
    assert people_count(api) == count_before, (
        "link-existing создал дубликат — people-count не должен меняться"
    )


@allure.title("Отвязка привязанной персоны возвращает форму в режим создания")
def test_unlink_existing_returns_to_create_mode(
    owner_page: Page, owner_user, tenant_client
):
    """`link → create` через «Отвязать»: после клика подсказки fields readonly
    → клик `[data-action="unlink-existing"]` → fields editable → правка
    surname → Save создаёт нового (POST /api/people + POST /api/relationships).
    """
    api = tenant_client(owner_user)
    existing_id = seed_person(
        api,
        pid="unlink-existing",
        name="Семён Семёнов",
        surname="Семёнов",
        given_name="Семён",
    )
    count_before = people_count(api)

    panel = open_demo_self_profile(owner_page)
    panel.click_add_sibling()

    modal = AddRelativeModal(owner_page)
    modal.expect_visible()
    modal.search_existing(surname="Семён")
    modal.expect_dropdown_open()
    modal.pick_existing(existing_id)
    modal.expect_linked_to(existing_id)
    modal.expect_field_readonly("surname")

    # Отвязать → проверяем что fields снова editable.
    modal.unlink_existing()
    modal.expect_not_linked()
    expect(modal.surname).not_to_have_attribute("readonly", "readonly")

    # Правим surname (оставляем prefilled given) → создаём нового.
    modal.surname.fill("Семёнов-Новый")

    with owner_page.expect_response(
        lambda r: "/api/people" in r.url and r.request.method == "POST"
    ) as person_info:
        modal.btn_save.click()
    assert person_info.value.ok, (
        f"POST /api/people failed: {person_info.value.status}"
    )

    expect(modal.overlay).not_to_be_visible()
    assert people_count(api) == count_before + 1, (
        "после unlink + правка + Save должен быть РОВНО один новый person"
    )


@allure.title("Автоподсказка исключает текущую персону из списка")
def test_dropdown_excludes_self(owner_page: Page, owner_user, tenant_client):
    """Self-exclusion (validate_self_loop): ввод подстроки имени самого
    currentPerson'а → его строки нет в dropdown'е, даже если он
    единственный кандидат-substring-match.

    owner_user.full_name по умолчанию `Тестовый Пользователь` (см.
    `signup_via_api`); subject в дереве — demo-self с тем же name.
    Ввод «Польз» — substring совпадает только с demo-self → dropdown
    должен либо не открыться, либо показать пустую выдачу.
    """
    panel = open_demo_self_profile(owner_page)
    panel.click_add_sibling()

    modal = AddRelativeModal(owner_page)
    modal.expect_visible()
    modal.search_existing(given="Польз")

    # Demo-self в dropdown'е быть не должен.
    expect(
        modal.row_by_person_id(TestData.DEMO_PERSON_ID)
    ).not_to_be_visible()


@allure.title("Стрелка вниз и Enter выбирают кандидата из автоподсказки")
def test_keyboard_arrow_down_enter_picks_first_candidate(
    owner_page: Page, owner_user, tenant_client
):
    """ArrowDown открывает dropdown (если есть запрос), ещё ArrowDown
    выделяет следующую строку, Enter — выбирает highlighted.

    Здесь упрощено: один кандидат → ArrowDown откроет dropdown с
    highlighted=0 → Enter сразу выбирает.
    """
    api = tenant_client(owner_user)
    existing_id = seed_person(
        api,
        pid="kbd-existing",
        name="Глеб Глебов",
        surname="Глебов",
        given_name="Глеб",
    )

    panel = open_demo_self_profile(owner_page)
    panel.click_add_sibling()

    modal = AddRelativeModal(owner_page)
    modal.expect_visible()
    modal.surname.fill("Глеб")
    modal.expect_dropdown_open()

    # Focus должен быть на surname после fill; ArrowDown навигирует,
    # Enter подтверждает.
    modal.surname.focus()
    owner_page.keyboard.press("ArrowDown")
    owner_page.keyboard.press("Enter")
    modal.expect_linked_to(existing_id)


@allure.title("Esc закрывает выпадающий список, но не модалку добавления")
def test_escape_closes_dropdown_keeps_modal(
    owner_page: Page, owner_user, tenant_client
):
    """Esc на открытом dropdown'е → dropdown закрыт; модалка остаётся
    открытой. Critical: trapFocus.onEscape повешен на саму модалку и
    закрыл бы её — но dropdown-keydown делает `stopPropagation`.
    """
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
    modal.surname.fill("Антон")
    modal.expect_dropdown_open()

    modal.surname.focus()
    owner_page.keyboard.press("Escape")

    modal.expect_dropdown_closed()
    # Модалка ещё открыта — Esc не всплыл до trapFocus.onEscape.
    expect(modal.container).to_be_visible()
