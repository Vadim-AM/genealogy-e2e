"""TC-GEDCOM-DEEP: полноценные UI flow — import + навигация + encoding + idempotency."""

from __future__ import annotations

import allure
from playwright.sync_api import Page, expect

from assertions.base import should
from framework.step import step
from helpers.admin.gedcom_ui import import_via_ui
from helpers.tree.tree_navigation import (
    click_family_link,
    search_and_open_profile,
    search_and_orbit,
)
from pages.owner_page import OwnerPage
from src.texts import ErrMsg, FamilyGroups, RelationLabels, t
from test_data.gedcom.samples import (
    GEDCOM_CYRILLIC_EDGE,
    GEDCOM_MINIMAL_INDI,
    GEDCOM_THREE_GEN,
    GEDCOM_WITH_NOTE,
)


@allure.title("GEDCOM: импорт 3 поколений и навигация по семейным связям")
def test_user_imports_three_generation_family_and_navigates_via_ui(
    owner_page: Page, owner_user,
) -> None:
    """Импорт 3-gen семьи и навигация по семейным связям в обе стороны."""
    with step("подготовка: импорт 3-поколенного GEDCOM"):
        import_via_ui(owner_page, GEDCOM_THREE_GEN, "three-gen.ged")

    with step("проверка: профиль Андрея содержит имя и год рождения"):
        # User finds Андрея через search (single token: search.js matches
        # `p.name.includes(q)`; multi-word query was failing because backend
        # stores `name="Surname Given"` while UI shows `Given Surname` — UX
        # inconsistency tracked separately).
        panel = search_and_open_profile(owner_page, "Андрей")

        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Андрей")
        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Сидоров")
        expect(
            # no semantic: data-testid element, no role
            panel.container.locator('[data-testid="profile-dates"]'),
            ErrMsg.profile_dates_wrong,
        ).to_contain_text("1980")

        # У Андрея ровно 2 родителя — если бы import продублировал персону,
        # их было бы 4. Точный count ловит обе регрессии: «нет связей» и
        # «дубли».
        parents_group = panel.container.locator(
            # no semantic: data-testid element, no role
            '[data-testid="profile-family-group"]', has_text=t(FamilyGroups.PARENTS),
        )
        expect(
            parents_group.locator('a[data-action="open-profile"]'),
            ErrMsg.family_group_count_wrong,
        ).to_have_count(2)

    with step("проверка: навигация Андрей → Сергей (родитель) и обратная ссылка"):
        # Connection: Андрей → Сергей (родитель).
        click_family_link(panel, t(FamilyGroups.PARENTS), "Сергей")
        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Сергей")
        expect(
            # no semantic: data-testid element, no role
            panel.container.locator('[data-testid="profile-dates"]'),
            ErrMsg.profile_dates_wrong,
        ).to_contain_text("1950")

        # Bidirectional: Сергей → Андрей (в «Дети»). Ровно один ребёнок.
        children_group = panel.container.locator(
            # no semantic: data-testid element, no role
            '[data-testid="profile-family-group"]', has_text=t(FamilyGroups.CHILDREN),
        )
        expect(
            children_group.locator('a[data-action="open-profile"]'),
            ErrMsg.family_group_count_wrong,
        ).to_have_count(1)
        expect(
            children_group.locator('a[data-action="open-profile"]').filter(has_text="Андрей"),
            ErrMsg.family_link_not_visible,
        ).to_be_visible()

    with step("проверка: навигация Сергей → Елена (супруга) и bidirectional spouse"):
        # Connection: Сергей → Елена (супруга). Ровно один супруг.
        spouse_group = panel.container.locator(
            # no semantic: data-testid element, no role
            '[data-testid="profile-family-group"]', has_text=t(FamilyGroups.SPOUSE),
        )
        expect(
            spouse_group.locator('a[data-action="open-profile"]'),
            ErrMsg.family_group_count_wrong,
        ).to_have_count(1)
        click_family_link(panel, t(FamilyGroups.SPOUSE), "Елена")
        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Елена")
        expect(
            # no semantic: data-testid element, no role
            panel.container.locator('[data-testid="profile-dates"]'),
            ErrMsg.profile_dates_wrong,
        ).to_contain_text("1952")

        # Bidirectional spouse: Елена → Сергей (count=1).
        elena_spouse_group = panel.container.locator(
            # no semantic: data-testid element, no role
            '[data-testid="profile-family-group"]', has_text=t(FamilyGroups.SPOUSE),
        )
        expect(
            elena_spouse_group.locator('a[data-action="open-profile"]'),
            ErrMsg.family_group_count_wrong,
        ).to_have_count(1)
        expect(
            elena_spouse_group.locator('a[data-action="open-profile"]').filter(has_text="Сергей"),
            ErrMsg.family_link_not_visible,
        ).to_be_visible()

    with step("проверка: навигация к Ивану (поколение 1) — даты и место"):
        # Navigate back к Сергею, потом вверх к Ивану (generation 1).
        elena_spouse_group.locator('a[data-action="open-profile"]').filter(has_text="Сергей").click()
        panel.expect_visible()
        click_family_link(panel, t(FamilyGroups.PARENTS), "Иван")

        # Iван (generation 1): daдy + место + год смерти.
        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Иван")
        # no semantic: data-testid element, no role
        dates_loc = panel.container.locator('[data-testid="profile-dates"]')
        expect(dates_loc, ErrMsg.profile_dates_wrong).to_contain_text("1920")
        expect(dates_loc, ErrMsg.profile_dates_wrong).to_contain_text("1990")
        expect(
            # no semantic: data-testid element, no role
            panel.container.locator('[data-testid="profile-place"]'),
            ErrMsg.profile_place_wrong,
        ).to_contain_text("Краснодар")



@allure.title("GEDCOM: кириллица с буквой ё сохраняется без искажений")
def test_user_imports_cyrillic_data_renders_without_mojibake_via_ui(
    owner_page: Page, owner_user,
) -> None:
    """Кириллица с буквой ё сохраняется без mojibake через всю UI цепочку."""
    with step("подготовка: импорт GEDCOM с кириллицей и буквой ё"):
        import_via_ui(owner_page, GEDCOM_CYRILLIC_EDGE, "cyrillic.ged")

    with step("проверка: профиль Петра содержит точные кириллические символы"):
        panel = search_and_open_profile(owner_page, "Пётр")

        # Title содержит exact символы — букву ё и дефисную фамилию.
        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Пётр")
        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Аксёнов-Жёлтый")

        # Даты + место с буквой ё в имени села.
        # no semantic: data-testid element, no role
        dates_loc = panel.container.locator('[data-testid="profile-dates"]')
        expect(dates_loc, ErrMsg.profile_dates_wrong).to_contain_text("1900")
        expect(dates_loc, ErrMsg.profile_dates_wrong).to_contain_text("1973")
        expect(
            # no semantic: data-testid element, no role
            panel.container.locator('[data-testid="profile-place"]'),
            ErrMsg.profile_place_wrong,
        ).to_contain_text("Ёлкино")

    with step("проверка: навигация к супруге Евдокии — буква ё в фамилии"):
        # Bidirectional spouse: Пётр → Евдокия с буквой ё в её фамилии.
        click_family_link(panel, t(FamilyGroups.SPOUSE), "Евдокия")
        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Евдокия")
        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Аксёнова-Жёлтая")



@allure.title("GEDCOM: минимальный INDI (только имя и пол) не ломает профиль")
def test_user_imports_minimal_indi_profile_renders_without_crash(
    owner_page: Page, owner_user,
) -> None:
    """Минимальный INDI (NAME + SEX) рендерится корректно без краша."""
    with step("подготовка: импорт минимального INDI"):
        import_via_ui(owner_page, GEDCOM_MINIMAL_INDI, "minimal.ged")

    with step("проверка: профиль рендерится с именем без краша"):
        panel = search_and_open_profile(owner_page, "Минимальный")

        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Минимальный")
        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Тестов")

        # `.profile-page` container loaded — никаких JS exceptions, никакой
        # broken rendering (sanity что openProfile прошёл до конца).
        expect(panel.container, ErrMsg.profile_not_visible).to_be_visible()

    with step("проверка: даты пустые и нет фантомных связей"):
        # Дата отсутствует — `[data-testid="profile-dates"]` либо empty, либо отсутствует.
        # Контракт: рендер не падает, даже если у profile нет жизненных дат.
        # no semantic: data-testid element, no role
        dates_loc = panel.container.locator('[data-testid="profile-dates"]')
        if dates_loc.count() > 0:
            # Если элемент есть — он не должен содержать «1970», «1980» или
            # подобных «фантомных» дат от backend defaults.
            text = (dates_loc.text_content() or "").strip()
            should.be_false(
                any(year in text for year in ("1970", "1980", "1990")),
                ErrMsg.gedcom_phantom_dates,
            )

        # Family-секция структурно есть (4 группы — Родители/Супруг/Дети/
        # Братья), но без relations: ни одной `<a data-action="open-profile">`
        # ссылки на родственника. Селектор `[data-testid="profile-family"]` — стабильный
        # контейнер (не зависит от локали section-title).
        # no semantic: data-testid element, no role
        family_block = panel.container.locator('[data-testid="profile-family"]')
        expect(family_block, ErrMsg.element_not_visible).to_be_visible()
        expect(family_block.locator('a[data-action="open-profile"]'), ErrMsg.family_group_count_wrong).to_have_count(0)



@allure.title("GEDCOM: NOTE из файла отображается как биография в профиле")
def test_user_imports_indi_with_note_renders_biography_in_profile_story(
    owner_page: Page, owner_user,
) -> None:
    """NOTE из GEDCOM отображается в profile-story."""
    with step("подготовка: импорт GEDCOM с NOTE"):
        import_via_ui(owner_page, GEDCOM_WITH_NOTE, "with-note.ged")

    with step("проверка: биография из NOTE отображается в profile-story"):
        panel = search_and_open_profile(owner_page, "Захар")

        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Захар")
        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Семёнов")

        # no semantic: data-testid element, no role
        story = panel.container.locator('[data-testid="profile-story"]')
        expect(story, ErrMsg.story_not_visible).to_be_visible()
        # Полный текст биографии (берём 3 опорные фразы — медаль, профессия,
        # эвакуация). Достаточно distinct, чтобы любая обрезка / потеря
        # фрагмента провалила тест.
        expect(story, ErrMsg.story_text_wrong).to_contain_text("Георгиевским крестом 4 степени")
        expect(story, ErrMsg.story_text_wrong).to_contain_text("учителем в селе Никольское")
        expect(story, ErrMsg.story_text_wrong).to_contain_text("Эвакуировался в 1942 году")



@allure.title("GEDCOM: пол M/F определяет подписи «отец»/«мать» в орбите")
def test_user_imports_male_and_female_show_correct_relation_label_in_orbit(
    owner_page: Page, owner_user,
) -> None:
    """SEX M/F определяет подписи «отец»/«мать» в orbit-карточках."""
    with step("подготовка: импорт 3-gen GEDCOM и переход в orbit Андрея"):
        import_via_ui(owner_page, GEDCOM_THREE_GEN, "three-gen.ged")
        search_and_orbit(owner_page, "Андрей")

    with step("проверка: orbit-карточки показывают «отец» и «мать»"):
        # Orbit-cards вокруг Андрея. Кажда parent-card — отдельная `.orbit-card`
        # с `.orbit-card-relation` под именем. Фильтруем by name → один card
        # на родителя, читаем relation.
        # no semantic: data-testid element, no role
        orbit_cards = owner_page.locator('[data-testid="orbit-card"]')
        sergey_card = orbit_cards.filter(has_text="Сергей").first
        elena_card = orbit_cards.filter(has_text="Елена").first
        expect(sergey_card, ErrMsg.orbit_card_not_visible).to_be_visible()
        expect(elena_card, ErrMsg.orbit_card_not_visible).to_be_visible()

        expect(
            # no semantic: data-testid element, no role
            sergey_card.locator('[data-testid="orbit-card-relation"]'),
            ErrMsg.orbit_card_relation_wrong,
        ).to_have_text(t(RelationLabels.FATHER))
        expect(
            # no semantic: data-testid element, no role
            elena_card.locator('[data-testid="orbit-card-relation"]'),
            ErrMsg.orbit_card_relation_wrong,
        ).to_have_text(t(RelationLabels.MOTHER))



@allure.title("GEDCOM: повторный импорт того же файла не дублирует персон")
def test_user_reimports_same_file_does_not_duplicate_persons(
    owner_page: Page, owner_user,
) -> None:
    """Повторный импорт того же файла не дублирует персон и связей."""
    with step("подготовка: первый импорт 3-gen GEDCOM"):
        import_via_ui(owner_page, GEDCOM_THREE_GEN, "three-gen.ged")

    with step("действие: повторный импорт того же файла"):
        # «Импортировать ещё» → IDLE → upload того же файла → confirm → DONE.
        owner = OwnerPage(owner_page)
        owner.import_again_btn.click()
        owner.expect_import_state("IDLE")
        owner.upload_ged(filename="three-gen.ged", content=GEDCOM_THREE_GEN.encode("utf-8"))
        owner.expect_import_state("PREVIEW")
        owner.confirm_import_via_dialog()
        owner.expect_import_state("DONE")

    with step("проверка: Андрей один и у него ровно 2 родителя"):
        # 1. Search «Андрей» → ровно 1 карточка.
        panel = search_and_open_profile(owner_page, "Андрей")
        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Андрей")

        # 2. У Андрея всё ещё ровно 2 родителя (не 4 — что было бы при дубле
        # relationship-rows).
        parents_group = panel.container.locator(
            # no semantic: data-testid element, no role
            '[data-testid="profile-family-group"]', has_text=t(FamilyGroups.PARENTS),
        )
        expect(
            parents_group.locator('a[data-action="open-profile"]'),
            ErrMsg.family_group_count_wrong,
        ).to_have_count(2)
