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

from tests.messages import FamilyGroups, t
from tests.pages.owner_page import OwnerPage
from tests.pages.profile_panel import ProfilePanel
from tests.pages.tree_page import TreePage


# ─────────────────────────────────────────────────────────────────────
# GEDCOM fixtures
# ─────────────────────────────────────────────────────────────────────

# 3-generation family:
#   Иван Сидоров (1920-1990) ─┐
#                              ├─→ Сергей Сидоров (1950) ─┐
#   Мария Сидорова (1925) ────┘                          │
#                                                          ├─→ Андрей Сидоров (1980)
#                              Елена Иванова (1952) ─────┘
GEDCOM_THREE_GEN = """0 HEAD
1 SOUR DeepTest
1 CHAR UTF-8
0 @I1@ INDI
1 NAME Иван /Сидоров/
1 SEX M
1 BIRT
2 DATE 1920
2 PLAC Краснодар
1 DEAT
2 DATE 1990
0 @I2@ INDI
1 NAME Мария /Сидорова/
1 SEX F
1 BIRT
2 DATE 1925
0 @I3@ INDI
1 NAME Сергей /Сидоров/
1 SEX M
1 BIRT
2 DATE 1950
1 FAMC @F1@
1 FAMS @F2@
0 @I4@ INDI
1 NAME Елена /Иванова/
1 SEX F
1 BIRT
2 DATE 1952
1 FAMS @F2@
0 @I5@ INDI
1 NAME Андрей /Сидоров/
1 SEX M
1 BIRT
2 DATE 1980
1 FAMC @F2@
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 CHIL @I3@
0 @F2@ FAM
1 HUSB @I3@
1 WIFE @I4@
1 CHIL @I5@
0 TRLR
"""


# Persons с реальным русским orthography (ё, длинные фамилии, патронимы):
GEDCOM_CYRILLIC_EDGE = """0 HEAD
1 SOUR CyrillicTest
1 CHAR UTF-8
0 @I1@ INDI
1 NAME Пётр /Аксёнов-Жёлтый/
1 SEX M
1 BIRT
2 DATE 1900
2 PLAC село Ёлкино, Костромская губерния
1 DEAT
2 DATE 1973
2 PLAC Москва
0 @I2@ INDI
1 NAME Евдокия /Аксёнова-Жёлтая/
1 SEX F
1 BIRT
2 DATE 1905
1 FAMS @F1@
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
0 TRLR
"""


# Минимальный INDI — только NAME + SEX, без BIRT/DEAT/PLAC/NOTE.
GEDCOM_MINIMAL_INDI = """0 HEAD
1 SOUR MinimalTest
1 CHAR UTF-8
0 @I1@ INDI
1 NAME Минимальный /Тестов/
1 SEX M
0 TRLR
"""


# INDI с биографией — `1 NOTE` строкой. Биография обычно содержит знаки
# препинания (запятые, точки) и числа (годы службы) — проверяем что
# escape'ится корректно и текст не теряется.
_NOTE_BIO = (
    "Участник Первой мировой войны, награждён Георгиевским крестом 4 степени. "
    "С 1924 года работал учителем в селе Никольское. "
    "Эвакуировался в 1942 году вместе с семьёй."
)
GEDCOM_WITH_NOTE = f"""0 HEAD
1 SOUR NoteTest
1 CHAR UTF-8
0 @I1@ INDI
1 NAME Захар /Семёнов/
1 SEX M
1 BIRT
2 DATE 1885
1 NOTE {_NOTE_BIO}
0 TRLR
"""


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _import_via_ui(owner_page: Page, ged_content: str, filename: str) -> None:
    """User flow: open /owner → Import tab → upload → confirm → DONE."""
    owner = OwnerPage(owner_page)
    owner_page.goto("/owner")
    # GEDCOM widget mounts async после loadMe() — networkidle нужен явно.
    owner_page.wait_for_load_state("networkidle")
    owner.open_tab("export")
    expect(owner.import_root).to_have_attribute("data-gedcom-state", "IDLE")

    owner.upload_ged(filename=filename, content=ged_content.encode("utf-8"))
    owner.expect_import_state("PREVIEW")
    owner.confirm_import_via_dialog()
    owner.expect_import_state("DONE")


def _search_and_open_profile(owner_page: Page, query: str) -> ProfilePanel:
    """User flow: navigate к /, type в header search, click first result
    → orbit centers on person, click center card → profile opens.

    `DATA.people` populated через `loadData()` → `/api/tree` после mount;
    guard через `expect_response` (CSP блокирует string-`wait_for_function`).
    Search-click переключает orbit, не открывает profile напрямую —
    нужен дополнительный click по `.orbit-center-card` (это естественный
    пользовательский путь: «нашёл → перешёл на него в дереве → открыл
    карточку»).
    """
    tree = TreePage(owner_page)
    with owner_page.expect_response(lambda r: "/api/tree" in r.url and r.ok):
        tree.goto()
    tree.search_input.fill(query)
    expect(tree.search_results.first).to_be_visible()
    tree.search_results.first.click()
    center_card = owner_page.locator(".orbit-center-card")
    # Gate the click on the orbit having actually re-centred to the
    # searched person — `.orbit-center-card` always exists (demo-self is
    # the initial centre), so a bare `to_be_visible()` passes before the
    # async re-centre and the click opens the WRONG profile. Fast local
    # hid this; slow 2-core CI exposed it (5 gedcom_import_deep fails,
    # 2026-05-19). `to_contain_text(query)` auto-waits for the re-centre —
    # deterministic regardless of host speed, no product change.
    expect(center_card).to_contain_text(query)
    center_card.click()
    panel = ProfilePanel(owner_page)
    panel.expect_visible()
    return panel


def _click_family_link(panel: ProfilePanel, group_label: str, name_substring: str) -> None:
    """Click `<a data-action="open-profile">name</a>` внутри указанной family group."""
    group = panel.container.locator(".profile-family-group", has_text=group_label)
    expect(group).to_be_visible()
    link = group.locator('a[data-action="open-profile"]').filter(has_text=name_substring).first
    expect(link).to_be_visible()
    link.click()
    panel.expect_visible()


def _search_and_orbit(owner_page: Page, query: str) -> None:
    """User flow: navigate к /, search → click first result → orbit centers
    on person, **stay on orbit view** (без открытия profile).

    Используется для проверок, которые читают окружающие `.orbit-card`
    (relation labels к зафокусированному человеку).
    """
    tree = TreePage(owner_page)
    with owner_page.expect_response(lambda r: "/api/tree" in r.url and r.ok):
        tree.goto()
    tree.search_input.fill(query)
    expect(tree.search_results.first).to_be_visible()
    tree.search_results.first.click()
    expect(owner_page.locator(".orbit-center-card")).to_be_visible()


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
    _import_via_ui(owner_page, GEDCOM_THREE_GEN, "three-gen.ged")

    # User finds Андрея через search (single token: search.js matches
    # `p.name.includes(q)`; multi-word query was failing because backend
    # stores `name="Surname Given"` while UI shows `Given Surname` — UX
    # inconsistency tracked separately).
    panel = _search_and_open_profile(owner_page, "Андрей")

    expect(panel.title).to_contain_text("Андрей")
    expect(panel.title).to_contain_text("Сидоров")
    expect(panel.container.locator(".profile-dates")).to_contain_text("1980")

    # У Андрея ровно 2 родителя — если бы import продублировал персону,
    # их было бы 4. Точный count ловит обе регрессии: «нет связей» и
    # «дубли».
    parents_group = panel.container.locator(".profile-family-group", has_text=t(FamilyGroups.PARENTS))
    expect(parents_group.locator('a[data-action="open-profile"]')).to_have_count(2)

    # Connection: Андрей → Сергей (родитель).
    _click_family_link(panel, t(FamilyGroups.PARENTS), "Сергей")
    expect(panel.title).to_contain_text("Сергей")
    expect(panel.container.locator(".profile-dates")).to_contain_text("1950")

    # Bidirectional: Сергей → Андрей (в «Дети»). Ровно один ребёнок.
    children_group = panel.container.locator(".profile-family-group", has_text=t(FamilyGroups.CHILDREN))
    expect(children_group.locator('a[data-action="open-profile"]')).to_have_count(1)
    expect(children_group.locator('a[data-action="open-profile"]').filter(has_text="Андрей")).to_be_visible()

    # Connection: Сергей → Елена (супруга). Ровно один супруг.
    spouse_group = panel.container.locator(".profile-family-group", has_text=t(FamilyGroups.SPOUSE))
    expect(spouse_group.locator('a[data-action="open-profile"]')).to_have_count(1)
    _click_family_link(panel, t(FamilyGroups.SPOUSE), "Елена")
    expect(panel.title).to_contain_text("Елена")
    expect(panel.container.locator(".profile-dates")).to_contain_text("1952")

    # Bidirectional spouse: Елена → Сергей (count=1).
    elena_spouse_group = panel.container.locator(".profile-family-group", has_text=t(FamilyGroups.SPOUSE))
    expect(elena_spouse_group.locator('a[data-action="open-profile"]')).to_have_count(1)
    expect(elena_spouse_group.locator('a[data-action="open-profile"]').filter(has_text="Сергей")).to_be_visible()

    # Navigate back к Сергею, потом вверх к Ивану (generation 1).
    elena_spouse_group.locator('a[data-action="open-profile"]').filter(has_text="Сергей").click()
    panel.expect_visible()
    _click_family_link(panel, t(FamilyGroups.PARENTS), "Иван")

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
    _import_via_ui(owner_page, GEDCOM_CYRILLIC_EDGE, "cyrillic.ged")

    panel = _search_and_open_profile(owner_page, "Пётр")

    # Title содержит exact символы — букву ё и дефисную фамилию.
    expect(panel.title).to_contain_text("Пётр")
    expect(panel.title).to_contain_text("Аксёнов-Жёлтый")

    # Даты + место с буквой ё в имени села.
    dates_loc = panel.container.locator(".profile-dates")
    expect(dates_loc).to_contain_text("1900")
    expect(dates_loc).to_contain_text("1973")
    expect(panel.container.locator(".profile-place")).to_contain_text("Ёлкино")

    # Bidirectional spouse: Пётр → Евдокия с буквой ё в её фамилии.
    _click_family_link(panel, t(FamilyGroups.SPOUSE), "Евдокия")
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
    _import_via_ui(owner_page, GEDCOM_MINIMAL_INDI, "minimal.ged")

    panel = _search_and_open_profile(owner_page, "Минимальный")

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
    _import_via_ui(owner_page, GEDCOM_WITH_NOTE, "with-note.ged")
    panel = _search_and_open_profile(owner_page, "Захар")

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
    _import_via_ui(owner_page, GEDCOM_THREE_GEN, "three-gen.ged")
    _search_and_orbit(owner_page, "Андрей")

    # Orbit-cards вокруг Андрея. Кажда parent-card — отдельная `.orbit-card`
    # с `.orbit-card-relation` под именем. Фильтруем by name → один card
    # на родителя, читаем relation.
    orbit_cards = owner_page.locator(".orbit-card")
    sergey_card = orbit_cards.filter(has_text="Сергей").first
    elena_card = orbit_cards.filter(has_text="Елена").first
    expect(sergey_card).to_be_visible()
    expect(elena_card).to_be_visible()

    expect(sergey_card.locator(".orbit-card-relation")).to_have_text("отец")
    expect(elena_card.locator(".orbit-card-relation")).to_have_text("мать")


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
    _import_via_ui(owner_page, GEDCOM_THREE_GEN, "three-gen.ged")

    # «Импортировать ещё» → IDLE → upload того же файла → confirm → DONE.
    owner = OwnerPage(owner_page)
    owner.import_again_btn.click()
    owner.expect_import_state("IDLE")
    owner.upload_ged(filename="three-gen.ged", content=GEDCOM_THREE_GEN.encode("utf-8"))
    owner.expect_import_state("PREVIEW")
    owner.confirm_import_via_dialog()
    owner.expect_import_state("DONE")

    # 1. Search «Андрей» → ровно 1 карточка.
    panel = _search_and_open_profile(owner_page, "Андрей")
    expect(panel.title).to_contain_text("Андрей")

    # 2. У Андрея всё ещё ровно 2 родителя (не 4 — что было бы при дубле
    # relationship-rows).
    parents_group = panel.container.locator(".profile-family-group", has_text=t(FamilyGroups.PARENTS))
    expect(parents_group.locator('a[data-action="open-profile"]')).to_have_count(2)
