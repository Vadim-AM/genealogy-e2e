"""FEATURE-PARENT-SEARCH-001: «быстрый поиск» existing person в add-relative-modal.

Текущая graph-aware dedup (Фаза 1) предлагает кандидата-родителя **только**
если у current-person есть sibling с уже-привязанным parent'ом. Большой
пул сценариев это не покрывает:

- person без siblings (одинокий subject в дереве) хочет привязать дедушку,
  записанного отдельно в другой ветке.
- person с siblings, но желаемый parent не привязан ни к одному из них
  (например, добавили только мать → ищем отца, который записан в третьем
  поколении сбоку).
- юзер начинает с импорта 5 INDI из GEDCOM, потом manually добавляет
  6-го — должен иметь возможность привязать его к existing вместо
  создания дубля.

Решение: в add-relative-modal добавить input для поиска existing person'а
по name (autocomplete), и кнопку «Привязать» — выбор → POST /relationships,
никакого нового person'а.

Тест в xfail до реализации фичи. После релиза:
1. Снять `pytestmark`.
2. Уточнить селекторы под актуальный markup, если они отличаются от
   предположенных ниже.

Selectors-предположения (документация для разработчика фичи):
- `#addRelExistingSearch` — text input для name query (placeholder типа
  «Найти существующего человека»).
- `[data-action="pick-existing"][data-person-id="..."]` — карточка
  результата, клик = ссылка на existing.
- `[data-existing-results]` — контейнер списка результатов.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.api_paths import API
from tests.pages.person_editor import AddRelativeModal
from tests.pages.profile_panel import ProfilePanel


pytestmark = pytest.mark.xfail(
    strict=False,
    reason=(
        "FEATURE-PARENT-SEARCH-001: search-input для existing persons в "
        "add-relative-modal не реализован. Текущий dedup graph-aware "
        "(suggestion от siblings) не покрывает person'ов без siblings. "
        "Снять marker когда фича приедет в add-relative-modal.js."
    ),
)


def _open_profile(page: Page, person_id: str) -> ProfilePanel:
    """Navigate к profile через `/#/p/{id}` — full reload, чтобы init.js
    re-bound DATA cache."""
    page.goto("/")
    page.wait_for_load_state("domcontentloaded")
    page.goto(f"/#/p/{person_id}")
    page.wait_for_load_state("domcontentloaded")
    panel = ProfilePanel(page)
    panel.expect_visible()
    return panel


def test_user_links_existing_parent_via_modal_quick_search(
    owner_page: Page, owner_user, tenant_client,
):
    """User flow: одинокий person + существующий-в-БД отец (не sibling-bridged).
    В модалке «+ родитель» ввод его имени → click пиктограмму выбора →
    POST /relationships без создания дубликата.

    Acceptance через UI:
    - Search-input виден в modal.
    - Type → появляется результат-карточка с именем кандидата.
    - Click → modal закрывается, новый person НЕ создан, parent привязан.
    """
    api = tenant_client(owner_user)

    # Существующий-в-БД отец, записан independently (не привязан ни к кому).
    r = api.post(
        API.PEOPLE,
        json={
            "name": "Богданов Аркадий",
            "gender": "m",
            "birth": "1935",
            "branch": "other",
        },
    )
    r.raise_for_status()
    father_id = r.json()["id"]

    # Subject — одинокий, без parents и siblings.
    r2 = api.post(
        API.PEOPLE,
        json={
            "name": "Богданов Тимофей",
            "gender": "m",
            "birth": "1965",
            "branch": "other",
        },
    )
    r2.raise_for_status()
    subject_id = r2.json()["id"]

    people_count_before = len(api.get(API.TREE).json()["people"])

    # Open subject → «+ родитель».
    panel = _open_profile(owner_page, subject_id)
    panel.click_add_parent()
    modal = AddRelativeModal(owner_page)
    modal.expect_visible()

    # FEATURE: search-input по existing persons.
    search_input = modal.container.locator("#addRelExistingSearch")
    expect(search_input).to_be_visible()

    search_input.fill("Аркадий")

    # Result-card видна, attached на known id.
    result = modal.container.locator(
        f'[data-action="pick-existing"][data-person-id="{father_id}"]'
    )
    expect(result).to_be_visible()

    # Click → POST /relationships (НЕ /people).
    with owner_page.expect_response(f"**{API.RELATIONSHIPS}**") as rel_resp:
        result.click()
    assert rel_resp.value.ok, (
        f"POST /api/relationships failed: {rel_resp.value.status} "
        f"{rel_resp.value.text()[:200]}"
    )
    expect(modal.overlay).not_to_be_visible()

    # Новый person не создан — только link.
    people_after = api.get(API.TREE).json()["people"]
    assert len(people_after) == people_count_before, (
        f"unexpected new persons; before={people_count_before}, "
        f"after={len(people_after)}"
    )

    # Subject получил parent = известный Аркадий.
    rels = api.get(API.RELATIONSHIPS).json()
    parent_edges = [
        r for r in rels
        if r["type"] == "parent"
        and r["person2_id"] == subject_id
        and r["person1_id"] == father_id
    ]
    assert len(parent_edges) == 1, (
        f"expected exactly 1 parent edge subject→Аркадий; got {parent_edges}"
    )


def test_quick_search_filters_by_relation_gender_constraint(
    owner_page: Page, owner_user, tenant_client,
):
    """Search-input для «+ родитель» должен фильтровать по требуемому полу:
    если в модалке выбран gender='f' (мать), кандидаты-мужчины не показываются.

    Это эквивалент существующего gender-фильтра для suggestion-блока, но
    для search-input.
    """
    api = tenant_client(owner_user)

    api.post(
        API.PEOPLE,
        json={"name": "Богданов Аркадий", "gender": "m", "birth": "1935", "branch": "other"},
    ).raise_for_status()
    mother_resp = api.post(
        API.PEOPLE,
        json={"name": "Богданова Мария", "gender": "f", "birth": "1937", "branch": "other"},
    )
    mother_resp.raise_for_status()
    mother_id = mother_resp.json()["id"]

    subject_resp = api.post(
        API.PEOPLE,
        json={"name": "Богданов Тимофей", "gender": "m", "birth": "1965", "branch": "other"},
    )
    subject_resp.raise_for_status()
    subject_id = subject_resp.json()["id"]

    panel = _open_profile(owner_page, subject_id)
    panel.click_add_parent()
    modal = AddRelativeModal(owner_page)
    modal.expect_visible()
    modal.select_gender("f")

    modal.container.locator("#addRelExistingSearch").fill("Богданов")

    # Мать видна (gender match).
    mother_card = modal.container.locator(
        f'[data-action="pick-existing"][data-person-id="{mother_id}"]'
    )
    expect(mother_card).to_be_visible()

    # Аркадий (мужчина) — отфильтрован.
    male_cards = modal.container.locator(
        '[data-action="pick-existing"]'
    ).filter(has_text="Аркадий")
    expect(male_cards).to_have_count(0)
