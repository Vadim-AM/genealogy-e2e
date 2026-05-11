"""Add-relative dedup — graph-aware suggestion (Фаза 1).

Сценарий бага: у A записаны родители Иван и Мария. К A добавляем сестру S
(без auto-parent). Открываем S → «+ родитель»: фронт **должен** проактивно
предложить уже-существующих parent'ов (Иван, Мария) — клик привязывает к S
без создания дубликата. Без suggestion юзер вводил «Иван Иванов» руками,
бэк создавал нового person'а с другим id, в графе появлялось два разных Ивана.

Сетап для всех тестов: используем demo-self person из seed-данных
(signup_via_api проставляет ему 2 demo-parent'ов — отца и мать). Этого
достаточно для главного flow; для variant-тестов добавляем дополнительные
persons через API.
"""

from __future__ import annotations

import httpx
import pytest
from playwright.sync_api import Page, expect

from tests.api_paths import API
from tests.messages import TestData
from tests.pages.person_editor import AddRelativeModal
from tests.pages.profile_panel import ProfilePanel
from tests.timeouts import TIMEOUTS


# ─────────────────────────────────────────────────────────────────────────
# Helpers (локальные, чтобы не плодить fixture'ы — переиспользуются только
# внутри этого файла)
# ─────────────────────────────────────────────────────────────────────────


def _people(api: httpx.Client) -> list[dict]:
    r = api.get(API.TREE)
    r.raise_for_status()
    return r.json()["people"]


def _relationships(api: httpx.Client) -> list[dict]:
    r = api.get(API.RELATIONSHIPS)
    r.raise_for_status()
    return r.json()


def _demo_parents_of_self(api: httpx.Client) -> dict[str, str]:
    """Returns {'m': father_id, 'f': mother_id} for demo-self."""
    people_by_id = {p["id"]: p for p in _people(api)}
    rels = _relationships(api)
    parent_rels = [
        r for r in rels
        if r["type"] == "parent" and r["person2_id"] == TestData.DEMO_PERSON_ID
    ]
    assert len(parent_rels) == 2, (
        f"expected demo-self to have 2 seeded parents; got {len(parent_rels)}: {parent_rels}"
    )
    result: dict[str, str] = {}
    for r in parent_rels:
        parent = people_by_id.get(r["person1_id"])
        assert parent, f"parent {r['person1_id']} not in tree"
        gender = parent.get("gender")
        assert gender in ("m", "f"), f"demo-parent {parent['id']} has invalid gender: {gender!r}"
        result[gender] = parent["id"]
    assert set(result) == {"m", "f"}, f"demo-self lacks one parent gender: {result}"
    return result


def _open_profile(page: Page, person_id: str) -> ProfilePanel:
    page.goto(f"/#/p/{person_id}")
    page.wait_for_load_state("networkidle")
    panel = ProfilePanel(page)
    panel.expect_visible()
    return panel


def _add_sibling_without_auto_parents(
    page: Page,
    *,
    surname: str,
    given: str,
    birth: str = "",
    gender: str | None = None,
) -> AddRelativeModal:
    """Open add-sibling modal, uncheck auto-parent чекбокс, fill, save, wait close."""
    panel = ProfilePanel(page)
    panel.click_add_sibling()

    modal = AddRelativeModal(page)
    modal.expect_visible()

    share_check = page.locator("#addRelSiblingShareParents")
    if share_check.count() > 0 and share_check.is_checked():
        share_check.uncheck()

    modal.fill_fio(surname=surname, given=given, birth=birth)
    if gender:
        modal.select_gender(gender)

    with page.expect_response("**/api/people**") as resp:
        modal.save()
    assert resp.value.ok, (
        f"POST /api/people failed: {resp.value.status} {resp.value.text()[:200]}"
    )
    expect(modal.overlay).not_to_be_visible()
    return modal


def _find_person_by_name(api: httpx.Client, *substrings: str) -> dict:
    """Find a person whose name contains ALL given substrings. Asserts uniqueness."""
    matches = [
        p for p in _people(api)
        if all(s in p["name"] for s in substrings)
    ]
    assert len(matches) == 1, (
        f"expected exactly 1 person matching {substrings!r}; got {len(matches)}: "
        f"{[p['name'] for p in matches]}"
    )
    return matches[0]


# ─────────────────────────────────────────────────────────────────────────
# Главный сценарий — закрытие бага
# ─────────────────────────────────────────────────────────────────────────


def test_sibling_parent_suggestion_prevents_duplicate(
    owner_page: Page, owner_user, tenant_client
):
    """Закрывает баг: при добавлении отца сёстре фронт предлагает уже
    записанного отца другой сестры (а не создаёт дубликата).

    Verification двойная — UI (suggestion-card видна и кликабельна) + API
    (нет нового person'а, у обеих сестёр один parent-edge на того же id).
    """
    api = tenant_client(owner_user)
    parents = _demo_parents_of_self(api)
    demo_father_id = parents["m"]

    people_before = _people(api)
    count_before = len(people_before)
    assert demo_father_id in {p["id"] for p in people_before}

    # 1. demo-self → add sibling без auto-parent (у Светланы 0 родителей)
    _open_profile(owner_page, TestData.DEMO_PERSON_ID)
    _add_sibling_without_auto_parents(
        owner_page,
        surname="Тестовая",
        given="Светлана",
        birth="15.06.1992",
        gender="f",
    )

    svetlana = _find_person_by_name(api, "Светлана", "Тестовая")

    # 2. Open Светлана → "+ родитель"
    panel = _open_profile(owner_page, svetlana["id"])
    panel.click_add_parent()

    modal = AddRelativeModal(owner_page)
    modal.expect_visible()

    # KEY-1: suggestion-card на demo-father должна быть видна
    modal.expect_suggestion_visible(demo_father_id)

    # KEY-2: клик на suggestion = POST /relationships (НЕ /people)
    with owner_page.expect_response("**/api/relationships**") as rel_resp:
        modal.click_suggestion(demo_father_id)
    assert rel_resp.value.ok, (
        f"POST /api/relationships failed: {rel_resp.value.status} "
        f"{rel_resp.value.text()[:200]}"
    )
    expect(modal.overlay).not_to_be_visible()

    # API assertion 1: ровно один новый person (Светлана), suggestion не создала второго
    people_after = _people(api)
    assert len(people_after) == count_before + 1, (
        f"unexpected new persons; before={count_before}, after={len(people_after)}"
    )

    # API assertion 2: оба ребёнка (demo-self, Светлана) ссылаются на ТОТ ЖЕ demo_father_id
    rels = _relationships(api)
    father_edges = {
        r["person2_id"]: r
        for r in rels
        if r["type"] == "parent" and r["person1_id"] == demo_father_id
    }
    assert TestData.DEMO_PERSON_ID in father_edges
    assert svetlana["id"] in father_edges
    # И нет «ivan-ivanov-2»-подобных дубликатов
    assert not any(p["id"].endswith("-2") for p in people_after), (
        f"found duplicate-suffix ids: {[p['id'] for p in people_after if p['id'].endswith('-2')]}"
    )


# ─────────────────────────────────────────────────────────────────────────
# Variants
# ─────────────────────────────────────────────────────────────────────────


def test_suggestion_filters_by_gender_for_mother_relationship(
    owner_page: Page, owner_user, tenant_client
):
    """Выбор пола `f` в форме → suggestion исключает demo-father (m) и
    показывает demo-mother (f)."""
    api = tenant_client(owner_user)
    parents = _demo_parents_of_self(api)

    # Add sibling без auto-parent
    _open_profile(owner_page, TestData.DEMO_PERSON_ID)
    _add_sibling_without_auto_parents(
        owner_page, surname="Тестовая", given="Светлана", gender="f"
    )

    svetlana = _find_person_by_name(api, "Светлана", "Тестовая")

    # Open Светлана → add parent
    panel = _open_profile(owner_page, svetlana["id"])
    panel.click_add_parent()
    modal = AddRelativeModal(owner_page)
    modal.expect_visible()

    # Selecting gender=f in the form → re-renders suggestion: только мать
    modal.select_gender("f")
    expect(modal.suggestion_card_by_id(parents["f"])).to_be_visible()
    expect(modal.suggestion_card_by_id(parents["m"])).to_have_count(0)

    # Switching to gender=m → re-render: только отец
    modal.select_gender("m")
    expect(modal.suggestion_card_by_id(parents["m"])).to_be_visible()
    expect(modal.suggestion_card_by_id(parents["f"])).to_have_count(0)


def test_no_suggestion_when_no_siblings(
    owner_page: Page, owner_user, tenant_client
):
    """У demo-self нет siblings (только parents) → suggestion-блока нет."""
    api = tenant_client(owner_user)
    # Sanity: demo-self does have parents (otherwise +parent кнопка скрыта)
    parents = _demo_parents_of_self(api)
    assert len(parents) == 2  # both genders present

    # У demo-self уже 2 parents → "+ parent" кнопка скрыта по RELATIVE_LIMITS.
    # Поэтому для этого теста используем одного из parents (e.g. demo-father)
    # — у него siblings ≠ 0 не гарантировано, но parents точно нет.
    father_id = parents["m"]
    panel = _open_profile(owner_page, father_id)
    panel.click_add_parent()
    modal = AddRelativeModal(owner_page)
    modal.expect_visible()

    # У demo-father в seed-данных НЕТ siblings → suggestion-block не рендерится
    modal.expect_no_suggestions()


def test_no_suggestion_when_siblings_have_no_parents(
    owner_page: Page, owner_user, tenant_client
):
    """Сценарий: создаём через API двух siblings с **нулём** parents (только
    sibling-rel между ними). Open A → add parent → suggestion пуст (нечего
    предлагать)."""
    api = tenant_client(owner_user)

    api.post(API.PEOPLE, json={
        "id": "lone_a", "name": "Одинокий Альфа",
        "surname": "Одинокий", "given_name": "Альфа",
        "gender": "m", "branch": "other", "status": "confirmed",
    }).raise_for_status()
    api.post(API.PEOPLE, json={
        "id": "lone_b", "name": "Одинокий Бета",
        "surname": "Одинокий", "given_name": "Бета",
        "gender": "m", "branch": "other", "status": "confirmed",
    }).raise_for_status()
    api.post(API.RELATIONSHIPS, json={
        "type": "sibling", "person1_id": "lone_a", "person2_id": "lone_b"
    }).raise_for_status()

    panel = _open_profile(owner_page, "lone_a")
    panel.click_add_parent()
    modal = AddRelativeModal(owner_page)
    modal.expect_visible()
    modal.expect_no_suggestions()


def test_no_suggestion_when_max_parents_already(
    owner_page: Page, owner_user, tenant_client
):
    """Если у currentPerson уже 2 parents — «+ parent» кнопка скрыта по
    RELATIVE_LIMITS. Negative-ассерт: панель не показывает кнопку.

    (Раньше я хотел проверить «модалка открыта, suggestion пуст» — но в UI
    кнопка +parent скрывается до открытия модалки, так что этот guard-rail
    лучше проверять на уровне профиля.)"""
    api = tenant_client(owner_user)
    _demo_parents_of_self(api)  # sanity

    panel = _open_profile(owner_page, TestData.DEMO_PERSON_ID)
    # +parent button locator (внутри ProfilePanel.add_relative_button)
    # должна отсутствовать или быть hidden у demo-self (2 parents already).
    from tests.messages import FamilyGroups, t
    parents_add_btn = panel.add_relative_button(t(FamilyGroups.PARENTS))
    expect(parents_add_btn).to_have_count(0)


# ─────────────────────────────────────────────────────────────────────────
# Negative / legit case
# ─────────────────────────────────────────────────────────────────────────


def test_user_ignores_suggestion_creates_new_person(
    owner_page: Page, owner_user, tenant_client
):
    """Юзер видит suggestion с demo-father, но **игнорирует** и заполняет форму
    руками («Прадед Антонович» — легитимный другой человек). Save → создан
    новый person, демо-отец остался у demo-self.

    Этот тест защищает от over-correction: suggestion ≠ принудительный merge,
    юзер всегда может создать нового человека.
    """
    api = tenant_client(owner_user)
    parents = _demo_parents_of_self(api)
    demo_father_id = parents["m"]

    # Add sibling без auto-parent
    _open_profile(owner_page, TestData.DEMO_PERSON_ID)
    _add_sibling_without_auto_parents(
        owner_page, surname="Тестовая", given="Светлана", gender="f"
    )
    svetlana = _find_person_by_name(api, "Светлана", "Тестовая")

    count_before_add_father = len(_people(api))

    # Open Светлана → add parent → SUGGESTION visible BUT юзер не кликает,
    # вводит ФИО руками и жмёт Save
    panel = _open_profile(owner_page, svetlana["id"])
    panel.click_add_parent()
    modal = AddRelativeModal(owner_page)
    modal.expect_visible()
    modal.expect_suggestion_visible(demo_father_id)

    modal.fill_fio(surname="Прадедов", given="Иннокентий", birth="01.01.1900")
    modal.select_gender("m")

    with owner_page.expect_response("**/api/people**") as resp:
        modal.save()
    assert resp.value.ok
    expect(modal.overlay).not_to_be_visible()

    # New legit person created → +1
    people_after = _people(api)
    assert len(people_after) == count_before_add_father + 1
    # demo-self's father unchanged
    rels = _relationships(api)
    self_fathers = [
        r["person1_id"] for r in rels
        if r["type"] == "parent" and r["person2_id"] == TestData.DEMO_PERSON_ID
    ]
    assert demo_father_id in self_fathers
    # Светлана's father = Иннокентий (новый), не demo-father
    sv_father_rels = [
        r for r in rels
        if r["type"] == "parent" and r["person2_id"] == svetlana["id"]
    ]
    assert len(sv_father_rels) == 1
    new_father_id = sv_father_rels[0]["person1_id"]
    assert new_father_id != demo_father_id
    new_father = next(p for p in people_after if p["id"] == new_father_id)
    assert "Иннокентий" in new_father["name"]


def test_suggestion_click_does_not_create_new_person(
    owner_page: Page, owner_user, tenant_client
):
    """Клик на suggestion-card НИКОГДА не дёргает POST /api/people.

    Regression-guard: следим за network'ом — между modal.expect_visible() и
    закрытием модалки видим только POST /relationships, ни одного /people.
    """
    api = tenant_client(owner_user)
    parents = _demo_parents_of_self(api)
    demo_father_id = parents["m"]

    _open_profile(owner_page, TestData.DEMO_PERSON_ID)
    _add_sibling_without_auto_parents(
        owner_page, surname="Тестовая", given="Светлана", gender="f"
    )
    svetlana = _find_person_by_name(api, "Светлана", "Тестовая")

    panel = _open_profile(owner_page, svetlana["id"])
    panel.click_add_parent()
    modal = AddRelativeModal(owner_page)
    modal.expect_visible()
    modal.expect_suggestion_visible(demo_father_id)

    # Логируем все исходящие POST'ы. expected_post_people_count = 0.
    posted_people: list[str] = []
    def _on_request(req):
        if req.method == "POST" and "/api/people" in req.url and "/api/people-" not in req.url:
            posted_people.append(req.url)

    owner_page.on("request", _on_request)
    try:
        with owner_page.expect_response("**/api/relationships**") as _:
            modal.click_suggestion(demo_father_id)
        expect(modal.overlay).not_to_be_visible()
    finally:
        owner_page.remove_listener("request", _on_request)

    assert posted_people == [], (
        f"expected ZERO POST /api/people on suggestion-click; got {posted_people}"
    )


# ─────────────────────────────────────────────────────────────────────────
# Cross-flow regression
# ─────────────────────────────────────────────────────────────────────────


def test_existing_sibling_auto_parent_checkbox_still_works(
    owner_page: Page, owner_user, tenant_client
):
    """Регрессия: чекбокс «Те же родители» при добавлении sibling (с auto-link)
    продолжает работать — наша Фаза 1 не сломала существующий flow.

    Добавляем sibling к demo-self с checked checkbox → ожидаем что новый
    sibling получает обоих demo-parents через parent-relationships.
    """
    api = tenant_client(owner_user)
    parents = _demo_parents_of_self(api)

    panel = _open_profile(owner_page, TestData.DEMO_PERSON_ID)
    panel.click_add_sibling()
    modal = AddRelativeModal(owner_page)
    modal.expect_visible()

    # Чекбокс ДОЛЖЕН быть checked by default — не трогаем
    share_check = owner_page.locator("#addRelSiblingShareParents")
    expect(share_check).to_be_checked()

    modal.fill_fio(surname="Тестовая", given="Брат", birth="01.01.1985")
    modal.select_gender("m")

    with owner_page.expect_response("**/api/people**") as resp:
        modal.save()
    assert resp.value.ok
    expect(modal.overlay).not_to_be_visible()

    brat = _find_person_by_name(api, "Брат", "Тестовая")
    rels = _relationships(api)
    brat_parents = {
        r["person1_id"] for r in rels
        if r["type"] == "parent" and r["person2_id"] == brat["id"]
    }
    assert parents["m"] in brat_parents, (
        f"auto-parent checkbox failed: father {parents['m']} not linked to brat. "
        f"Got parents: {brat_parents}"
    )
    assert parents["f"] in brat_parents, (
        f"auto-parent checkbox failed: mother {parents['f']} not linked to brat. "
        f"Got parents: {brat_parents}"
    )


# ─────────────────────────────────────────────────────────────────────────
# Sad path
# ─────────────────────────────────────────────────────────────────────────


def test_suggestion_click_shows_error_on_backend_422(
    owner_page: Page, owner_user, tenant_client
):
    """Если бэк возвращает 422 при попытке привязать suggestion (например,
    age-gap validation) — модалка остаётся открытой, error visible, граф
    не меняется. Юзер может закрыть и попробовать другой подход.

    Симулируем 422 через page.route интерцепцию POST /api/relationships.
    """
    api = tenant_client(owner_user)
    parents = _demo_parents_of_self(api)
    demo_father_id = parents["m"]

    _open_profile(owner_page, TestData.DEMO_PERSON_ID)
    _add_sibling_without_auto_parents(
        owner_page, surname="Тестовая", given="Светлана", gender="f"
    )
    svetlana = _find_person_by_name(api, "Светлана", "Тестовая")

    rels_before = _relationships(api)

    panel = _open_profile(owner_page, svetlana["id"])
    panel.click_add_parent()
    modal = AddRelativeModal(owner_page)
    modal.expect_visible()
    modal.expect_suggestion_visible(demo_father_id)

    # Перехватываем POST /api/relationships и возвращаем 422
    def _block_with_422(route):
        if route.request.method == "POST":
            route.fulfill(
                status=422,
                content_type="application/json",
                body='{"detail":"Возраст родителя должен превышать возраст ребёнка минимум на 14 лет"}',
            )
        else:
            route.continue_()

    owner_page.route("**/api/relationships*", _block_with_422)
    try:
        modal.click_suggestion(demo_father_id)
        # Модалка должна остаться открытой
        expect(modal.overlay).to_be_visible()
        expect(modal.error).to_be_visible()
        expect(modal.error).to_contain_text("Возраст родителя")
    finally:
        owner_page.unroute("**/api/relationships*")

    # Граф не должен был измениться
    rels_after = _relationships(api)
    assert len(rels_after) == len(rels_before), (
        f"relationships count changed despite 422; "
        f"before={len(rels_before)}, after={len(rels_after)}"
    )
