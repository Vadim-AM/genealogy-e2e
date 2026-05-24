"""Localised UI strings + assertion error messages — единый source of truth.

Usage:
    from src.texts import t, Buttons, ErrMsg

    expect(locator, ErrMsg.profile_not_visible).to_be_visible()
    page.get_by_role("button", name=t(Buttons.SAVE))

Каждый русскоязычный текст, на который тест ассертит или по которому
ищет элемент, живёт здесь. Переключение локали — одна правка.
"""

from __future__ import annotations

from config.settings import settings

_LOCALE = settings.locale


class _Catalogue:
    """Subclass and define attributes as `dict[locale, str]` or plain `str`."""


# ─────────────────────────────────────────────────────────────────────────
# UI string catalogues
# ─────────────────────────────────────────────────────────────────────────


class Buttons(_Catalogue):
    """Button names — used in `get_by_role("button", name=...)`."""

    LOGIN = {"ru": "Войти", "en": "Sign in"}
    SIGNUP = {"ru": "Создать аккаунт", "en": "Create account"}
    SAVE = {"ru": "Сохранить", "en": "Save"}
    CANCEL = {"ru": "Отмена", "en": "Cancel"}
    DELETE = {"ru": "Удалить", "en": "Delete"}
    EDIT = {"ru": "Редактировать", "en": "Edit"}
    CLOSE = {"ru": "Закрыть", "en": "Close"}
    ACCEPT = {"ru": "Принять", "en": "Accept"}
    REJECT = {"ru": "Отклонить", "en": "Reject"}
    ENRICH = {"ru": "Найти больше", "en": "Find more"}
    ADD = {"ru": "Добавить", "en": "Add"}
    SEND_RESET_LINK = {"ru": "Прислать ссылку", "en": "Send reset link"}
    WAITLIST_SUBMIT = {"ru": "Записаться в ранний доступ", "en": "Join early access"}


class Links(_Catalogue):
    SIGNUP = {"ru": "Регистрация", "en": "Sign up"}
    FORGOT_PASSWORD = {"ru": "Забыли пароль", "en": "Forgot password"}


class Brand(_Catalogue):
    TITLE_FRAGMENTS = {
        "ru": ("Родословн", "Семейн", "древо"),
        "en": ("Genealogy", "Family", "tree"),
    }


class Invite(_Catalogue):
    OWNER_WARNING = {"ru": "владелец", "en": "owner"}
    ACCEPT_SUCCESS_TITLE = {"ru": "Готово", "en": "Done"}
    ALREADY_MEMBER_TITLE = {"ru": "уже здесь", "en": "already here"}
    OPEN_TREE_LINK = {"ru": "Открыть древо", "en": "Open tree"}
    ADDED_TO_TREE = {"ru": "добавлены в древо", "en": "added to the tree"}
    LOGIN_REQUIRED_MSG = {"ru": "требует входа", "en": "requires sign-in"}
    LOGIN_LINK = Buttons.LOGIN
    SIGNUP_LINK = {"ru": "зарегистрироваться", "en": "sign up"}


class PII(_Catalogue):
    OWNER_FAMILY_NAMES = ("Данилюк", "Макаров")


class AiConsent(_Catalogue):
    PROVIDER = "Anthropic"
    POLICY_KEYWORD = {"ru": "приватность", "en": "privacy"}
    SHARED_DATA_KEYWORD = {"ru": "данных карточки", "en": "data from the card"}
    DECLINE_LABEL = {"ru": "Не сейчас", "en": "Not now"}
    CONFIRM_LABEL = {"ru": "Запустить", "en": "Run"}


class Enrichment(_Catalogue):
    REVERT_OK = {"ru": "Снять", "en": "Remove"}
    BETA_KEYWORD = {"ru": "публичной бете", "en": "public beta"}
    COMING_SOON = {"ru": "скоро", "en": "soon"}


class Mfa(_Catalogue):
    STATUS_ON = {"ru": "включена", "en": "enabled"}
    STATUS_OFF = {"ru": "отключена", "en": "disabled"}


class Onboarding(_Catalogue):
    CLEAR_DEMO_CONFIRM = {"ru": "Стереть", "en": "Erase"}
    KEEP_DEMO_CONFIRM = {"ru": "Использовать как шаблон", "en": "Use as template"}


class FamilyGroups(_Catalogue):
    PARENTS = {"ru": "Родители", "en": "Parents"}
    SPOUSE = {"ru": "Супруг", "en": "Spouse"}
    CHILDREN = {"ru": "Дети", "en": "Children"}
    SIBLINGS = {"ru": "Братья/сёстры", "en": "Siblings"}


class LinkedChip(_Catalogue):
    TITLE_KEYWORD = {"ru": "Привязка", "en": "Linked"}
    HINT_KEYWORD = {"ru": "связь", "en": "relationship"}
    UNLINK = {"ru": "Отвязать", "en": "Unlink"}


class TestData(_Catalogue):
    SAMPLE_SITE_NAME = "Тестовая семья"
    GEDCOM_HEAD = "0 HEAD"
    DEMO_PERSON_ID = "demo-self"
    DEFAULT_FULL_NAME = "Тестовый Пользователь"
    ADD_REL_SURNAME = "Тестовый"
    ADD_REL_GIVEN = "Брат"
    SOURCE_NAME = "Архив 1"
    SOURCE_NAME_PATCHED = "Архив 1 (испр.)"


class GedcomImport(_Catalogue):
    SKIPPED_LABEL = {"ru": "Пропущено", "en": "Skipped"}
    FILE_EXTENSION_HINT = ".ged"
    EMPTY_LABEL = {"ru": "пустой", "en": "empty"}
    TOO_LARGE_LABEL = {"ru": "слишком большой", "en": "too large"}


class AgeValidation(_Catalogue):
    PARENT_AGE_KEYWORD = {"ru": "Возраст родителя", "en": "Parent age"}


class Waitlist(_Catalogue):
    OVERFLOW_TITLE = {"ru": "Сейчас принимаем не всех", "en": "Not accepting everyone"}
    WAITLIST_KEYWORD = {"ru": "список ожидания", "en": "waiting list"}


class ConfirmDialog(_Catalogue):
    IRREVERSIBLE = {"ru": "необратим", "en": "irreversible"}
    RELATIONS_KEYWORD = {"ru": "связ", "en": "relat"}


class RelationLabels(_Catalogue):
    FATHER = {"ru": "отец", "en": "father"}
    MOTHER = {"ru": "мать", "en": "mother"}


class Labels(_Catalogue):
    EMAIL = "Email"
    PASSWORD = {"ru": "Пароль", "en": "Password"}
    SITE_NAME = {"ru": "Название", "en": "Name"}
    FAMILY_NAME = {"ru": "Фамилия", "en": "Family name"}
    REGIONS = {"ru": "Регионы", "en": "Regions"}
    CONTACT_EMAIL = {"ru": "Контактный email", "en": "Contact email"}
    ABOUT = {"ru": "О проекте", "en": "About"}
    WAITLIST_EMAIL = {"ru": "Email для уведомления о запуске", "en": "Email for launch notification"}


class Placeholders(_Catalogue):
    SEARCH = {"ru": "Поиск", "en": "Search"}
    SEARCH_TREE = {"ru": "Найти...", "en": "Find..."}


class AboutTab(_Catalogue):
    FAMILY_TREE_KEYWORD = {"ru": "семейное древо", "en": "family tree"}


# ─────────────────────────────────────────────────────────────────────────
# Assertion error messages (ErrMsg)
# ─────────────────────────────────────────────────────────────────────────


class ErrMsg:
    """All assertion messages used by Playwright expect() calls."""

    # Profile
    profile_not_visible = "Профиль не отображается"
    profile_dates_wrong = "Даты в профиле не совпадают с ожидаемыми"
    profile_place_wrong = "Место рождения в профиле не совпадает"
    profile_title_wrong = "Заголовок профиля не совпадает"
    profile_name_missing = "Имя не найдено в заголовке профиля"
    story_not_visible = "Биография не отображается"
    story_text_wrong = "Текст биографии не совпадает"

    # Family groups
    family_group_count_wrong = "Количество родственников в группе не совпадает"
    family_link_not_visible = "Ссылка на родственника не видна"
    parent_button_should_be_hidden = "Кнопка добавления родителей должна быть скрыта при наличии двух"

    # Tree
    tree_not_rendered = "Дерево не отрисовалось"
    orbit_card_not_visible = "Orbit-карточка не видна"
    orbit_card_relation_wrong = "Подпись связи на orbit-карточке не совпадает"
    minimap_not_visible = "Минимапа не отображается"
    search_results_not_visible = "Результаты поиска не отображаются"
    tab_not_visible = "Вкладка не видна"
    tab_should_be_hidden = "Вкладка должна быть скрыта"

    # Editor
    editor_not_visible = "Редактор персоны не открылся"
    editor_field_wrong = "Значение поля в редакторе не совпадает"
    editor_save_failed = "Сохранение в редакторе не прошло"
    editor_warning_not_visible = "Предупреждение редактора не отображается"

    # Auth
    login_error_not_visible = "Ошибка входа не отображается"
    signup_form_not_visible = "Форма регистрации не отображается"
    verification_message_wrong = "Сообщение о верификации не совпадает"
    auth_name_wrong = "Имя пользователя в шапке не совпадает"
    logout_link_not_visible = "Ссылка «Выйти» не видна"

    # Invite
    invite_title_wrong = "Заголовок страницы приглашения не совпадает"
    invite_message_wrong = "Сообщение приглашения не совпадает"
    invite_link_not_visible = "Ссылка на приглашении не видна"

    # Enrichment
    enrichment_modal_not_visible = "Модальное окно обогащения не открылось"
    enrichment_results_wrong = "Результаты обогащения не совпадают"
    ai_button_should_be_disabled = "Кнопка AI должна быть disabled"

    # GEDCOM
    gedcom_import_state_wrong = "Состояние GEDCOM импорта не совпадает"
    gedcom_stats_not_visible = "Статистика GEDCOM не отображается"
    gedcom_encoding_wrong = "Кодировка GEDCOM не совпадает"

    # Security
    xss_payload_rendered = "XSS payload отрендерился как HTML"
    sql_error_leaked = "SQL ошибка утекла в response"

    # Modal / dialog / overlay
    modal_not_visible = "Модальное окно не отображается"
    overlay_should_be_closed = "Оверлей должен быть закрыт"
    dialog_not_visible = "Диалог не отображается"
    dialog_should_be_closed = "Диалог должен быть закрыт"

    # Dropdown (custom select)
    dropdown_not_visible = "Выпадающий список не отображается"
    dropdown_should_be_closed = "Выпадающий список должен быть закрыт"

    # Navigation
    page_title_wrong = "Заголовок страницы не совпадает"
    url_wrong = "URL страницы не совпадает"

    # Form / button
    button_not_visible = "Кнопка не видна"
    button_not_enabled = "Кнопка не активна"
    input_not_visible = "Поле ввода не видно"
    checkbox_state_wrong = "Состояние чекбокса не совпадает"

    # Feature flags
    feature_flag_state_wrong = "Состояние feature flag не совпадает"

    # MFA
    mfa_status_wrong = "Статус MFA не совпадает"

    # Dedup / add relative
    suggestion_not_visible = "Карточка предложения не видна"
    suggestion_count_wrong = "Количество предложений не совпадает"
    validation_error_wrong = "Ошибка валидации не совпадает"

    # Photos
    photo_not_visible = "Фото не отображается"

    # Pricing
    pricing_card_not_visible = "Карточка тарифа не видна"

    # General
    element_not_visible = "Элемент не видим"
    element_should_be_hidden = "Элемент должен быть скрыт"
    wrong_text_content = "Текстовое содержимое не совпадает"
    wrong_count = "Количество элементов не совпадает"
    wrong_attribute = "Значение атрибута не совпадает"
    wrong_css_class = "CSS-класс элемента не совпадает"
    link_not_visible = "Ссылка не видна"


# ─────────────────────────────────────────────────────────────────────────
# Locale resolver
# ─────────────────────────────────────────────────────────────────────────


def t(value):
    """Pick the active-locale string (or pass through if not localised)."""
    if isinstance(value, dict):
        if _LOCALE not in value:
            raise KeyError(
                f"locale {_LOCALE!r} not defined for value with keys {list(value)}; "
                "extend src/texts.py"
            )
        return value[_LOCALE]
    return value
