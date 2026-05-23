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

Was xfail until upstream commit `32d2a9a` (fix(profile): BUG-PROFILE-002 —
graph-aware suggestion в add-relative-modal).
"""

from __future__ import annotations

import allure
from playwright.sync_api import Page, expect

from tests.api_paths import API
from tests.helpers.tree.add_relative import add_sibling_without_auto_parents
from tests.helpers.tree.tree_api import (
    demo_parents_of_self,
    find_person_by_name,
    people,
    relationships,
)
from tests.helpers.tree.tree_navigation import open_profile
from tests.messages import AgeValidation, FamilyGroups, TestData, t
from tests.pages.person_editor import AddRelativeModal
from tests.pages.profile_panel import ProfilePanel


# ─────────────────────────────────────────────────────────────────────────
# Главный сценарий — закрытие бага
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Подсказка родителя для сестры предотвращает дубликат")
def test_sibling_parent_suggestion_prevents_duplicate(
    owner_page: Page, owner_user, tenant_client
):
    """Закрывает баг: при добавлении отца сёстре фронт предлагает уже
    записанного отца другой сестры (а не создаёт дубликата).

    Verification двойная — UI (suggestion-card видна и кликабельна) + API
    (нет нового person'а, у обеих сестёр один parent-edge на того же id).
    """
    api = tenant_client(owner_user)
    parents = demo_parents_of_self(api)
    demo_father_id = parents["m"]

    people_before = people(api)
    count_before = len(people_before)
    assert demo_father_id in {p["id"] for p in people_before}, \
        f"demo father {demo_father_id} not found in seed people"

    # 1. demo-self → add sibling без auto-parent (у Светланы 0 родителей)
    open_profile(owner_page, TestData.DEMO_PERSON_ID)
    add_sibling_without_auto_parents(
        owner_page,
        surname="Тестовая",
        given="Светлана",
        birth="15.06.1992",
        gender="f",
    )

    svetlana = find_person_by_name(api, "Светлана", "Тестовая")

    # 2. Open Светлана → "+ родитель"
    panel = open_profile(owner_page, svetlana["id"])
    panel.click_add_parent()

    modal = AddRelativeModal(owner_page)
    modal.expect_visible()

    # KEY-1: suggestion-card на demo-father должна быть видна
    modal.expect_suggestion_visible(demo_father_id)

    # KEY-2: клик на suggestion → link-mode (chip), Save → POST
    # /relationships (НЕ /people). FEATURE-PARENT-SEARCH-001 развела
    # выбор и применение: клик карточки больше не POST'ит немедленно.
    modal.click_suggestion(demo_father_id)
    modal.expect_linked_to(demo_father_id)
    with owner_page.expect_response(f"**{API.RELATIONSHIPS}**") as rel_resp:
        modal.btn_save.click()
    assert rel_resp.value.ok, (
        f"POST /api/relationships failed: {rel_resp.value.status} "
        f"{rel_resp.value.text()[:200]}"
    )
    expect(modal.overlay).not_to_be_visible()

    # API assertion 1: ровно один новый person (Светлана), suggestion не создала второго
    people_after = people(api)
    assert len(people_after) == count_before + 1, (
        f"unexpected new persons; before={count_before}, after={len(people_after)}"
    )

    # API assertion 2: оба ребёнка (demo-self, Светлана) ссылаются на ТОТ ЖЕ demo_father_id
    rels = relationships(api)
    father_edges = {
        r["person2_id"]: r
        for r in rels
        if r["type"] == "parent" and r["person1_id"] == demo_father_id
    }
    assert TestData.DEMO_PERSON_ID in father_edges, \
        f"demo-self missing from father's children: {sorted(father_edges)}"
    assert svetlana["id"] in father_edges, \
        f"Svetlana missing from father's children: {sorted(father_edges)}"
    # И нет «ivan-ivanov-2»-подобных дубликатов
    assert not any(p["id"].endswith("-2") for p in people_after), (
        f"found duplicate-suffix ids: {[p['id'] for p in people_after if p['id'].endswith('-2')]}"
    )


# ─────────────────────────────────────────────────────────────────────────
# Variants
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Подсказки родителей фильтруются по выбранному полу")
def test_suggestion_filters_by_gender_for_mother_relationship(
    owner_page: Page, owner_user, tenant_client
):
    """Выбор пола `f` в форме → suggestion исключает demo-father (m) и
    показывает demo-mother (f)."""
    api = tenant_client(owner_user)
    parents = demo_parents_of_self(api)

    # Add sibling без auto-parent
    open_profile(owner_page, TestData.DEMO_PERSON_ID)
    add_sibling_without_auto_parents(
        owner_page, surname="Тестовая", given="Светлана", gender="f"
    )

    svetlana = find_person_by_name(api, "Светлана", "Тестовая")

    # Open Светлана → add parent
    panel = open_profile(owner_page, svetlana["id"])
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


@allure.title("Подсказки отсутствуют у персоны без братьев и сестёр")
def test_no_suggestion_when_no_siblings(
    owner_page: Page, owner_user, tenant_client
):
    """Person без siblings → suggestion-блока нет даже если у системы
    есть кандидаты-родители «где-то ещё»: suggestion graph-aware и
    приходит **только** через siblings.

    Сетап: создаём чистого person'а через API — никаких parents,
    никаких siblings. Открываем его → «+ родитель» → ожидаем пустой slot.
    """
    api = tenant_client(owner_user)
    # demo-self уже имеет 2 demo-parents в seed — без siblings они
    # значимы как доступный пул кандидатов, но фронт обязан игнорировать
    # их (нет sibling-bridge → нет suggestion).
    demo_parents_of_self(api)  # sanity: seed правильно собрался

    r = api.post(
        API.PEOPLE,
        json={
            "name": "Одинокий Тестовый",
            "gender": "m",
            "birth": "1980",
            "branch": "other",
        },
    )
    r.raise_for_status()
    lonely_id = r.json()["id"]

    panel = open_profile(owner_page, lonely_id)
    panel.click_add_parent()
    modal = AddRelativeModal(owner_page)
    modal.expect_visible()

    modal.expect_no_suggestions()


@allure.title("Подсказки пусты когда у сиблингов нет родителей")
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

    panel = open_profile(owner_page, "lone_a")
    panel.click_add_parent()
    modal = AddRelativeModal(owner_page)
    modal.expect_visible()
    modal.expect_no_suggestions()


@allure.title("Кнопка '+ родитель' скрыта при достижении лимита в 2 родителя")
def test_no_suggestion_when_max_parents_already(
    owner_page: Page, owner_user, tenant_client
):
    """Если у currentPerson уже 2 parents — «+ parent» кнопка скрыта по
    RELATIVE_LIMITS. Negative-ассерт: панель не показывает кнопку.

    (Раньше я хотел проверить «модалка открыта, suggestion пуст» — но в UI
    кнопка +parent скрывается до открытия модалки, так что этот guard-rail
    лучше проверять на уровне профиля.)"""
    api = tenant_client(owner_user)
    demo_parents_of_self(api)  # sanity

    panel = open_profile(owner_page, TestData.DEMO_PERSON_ID)
    # +parent button locator (внутри ProfilePanel.add_relative_button)
    # должна отсутствовать или быть hidden у demo-self (2 parents already).
    parents_add_btn = panel.add_relative_button(t(FamilyGroups.PARENTS))
    expect(parents_add_btn).to_have_count(0)


# ─────────────────────────────────────────────────────────────────────────
# Negative / legit case
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Игнорирование подсказки создаёт нового человека вручную")
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
    parents = demo_parents_of_self(api)
    demo_father_id = parents["m"]

    # Add sibling без auto-parent
    open_profile(owner_page, TestData.DEMO_PERSON_ID)
    add_sibling_without_auto_parents(
        owner_page, surname="Тестовая", given="Светлана", gender="f"
    )
    svetlana = find_person_by_name(api, "Светлана", "Тестовая")

    count_before_add_father = len(people(api))

    # Open Светлана → add parent → SUGGESTION visible BUT юзер не кликает,
    # вводит ФИО руками и жмёт Save
    panel = open_profile(owner_page, svetlana["id"])
    panel.click_add_parent()
    modal = AddRelativeModal(owner_page)
    modal.expect_visible()
    modal.expect_suggestion_visible(demo_father_id)

    modal.fill_fio(surname="Прадедов", given="Иннокентий", birth="01.01.1900")
    modal.select_gender("m")

    with owner_page.expect_response(f"**{API.PEOPLE}**") as resp:
        modal.save()
    assert resp.value.ok, \
        f"POST /api/people failed: {resp.value.status} {resp.value.text()[:200]}"
    expect(modal.overlay).not_to_be_visible()

    # New legit person created → +1
    people_after = people(api)
    assert len(people_after) == count_before_add_father + 1, \
        f"expected +1 person; before={count_before_add_father}, after={len(people_after)}"
    # demo-self's father unchanged
    rels = relationships(api)
    self_fathers = [
        r["person1_id"] for r in rels
        if r["type"] == "parent" and r["person2_id"] == TestData.DEMO_PERSON_ID
    ]
    assert demo_father_id in self_fathers, \
        f"demo father {demo_father_id} lost from demo-self parents: {self_fathers}"
    # Светлана's father = Иннокентий (новый), не demo-father
    sv_father_rels = [
        r for r in rels
        if r["type"] == "parent" and r["person2_id"] == svetlana["id"]
    ]
    assert len(sv_father_rels) == 1, \
        f"Svetlana must have exactly 1 parent rel, got {len(sv_father_rels)}"
    new_father_id = sv_father_rels[0]["person1_id"]
    assert new_father_id != demo_father_id, \
        "new father must differ from demo father (user ignored suggestion)"
    new_father = next(p for p in people_after if p["id"] == new_father_id)
    assert "Иннокентий" in new_father["name"], \
        f"new father name missing 'Иннокентий': {new_father['name']!r}"


@allure.title("Клик по подсказке привязывает существующего, не создаёт нового")
def test_suggestion_click_does_not_create_new_person(
    owner_page: Page, owner_user, tenant_client
):
    """Клик на suggestion-card НИКОГДА не дёргает POST /api/people.

    Regression-guard: следим за network'ом — между modal.expect_visible() и
    закрытием модалки видим только POST /relationships, ни одного /people.
    """
    api = tenant_client(owner_user)
    parents = demo_parents_of_self(api)
    demo_father_id = parents["m"]

    open_profile(owner_page, TestData.DEMO_PERSON_ID)
    add_sibling_without_auto_parents(
        owner_page, surname="Тестовая", given="Светлана", gender="f"
    )
    svetlana = find_person_by_name(api, "Светлана", "Тестовая")

    panel = open_profile(owner_page, svetlana["id"])
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
        # click → link-mode, Save → POST /relationships (FEATURE-PARENT-SEARCH-001).
        modal.click_suggestion(demo_father_id)
        modal.expect_linked_to(demo_father_id)
        with owner_page.expect_response(f"**{API.RELATIONSHIPS}**") as _:
            modal.btn_save.click()
        expect(modal.overlay).not_to_be_visible()
    finally:
        owner_page.remove_listener("request", _on_request)

    assert posted_people == [], (
        f"expected ZERO POST /api/people on suggestion link-and-save; got {posted_people}"
    )


# ─────────────────────────────────────────────────────────────────────────
# Cross-flow regression
# ─────────────────────────────────────────────────────────────────────────


@allure.title("Чекбокс 'Те же родители' привязывает обоих родителей к сиблингу")
def test_existing_sibling_auto_parent_checkbox_still_works(
    owner_page: Page, owner_user, tenant_client
):
    """Регрессия: чекбокс «Те же родители» при добавлении sibling (с auto-link)
    продолжает работать — наша Фаза 1 не сломала существующий flow.

    Добавляем sibling к demo-self с checked checkbox → ожидаем что новый
    sibling получает обоих demo-parents через parent-relationships.
    """
    api = tenant_client(owner_user)
    parents = demo_parents_of_self(api)

    panel = open_profile(owner_page, TestData.DEMO_PERSON_ID)
    panel.click_add_sibling()
    modal = AddRelativeModal(owner_page)
    modal.expect_visible()

    # Чекбокс ДОЛЖЕН быть checked by default — не трогаем
    expect(modal.share_parents_input).to_be_checked()

    modal.fill_fio(surname="Тестовая", given="Брат", birth="01.01.1985")
    modal.select_gender("m")

    with owner_page.expect_response(f"**{API.PEOPLE}**") as resp:
        modal.save()
    assert resp.value.ok, \
        f"POST /api/people failed: {resp.value.status} {resp.value.text()[:200]}"
    expect(modal.overlay).not_to_be_visible()

    brat = find_person_by_name(api, "Брат", "Тестовая")
    rels = relationships(api)
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


@allure.title("Ошибка 422 при привязке подсказки оставляет модалку открытой")
def test_suggestion_click_shows_error_on_backend_422(
    owner_page: Page, owner_user, tenant_client
):
    """Если бэк возвращает 422 при попытке привязать suggestion (например,
    age-gap validation) — модалка остаётся открытой, error visible, граф
    не меняется. Юзер может закрыть и попробовать другой подход.

    Симулируем 422 через page.route интерцепцию POST /api/relationships.
    """
    api = tenant_client(owner_user)
    parents = demo_parents_of_self(api)
    demo_father_id = parents["m"]

    open_profile(owner_page, TestData.DEMO_PERSON_ID)
    add_sibling_without_auto_parents(
        owner_page, surname="Тестовая", given="Светлана", gender="f"
    )
    svetlana = find_person_by_name(api, "Светлана", "Тестовая")

    rels_before = relationships(api)

    panel = open_profile(owner_page, svetlana["id"])
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

    owner_page.route(f"**{API.RELATIONSHIPS}*", _block_with_422)
    try:
        # click → link-mode; POST уходит на Save (FEATURE-PARENT-SEARCH-001).
        modal.click_suggestion(demo_father_id)
        modal.expect_linked_to(demo_father_id)
        modal.btn_save.click()
        # Модалка должна остаться открытой, ошибка 422 — видимой.
        expect(modal.overlay).to_be_visible()
        expect(modal.error).to_be_visible()
        expect(modal.error).to_contain_text(t(AgeValidation.PARENT_AGE_KEYWORD))
    finally:
        owner_page.unroute(f"**{API.RELATIONSHIPS}*")

    # Граф не должен был измениться
    rels_after = relationships(api)
    assert len(rels_after) == len(rels_before), (
        f"relationships count changed despite 422; "
        f"before={len(rels_before)}, after={len(rels_after)}"
    )
