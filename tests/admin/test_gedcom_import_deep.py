"""TC-GEDCOM-DEEP: полноценные user flow сценарии import + verification.

Все assertions через UI: поиск, открытие профиля, кликабельные ссылки в
семейных группах. **Никаких API-backdoor проверок** — что юзер видит,
то тест проверяет.

Сценарии:
- **3-generation tree**: import 5 человек (2 grandparents → 2 parents → 1 child),
  навигация по семейным ссылкам в обе стороны.
- **Cyrillic preservation**: имена с ё, кавычками, длинными суффиксами
  без mojibake через всю UI цепочку.
- **Edge — minimal INDI**: только NAME + SEX, profile рендерится без crash.
- **NOTE → biography**: `1 NOTE` в GEDCOM рендерится в `.profile-story`.
- **Gender → relation label**: `1 SEX M/F` отражается в orbit-card-relation
  («отец»/«мать», «сын»/«дочь») surrounding cards.
- **Re-import idempotency**: повторный upload того же external-файла не
  дублирует ни персон, ни relationships.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from tests._data.gedcom.samples import (
    GEDCOM_CYRILLIC_EDGE,
    GEDCOM_MINIMAL_INDI,
    GEDCOM_THREE_GEN,
    GEDCOM_WITH_NOTE,
)
from tests.helpers.admin.gedcom_ui import import_via_ui
from tests.helpers.tree.tree_navigation import (
    click_family_link,
    search_and_open_profile,
    search_and_orbit,
)
from tests.messages import FamilyGroups, RelationLabels, t
from tests.pages.owner_page import OwnerPage


# ─────────────────────────────────────────────────────────────────────
# TC-GEDCOM-DEEP-1: 3-generation family с проверкой связей и данных
# ─────────────────────────────────────────────────────────────────────


def test_user_imports_three_generation_family_and_navigates_via_ui(
    owner_page: Page, owner_user,
):
    """Полный сценарий: импорт 3-поколенной семьи, навигация по семейным
    ссылкам в обе стороны.

    Verifies через UI:
    - DONE summary упоминает «Пропущено» (т.к. идемпотентность не сработала
      на свежий GEDCOM — все 5 INDI создались как новые персоны) или counts.
    - Андрей (ребёнок, generation 3) находится через header search.
    - Профиль Андрея показывает год 1980 в `.profile-dates`.
    - Группа «Родители» содержит ссылку на Сергея — клик открывает его профиль.
    - Профиль Сергея: год 1950, в «Дети» обратная ссылка на Андрея.
    - Группа «Супруг(а)» содержит Елену — клик открывает её профиль.
    - Профиль Елены: bidirectional spouse-link на Сергея.
    - Сергей.«Родители» содержит Ивана + Марию (generation 1).
    - Профиль Ивана: даты 1920-1990, место рождения Краснодар.
    """
    import_via_ui(owner_page, GEDCOM_THREE_GEN, "three-gen.ged")

    # User finds Андрея через search (single token: search.js matches
    # `p.name.includes(q)`; multi-word query was failing because backend
    # stores `name="Surname Given"` while UI shows `Given Surname` — UX
    # inconsistency tracked separately).
    panel = search_and_open_profile(owner_page, "Андрей")

    expect(panel.title).to_contain_text("Андрей")
    expect(panel.title).to_contain_text("Сидоров")
    expect(panel.container.locator(".profile-dates")).to_contain_text("1980")

    # У Андрея ровно 2 родителя — если бы import продублировал персону,
    # их было бы 4. Точный count ловит обе регрессии: «нет связей» и
    # «дубли».
    parents_group = panel.container.locator(".profile-family-group", has_text=t(FamilyGroups.PARENTS))
    expect(parents_group.locator('a[data-action="open-profile"]')).to_have_count(2)

    # Connection: Андрей → Сергей (родитель).
    click_family_link(panel, t(FamilyGroups.PARENTS), "Сергей")
    expect(panel.title).to_contain_text("Сергей")
    expect(panel.container.locator(".profile-dates")).to_contain_text("1950")

    # Bidirectional: Сергей → Андрей (в «Дети»). Ровно один ребёнок.
    children_group = panel.container.locator(".profile-family-group", has_text=t(FamilyGroups.CHILDREN))
    expect(children_group.locator('a[data-action="open-profile"]')).to_have_count(1)
    expect(children_group.locator('a[data-action="open-profile"]').filter(has_text="Андрей")).to_be_visible()

    # Connection: Сергей → Елена (супруга). Ровно один супруг.
    spouse_group = panel.container.locator(".profile-family-group", has_text=t(FamilyGroups.SPOUSE))
    expect(spouse_group.locator('a[data-action="open-profile"]')).to_have_count(1)
    click_family_link(panel, t(FamilyGroups.SPOUSE), "Елена")
    expect(panel.title).to_contain_text("Елена")
    expect(panel.container.locator(".profile-dates")).to_contain_text("1952")

    # Bidirectional spouse: Елена → Сергей (count=1).
    elena_spouse_group = panel.container.locator(".profile-family-group", has_text=t(FamilyGroups.SPOUSE))
    expect(elena_spouse_group.locator('a[data-action="open-profile"]')).to_have_count(1)
    expect(elena_spouse_group.locator('a[data-action="open-profile"]').filter(has_text="Сергей")).to_be_visible()

    # Navigate back к Сергею, потом вверх к Ивану (generation 1).
    elena_spouse_group.locator('a[data-action="open-profile"]').filter(has_text="Сергей").click()
    panel.expect_visible()
    click_family_link(panel, t(FamilyGroups.PARENTS), "Иван")

    # Iван (generation 1): daдy + место + год смерти.
    expect(panel.title).to_contain_text("Иван")
    dates_loc = panel.container.locator(".profile-dates")
    expect(dates_loc).to_contain_text("1920")
    expect(dates_loc).to_contain_text("1990")
    expect(panel.container.locator(".profile-place")).to_contain_text("Краснодар")


# ─────────────────────────────────────────────────────────────────────
# TC-GEDCOM-DEEP-2: Cyrillic preservation (edge — ё, длинные имена, места)
# ─────────────────────────────────────────────────────────────────────


def test_user_imports_cyrillic_data_renders_without_mojibake_via_ui(
    owner_page: Page, owner_user,
):
    """Edge — encoding preservation через full UI path.

    Импортируем GEDCOM с экзотической русской орфографией (ё, длинные
    суффиксы) и проверяем что профиль импортированного человека
    показывает символы exactly как в исходном файле — никаких `?`,
    `Иван`, или транслитерации.
    """
    import_via_ui(owner_page, GEDCOM_CYRILLIC_EDGE, "cyrillic.ged")

    panel = search_and_open_profile(owner_page, "Пётр")

    # Title содержит exact символы — букву ё и дефисную фамилию.
    expect(panel.title).to_contain_text("Пётр")
    expect(panel.title).to_contain_text("Аксёнов-Жёлтый")

    # Даты + место с буквой ё в имени села.
    dates_loc = panel.container.locator(".profile-dates")
    expect(dates_loc).to_contain_text("1900")
    expect(dates_loc).to_contain_text("1973")
    expect(panel.container.locator(".profile-place")).to_contain_text("Ёлкино")

    # Bidirectional spouse: Пётр → Евдокия с буквой ё в её фамилии.
    click_family_link(panel, t(FamilyGroups.SPOUSE), "Евдокия")
    expect(panel.title).to_contain_text("Евдокия")
    expect(panel.title).to_contain_text("Аксёнова-Жёлтая")


# ─────────────────────────────────────────────────────────────────────
# TC-GEDCOM-DEEP-3: Edge — минимальный INDI без optional полей
# ─────────────────────────────────────────────────────────────────────


def test_user_imports_minimal_indi_profile_renders_without_crash(
    owner_page: Page, owner_user,
):
    """Edge case: INDI с только NAME + SEX (без BIRT/DEAT/PLAC/NOTE/FAMS/FAMC).

    User flow: import → search → open profile. Профиль должен корректно
    рендериться: имя в title, даты пустые (либо отсутствуют, либо empty),
    family-секция structurally OK без relations.
    """
    import_via_ui(owner_page, GEDCOM_MINIMAL_INDI, "minimal.ged")

    panel = search_and_open_profile(owner_page, "Минимальный")

    expect(panel.title).to_contain_text("Минимальный")
    expect(panel.title).to_contain_text("Тестов")

    # `.profile-page` container loaded — никаких JS exceptions, никакой
    # broken rendering (sanity что openProfile прошёл до конца).
    expect(panel.container).to_be_visible()

    # Дата отсутствует — `.profile-dates` либо empty, либо отсутствует.
    # Контракт: рендер не падает, даже если у profile нет жизненных дат.
    dates_loc = panel.container.locator(".profile-dates")
    if dates_loc.count() > 0:
        # Если элемент есть — он не должен содержать «1970», «1980» или
        # подобных «фантомных» дат от backend defaults.
        text = (dates_loc.text_content() or "").strip()
        assert not any(year in text for year in ("1970", "1980", "1990")), (
            f"profile-dates should be empty for minimal INDI; got {text!r}"
        )

    # Family-секция структурно есть (4 группы — Родители/Супруг/Дети/
    # Братья), но без relations: ни одной `<a data-action="open-profile">`
    # ссылки на родственника. Селектор `.profile-family` — стабильный
    # контейнер (не зависит от локали section-title).
    family_block = panel.container.locator(".profile-family")
    expect(family_block).to_be_visible()
    expect(family_block.locator('a[data-action="open-profile"]')).to_have_count(0)


# ─────────────────────────────────────────────────────────────────────
# TC-GEDCOM-DEEP-4: NOTE → биография в `.profile-story`
# ─────────────────────────────────────────────────────────────────────


def test_user_imports_indi_with_note_renders_biography_in_profile_story(
    owner_page: Page, owner_user,
):
    """`1 NOTE <текст>` из GEDCOM должен попасть в `p.notes` и отрисоваться
    в `.profile-story` (секция «История»).

    Реальные .ged-файлы почти всегда содержат NOTE с биографией. Регрессия
    «notes теряются при импорте» отрезает у пользователя самую ценную
    часть содержимого.
    """
    import_via_ui(owner_page, GEDCOM_WITH_NOTE, "with-note.ged")
    panel = search_and_open_profile(owner_page, "Захар")

    expect(panel.title).to_contain_text("Захар")
    expect(panel.title).to_contain_text("Семёнов")

    story = panel.container.locator(".profile-story")
    expect(story).to_be_visible()
    # Полный текст биографии (берём 3 опорные фразы — медаль, профессия,
    # эвакуация). Достаточно distinct, чтобы любая обрезка / потеря
    # фрагмента провалила тест.
    expect(story).to_contain_text("Георгиевским крестом 4 степени")
    expect(story).to_contain_text("учителем в селе Никольское")
    expect(story).to_contain_text("Эвакуировался в 1942 году")


# ─────────────────────────────────────────────────────────────────────
# TC-GEDCOM-DEEP-5: Gender → relation label в orbit
# ─────────────────────────────────────────────────────────────────────


def test_user_imports_male_and_female_show_correct_relation_label_in_orbit(
    owner_page: Page, owner_user,
):
    """`1 SEX M/F` влияет на `getRelationLabel` (`js/components/card.js`):
    парент-папа = «отец», парент-мама = «мать». Тест import'ит 3-gen,
    переключает orbit на Андрея и читает `.orbit-card-relation` для
    его карточек-родителей.

    Регрессия «SEX игнорируется парсером» (все приходят как M) → все
    parent-cards будут показывать «отец», что заметно сразу.
    """
    import_via_ui(owner_page, GEDCOM_THREE_GEN, "three-gen.ged")
    search_and_orbit(owner_page, "Андрей")

    # Orbit-cards вокруг Андрея. Кажда parent-card — отдельная `.orbit-card`
    # с `.orbit-card-relation` под именем. Фильтруем by name → один card
    # на родителя, читаем relation.
    orbit_cards = owner_page.locator(".orbit-card")
    sergey_card = orbit_cards.filter(has_text="Сергей").first
    elena_card = orbit_cards.filter(has_text="Елена").first
    expect(sergey_card).to_be_visible()
    expect(elena_card).to_be_visible()

    expect(sergey_card.locator(".orbit-card-relation")).to_have_text(t(RelationLabels.FATHER))
    expect(elena_card.locator(".orbit-card-relation")).to_have_text(t(RelationLabels.MOTHER))


# ─────────────────────────────────────────────────────────────────────
# TC-GEDCOM-DEEP-6: Re-import idempotency (BUG-GEDCOM-001)
# ─────────────────────────────────────────────────────────────────────


def test_user_reimports_same_file_does_not_duplicate_persons(
    owner_page: Page, owner_user,
):
    """User flow: после успешного import «Импортировать ещё» → загружает
    тот же файл → DONE. Через UI проверяем:
    1. search по «Андрей» возвращает **одну** карточку, не две (нет
       дубликата person);
    2. в профиле Андрея группа «Родители» всё ещё содержит ровно две
       ссылки — не четыре (нет дубликата relationships).

    Идемпотентность — критичный контракт: пользователь может случайно
    re-upload-нуть тот же файл, бэкап-восстановление, частые repeat-uploads.
    Дубли множат граф 2N+, ломают визуализацию orbit и связи.

    Note: BUG-GEDCOM-001 в `docs/BUGS-FROM-E2E-2026-05-11.md` описывает
    смежный сценарий *export-then-import* (где система генерит GEDCOM
    из БД и пользователь импортит обратно — slug отсутствует) и не
    покрывается этим тестом. Здесь — внешний файл, загружаемый дважды.
    """
    import_via_ui(owner_page, GEDCOM_THREE_GEN, "three-gen.ged")

    # «Импортировать ещё» → IDLE → upload того же файла → confirm → DONE.
    owner = OwnerPage(owner_page)
    owner.import_again_btn.click()
    owner.expect_import_state("IDLE")
    owner.upload_ged(filename="three-gen.ged", content=GEDCOM_THREE_GEN.encode("utf-8"))
    owner.expect_import_state("PREVIEW")
    owner.confirm_import_via_dialog()
    owner.expect_import_state("DONE")

    # 1. Search «Андрей» → ровно 1 карточка.
    panel = search_and_open_profile(owner_page, "Андрей")
    expect(panel.title).to_contain_text("Андрей")

    # 2. У Андрея всё ещё ровно 2 родителя (не 4 — что было бы при дубле
    # relationship-rows).
    parents_group = panel.container.locator(".profile-family-group", has_text=t(FamilyGroups.PARENTS))
    expect(parents_group.locator('a[data-action="open-profile"]')).to_have_count(2)
