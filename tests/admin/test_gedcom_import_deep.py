"""TC-GEDCOM-DEEP: полноценные UI flow — import + навигация + encoding + idempotency."""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from assertions.base import should
from framework.step import step
from pages.owner_page import OwnerPage
from pages.tree_page import TreePage
from src.texts import ErrMsg, FamilyGroups, RelationLabels, t
from test_data.gedcom.samples import (
    GEDCOM_CYRILLIC_EDGE,
    GEDCOM_MINIMAL_INDI,
    GEDCOM_THREE_GEN,
    GEDCOM_WITH_NOTE,
)

if TYPE_CHECKING:
    from fixtures.users import AuthUser


@allure.title("GEDCOM: импорт 3 поколений и навигация по семейным связям")
def test_user_imports_three_generation_family_and_navigates_via_ui(
    owner_page: Page,
    owner_user: AuthUser,
) -> None:
    """Импорт 3-gen семьи и навигация по семейным связям в обе стороны."""
    with step("подготовка: импорт 3-поколенного GEDCOM"):
        owner = OwnerPage(owner_page)
        owner.import_gedcom_via_ui(GEDCOM_THREE_GEN, "three-gen.ged")

    with step("проверка: профиль Андрея содержит имя и год рождения"):
        # User finds Андрея через search (single token: search.js matches
        # `p.name.includes(q)`; multi-word query was failing because backend
        # stores `name="Surname Given"` while UI shows `Given Surname` — UX
        # inconsistency tracked separately).
        panel = TreePage(owner_page).search_and_open_profile("Андрей")

        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Андрей")
        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Сидоров")
        expect(panel.dates, ErrMsg.profile_dates_wrong).to_contain_text("1980")

        # У Андрея ровно 2 родителя — если бы import продублировал персону,
        # их было бы 4. Точный count ловит обе регрессии: «нет связей» и
        # «дубли».
        expect(
            panel.family_links(t(FamilyGroups.PARENTS)),
            ErrMsg.family_group_count_wrong,
        ).to_have_count(2)

    with step("проверка: навигация Андрей → Сергей (родитель) и обратная ссылка"):
        # Connection: Андрей → Сергей (родитель).
        panel.click_family_link(t(FamilyGroups.PARENTS), "Сергей")
        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Сергей")
        expect(panel.dates, ErrMsg.profile_dates_wrong).to_contain_text("1950")

        # Bidirectional: Сергей → Андрей (в «Дети»). Ровно один ребёнок.
        expect(
            panel.family_links(t(FamilyGroups.CHILDREN)),
            ErrMsg.family_group_count_wrong,
        ).to_have_count(1)
        expect(
            panel.family_link(t(FamilyGroups.CHILDREN), "Андрей"),
            ErrMsg.family_link_not_visible,
        ).to_be_visible()

    with step("проверка: навигация Сергей → Елена (супруга) и bidirectional spouse"):
        # Connection: Сергей → Елена (супруга). Ровно один супруг.
        expect(
            panel.family_links(t(FamilyGroups.SPOUSE)),
            ErrMsg.family_group_count_wrong,
        ).to_have_count(1)
        panel.click_family_link(t(FamilyGroups.SPOUSE), "Елена")
        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Елена")
        expect(panel.dates, ErrMsg.profile_dates_wrong).to_contain_text("1952")

        # Bidirectional spouse: Елена → Сергей (count=1).
        expect(
            panel.family_links(t(FamilyGroups.SPOUSE)),
            ErrMsg.family_group_count_wrong,
        ).to_have_count(1)
        expect(
            panel.family_link(t(FamilyGroups.SPOUSE), "Сергей"),
            ErrMsg.family_link_not_visible,
        ).to_be_visible()

    with step("проверка: навигация к Ивану (поколение 1) — даты и место"):
        # Navigate back к Сергею, потом вверх к Ивану (generation 1).
        panel.click_family_link(t(FamilyGroups.SPOUSE), "Сергей")
        panel.click_family_link(t(FamilyGroups.PARENTS), "Иван")

        # Иван (generation 1): году + место + год смерти.
        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Иван")
        expect(panel.dates, ErrMsg.profile_dates_wrong).to_contain_text("1920")
        expect(panel.dates, ErrMsg.profile_dates_wrong).to_contain_text("1990")
        expect(panel.place, ErrMsg.profile_place_wrong).to_contain_text("Краснодар")


@allure.title("GEDCOM: кириллица с буквой ё сохраняется без искажений")
def test_user_imports_cyrillic_data_renders_without_mojibake_via_ui(
    owner_page: Page,
    owner_user: AuthUser,
) -> None:
    """Кириллица с буквой ё сохраняется без mojibake через всю UI цепочку."""
    with step("подготовка: импорт GEDCOM с кириллицей и буквой ё"):
        owner = OwnerPage(owner_page)
        owner.import_gedcom_via_ui(GEDCOM_CYRILLIC_EDGE, "cyrillic.ged")

    with step("проверка: профиль Петра содержит точные кириллические символы"):
        panel = TreePage(owner_page).search_and_open_profile("Пётр")

        # Title содержит exact символы — букву ё и дефисную фамилию.
        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Пётр")
        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Аксёнов-Жёлтый")

        # Даты + место с буквой ё в имени села.
        expect(panel.dates, ErrMsg.profile_dates_wrong).to_contain_text("1900")
        expect(panel.dates, ErrMsg.profile_dates_wrong).to_contain_text("1973")
        expect(panel.place, ErrMsg.profile_place_wrong).to_contain_text("Ёлкино")

    with step("проверка: навигация к супруге Евдокии — буква ё в фамилии"):
        # Bidirectional spouse: Пётр → Евдокия с буквой ё в её фамилии.
        panel.click_family_link(t(FamilyGroups.SPOUSE), "Евдокия")
        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Евдокия")
        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Аксёнова-Жёлтая")


@allure.title("GEDCOM: минимальный INDI (только имя и пол) не ломает профиль")
def test_user_imports_minimal_indi_profile_renders_without_crash(
    owner_page: Page,
    owner_user: AuthUser,
) -> None:
    """Минимальный INDI (NAME + SEX) рендерится корректно без краша."""
    with step("подготовка: импорт минимального INDI"):
        owner = OwnerPage(owner_page)
        owner.import_gedcom_via_ui(GEDCOM_MINIMAL_INDI, "minimal.ged")

    with step("проверка: профиль рендерится с именем без краша"):
        panel = TreePage(owner_page).search_and_open_profile("Минимальный")

        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Минимальный")
        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Тестов")

        # `.profile-page` container loaded — никаких JS exceptions, никакой
        # broken rendering (sanity что openProfile прошёл до конца).
        expect(panel.container, ErrMsg.profile_not_visible).to_be_visible()

    with step("проверка: даты пустые и нет фантомных связей"):
        # Дата отсутствует — `[data-testid="profile-dates"]` либо empty, либо отсутствует.
        # Контракт: рендер не падает, даже если у profile нет жизненных дат.
        if panel.dates.count() > 0:
            # Если элемент есть — он не должен содержать «1970», «1980» или
            # подобных «фантомных» дат от backend defaults.
            text = (panel.dates.text_content() or "").strip()
            should.be_false(
                any(year in text for year in ("1970", "1980", "1990")),
                ErrMsg.gedcom_phantom_dates,
            )

        # Family-секция структурно есть (4 группы — Родители/Супруг/Дети/
        # Братья), но без relations: ни одной ссылки на родственника.
        expect(panel.family_section, ErrMsg.element_not_visible).to_be_visible()
        expect(panel.all_family_links, ErrMsg.family_group_count_wrong).to_have_count(0)


@allure.title("GEDCOM: NOTE из файла отображается как биография в профиле")
def test_user_imports_indi_with_note_renders_biography_in_profile_story(
    owner_page: Page,
    owner_user: AuthUser,
) -> None:
    """NOTE из GEDCOM отображается в profile-story."""
    with step("подготовка: импорт GEDCOM с NOTE"):
        owner = OwnerPage(owner_page)
        owner.import_gedcom_via_ui(GEDCOM_WITH_NOTE, "with-note.ged")

    with step("проверка: биография из NOTE отображается в profile-story"):
        panel = TreePage(owner_page).search_and_open_profile("Захар")

        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Захар")
        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Семёнов")

        expect(panel.story, ErrMsg.story_not_visible).to_be_visible()
        # Полный текст биографии (берём 3 опорные фразы — медаль, профессия,
        # эвакуация). Достаточно distinct, чтобы любая обрезка / потеря
        # фрагмента провалила тест.
        expect(panel.story, ErrMsg.story_text_wrong).to_contain_text("Георгиевским крестом 4 степени")
        expect(panel.story, ErrMsg.story_text_wrong).to_contain_text("учителем в селе Никольское")
        expect(panel.story, ErrMsg.story_text_wrong).to_contain_text("Эвакуировался в 1942 году")


@allure.title("GEDCOM: пол M/F определяет подписи «отец»/«мать» в орбите")
def test_user_imports_male_and_female_show_correct_relation_label_in_orbit(
    owner_page: Page,
    owner_user: AuthUser,
) -> None:
    """SEX M/F определяет подписи «отец»/«мать» в orbit-карточках."""
    with step("подготовка: импорт 3-gen GEDCOM и переход в orbit Андрея"):
        owner = OwnerPage(owner_page)
        owner.import_gedcom_via_ui(GEDCOM_THREE_GEN, "three-gen.ged")
        TreePage(owner_page).search_and_orbit("Андрей")

    with step("проверка: orbit-карточки показывают «отец» и «мать»"):
        # Orbit-cards вокруг Андрея. Кажда parent-card — отдельная `.orbit-card`
        # с `.orbit-card-relation` под именем. Фильтруем by name → один card
        # на родителя, читаем relation.
        tree = TreePage(owner_page)
        sergey_card = tree.orbit_card_by_name("Сергей")
        elena_card = tree.orbit_card_by_name("Елена")
        expect(sergey_card, ErrMsg.orbit_card_not_visible).to_be_visible()
        expect(elena_card, ErrMsg.orbit_card_not_visible).to_be_visible()

        expect(
            tree.orbit_card_relation(sergey_card),
            ErrMsg.orbit_card_relation_wrong,
        ).to_have_text(t(RelationLabels.FATHER))
        expect(
            tree.orbit_card_relation(elena_card),
            ErrMsg.orbit_card_relation_wrong,
        ).to_have_text(t(RelationLabels.MOTHER))


@allure.title("GEDCOM: повторный импорт того же файла не дублирует персон")
def test_user_reimports_same_file_does_not_duplicate_persons(
    owner_page: Page,
    owner_user: AuthUser,
) -> None:
    """Повторный импорт того же файла не дублирует персон и связей."""
    with step("подготовка: первый импорт 3-gen GEDCOM"):
        owner = OwnerPage(owner_page)
        owner.import_gedcom_via_ui(GEDCOM_THREE_GEN, "three-gen.ged")

    with step("действие: повторный импорт того же файла"):
        # «Импортировать ещё» → IDLE → upload того же файла → confirm → DONE.
        owner = OwnerPage(owner_page)
        owner.click_import_again()
        owner.expect_import_state("IDLE")
        owner.upload_ged(filename="three-gen.ged", content=GEDCOM_THREE_GEN.encode("utf-8"))
        owner.expect_import_state("PREVIEW")
        owner.confirm_import_via_dialog()
        owner.expect_import_state("DONE")

    with step("проверка: Андрей один и у него ровно 2 родителя"):
        # 1. Search «Андрей» → ровно 1 карточка.
        panel = TreePage(owner_page).search_and_open_profile("Андрей")
        expect(panel.title, ErrMsg.profile_title_wrong).to_contain_text("Андрей")

        # 2. У Андрея всё ещё ровно 2 родителя (не 4 — что было бы при дубле
        # relationship-rows).
        expect(
            panel.family_links(t(FamilyGroups.PARENTS)),
            ErrMsg.family_group_count_wrong,
        ).to_have_count(2)
