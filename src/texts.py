"""Localised UI strings + assertion error messages — единый source of truth.

Usage:
    from src.texts import t, Buttons, ErrMsg

    expect(locator, ErrMsg.profile_not_visible).to_be_visible()
    page.get_by_role("button", name=t(Buttons.SAVE))

Каждый русскоязычный текст, на который тест ассертит или по которому
ищет элемент, живёт здесь. Переключение локали — одна правка.
"""

from __future__ import annotations

from typing import Any

from config.settings import settings

LOCALE = settings.locale


class Catalogue:
    """Subclass and define attributes as `dict[locale, str]` or plain `str`."""


# ─────────────────────────────────────────────────────────────────────────
# UI string catalogues
# ─────────────────────────────────────────────────────────────────────────


class Buttons(Catalogue):
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


class Links(Catalogue):
    SIGNUP = {"ru": "Регистрация", "en": "Sign up"}
    FORGOT_PASSWORD = {"ru": "Забыли пароль", "en": "Forgot password"}


class Brand(Catalogue):
    TITLE_FRAGMENTS = {
        "ru": ("Родословн", "Семейн", "древо"),
        "en": ("Genealogy", "Family", "tree"),
    }


class Invite(Catalogue):
    OWNER_WARNING = {"ru": "владелец", "en": "owner"}
    ACCEPT_SUCCESS_TITLE = {"ru": "Готово", "en": "Done"}
    ALREADY_MEMBER_TITLE = {"ru": "уже здесь", "en": "already here"}
    OPEN_TREE_LINK = {"ru": "Открыть древо", "en": "Open tree"}
    ADDED_TO_TREE = {"ru": "добавлены в древо", "en": "added to the tree"}
    LOGIN_REQUIRED_MSG = {"ru": "требует входа", "en": "requires sign-in"}
    LOGIN_LINK = Buttons.LOGIN
    SIGNUP_LINK = {"ru": "зарегистрироваться", "en": "sign up"}


class PII(Catalogue):
    OWNER_FAMILY_NAMES = ("Данилюк", "Макаров")


class AiConsent(Catalogue):
    PROVIDER = "Anthropic"
    POLICY_KEYWORD = {"ru": "приватность", "en": "privacy"}
    SHARED_DATA_KEYWORD = {"ru": "данных карточки", "en": "data from the card"}
    DECLINE_LABEL = {"ru": "Не сейчас", "en": "Not now"}
    CONFIRM_LABEL = {"ru": "Запустить", "en": "Run"}


class Enrichment(Catalogue):
    REVERT_OK = {"ru": "Снять", "en": "Remove"}
    BETA_KEYWORD = {"ru": "публичной бете", "en": "public beta"}
    COMING_SOON = {"ru": "скоро", "en": "soon"}


class Mfa(Catalogue):
    STATUS_ON = {"ru": "включена", "en": "enabled"}
    STATUS_OFF = {"ru": "отключена", "en": "disabled"}


class Onboarding(Catalogue):
    CLEAR_DEMO_CONFIRM = {"ru": "Стереть", "en": "Erase"}
    KEEP_DEMO_CONFIRM = {"ru": "Использовать как шаблон", "en": "Use as template"}


class FamilyGroups(Catalogue):
    PARENTS = {"ru": "Родители", "en": "Parents"}
    SPOUSE = {"ru": "Супруг", "en": "Spouse"}
    CHILDREN = {"ru": "Дети", "en": "Children"}
    SIBLINGS = {"ru": "Братья/сёстры", "en": "Siblings"}


class LinkedChip(Catalogue):
    TITLE_KEYWORD = {"ru": "Привязка", "en": "Linked"}
    HINT_KEYWORD = {"ru": "связь", "en": "relationship"}
    UNLINK = {"ru": "Отвязать", "en": "Unlink"}


class TestData(Catalogue):
    SAMPLE_SITE_NAME = "Тестовая семья"
    GEDCOM_HEAD = "0 HEAD"
    DEMO_PERSON_ID = "demo-self"
    DEFAULT_FULL_NAME = "Тестовый Пользователь"
    ADD_REL_SURNAME = "Тестовый"
    ADD_REL_GIVEN = "Брат"
    SOURCE_NAME = "Архив 1"
    SOURCE_NAME_PATCHED = "Архив 1 (испр.)"


class GedcomImport(Catalogue):
    SKIPPED_LABEL = {"ru": "Пропущено", "en": "Skipped"}
    FILE_EXTENSION_HINT = ".ged"
    EMPTY_LABEL = {"ru": "пустой", "en": "empty"}
    TOO_LARGE_LABEL = {"ru": "слишком большой", "en": "too large"}


class AgeValidation(Catalogue):
    PARENT_AGE_KEYWORD = {"ru": "Возраст родителя", "en": "Parent age"}


class Waitlist(Catalogue):
    OVERFLOW_TITLE = {"ru": "Сейчас принимаем не всех", "en": "Not accepting everyone"}
    WAITLIST_KEYWORD = {"ru": "список ожидания", "en": "waiting list"}


class ConfirmDialog(Catalogue):
    IRREVERSIBLE = {"ru": "необратим", "en": "irreversible"}
    RELATIONS_KEYWORD = {"ru": "связ", "en": "relat"}


class RelationLabels(Catalogue):
    FATHER = {"ru": "отец", "en": "father"}
    MOTHER = {"ru": "мать", "en": "mother"}


class Labels(Catalogue):
    EMAIL = "Email"
    PASSWORD = {"ru": "Пароль", "en": "Password"}
    SITE_NAME = {"ru": "Название", "en": "Name"}
    FAMILY_NAME = {"ru": "Фамилия", "en": "Family name"}
    REGIONS = {"ru": "Регионы", "en": "Regions"}
    CONTACT_EMAIL = {"ru": "Контактный email", "en": "Contact email"}
    ABOUT = {"ru": "О проекте", "en": "About"}
    WAITLIST_EMAIL = {"ru": "Email для уведомления о запуске", "en": "Email for launch notification"}


class Placeholders(Catalogue):
    SEARCH = {"ru": "Поиск", "en": "Search"}
    SEARCH_TREE = {"ru": "Найти...", "en": "Find..."}


class AboutTab(Catalogue):
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

    # Enrichment / AI
    ai_tooltip_wrong = "Tooltip AI-кнопки не совпадает"
    enrich_post_leaked = "POST enrich не должен был произойти"
    bootstrap_fetch_failed = "Bootstrap-запрос не вернул ожидаемый статус"

    # Data / collections
    collection_not_empty = "Коллекция не должна быть пустой"
    collection_should_be_empty = "Коллекция должна быть пустой"
    item_not_found = "Элемент не найден в коллекции"
    count_mismatch = "Количество не совпадает"

    # Session / auth
    session_should_be_valid = "Сессия должна быть валидна"
    session_should_be_expired = "Сессия должна быть невалидна"
    login_response_not_ok = "Ответ на логин не ok"
    login_cookie_missing = "Session cookie не установлена после логина"
    login_slug_mismatch = "Slug тенанта в /me не совпадает после логина"
    login_error_texts_differ = "Тексты ошибок входа отличаются — возможна утечка enumeration"
    signup_response_not_ok = "Ответ на signup не ok"
    verify_token_missing = "Токен верификации не найден в теле письма"
    verify_auto_login_missing = "Ответ verify-email не содержит auto_login=true"
    verify_slug_missing = "Ответ verify-email не содержит tenant_slug"
    verify_cookie_missing = "Session cookie не установлена после verify-email"
    verify_slug_mismatch = "Slug тенанта в /me не совпадает после верификации"
    tenant_slug_missing = "Ответ login не содержит tenant_slug"
    password_validity_expected_false = "HTML5 minlength validation должна отклонить пароль"
    forgot_response_not_ok = "Ответ на forgot-password не ok"
    reset_response_not_ok = "Ответ на reset-password не ok"
    empty_email_triggered_request = "Пустой email не должен вызывать сетевой запрос"
    invite_href_wrong = "Ссылка open-tree должна указывать на /"
    invite_token_missing_in_href = "Ссылка не содержит invite-token"
    display_name_not_in_message = "display_name не найден в тексте предупреждения"
    slug_leaked_in_message = "Slug утёк в тексте сообщения"
    change_email_token_missing = "Токен подтверждения смены email не отправлен"
    cross_tab_slug_mismatch = "Сессия должна принадлежать ожидаемому тенанту"
    session_not_invalidated = "Сессия не инвалидирована после сброса пароля"
    session_should_be_active = "Сессия должна быть активна"
    welcome_email_missing_host = "Welcome-email не содержит host из GENEALOGY_PUBLIC_URL"
    welcome_email_hardcoded_prod = "Welcome-email содержит hardcoded prod-домен"
    recovery_code_count_wrong = "Количество кодов восстановления не совпадает"
    recovery_code_not_decremented = "Использование кода не уменьшило счётчик"
    me_slug_mismatch = "Slug тенанта в /me не совпадает"
    demo_seed_required = "Свежий тенант содержит демо-данные"
    demo_not_cleared = "Демо-данные должны быть удалены"
    demo_not_preserved = "Демо-данные должны быть сохранены"
    reserved_slug_assigned = "Зарезервированный slug назначен как тенант"
    signup_url_not_preserved = "URL должен остаться /signup после Esc"
    consent_provider_missing = "Текст consent должен упоминать провайдера"
    consent_policy_missing = "Текст consent должен содержать ссылку на политику"
    consent_data_missing = "Текст consent должен перечислять передаваемые данные"
    decline_should_block_post = "Отказ от consent не должен вызывать POST /api/enrich/*"
    enrichment_output_none = "Результат enrichment job не должен быть None"
    enrichment_mock_not_applied = "Mock fixture не применён — получен реальный output"
    enrichment_history_not_list = "history.items должен быть list"
    enrichment_not_429 = "Первый enrichment не должен возвращать 429"
    enrichment_id_missing = "Enrichment job не завершился вовремя"
    enrichment_cache_id_mismatch = "enrichment_id в кэше не совпадает"

    # API response
    status_mismatch = "HTTP статус не совпадает"
    response_field_wrong = "Поле ответа не совпадает"
    response_not_ok = "Ответ API не успешен"

    # Playwright response
    pw_response_not_ok = "Playwright response не 2xx"
    pw_response_status_wrong = "Playwright response status не совпадает"

    # Tree / people
    person_not_in_tree = "Персона не найдена в дереве"
    tree_count_wrong = "Количество персон в дереве не совпадает"
    demo_father_not_in_seed = "Демо-отец отсутствует в seed-данных"
    duplicate_person_found = "Обнаружен дубликат персоны"
    person_count_wrong = "Количество персон не совпадает"
    relationship_count_wrong = "Количество связей не совпадает"
    parent_link_missing = "Связь с родителем отсутствует"
    father_not_linked = "Отец не привязан к ребёнку"
    mother_not_linked = "Мать не привязана к ребёнку"
    new_father_must_differ = "Новый отец должен отличаться от демо-отца"
    people_post_not_expected = "POST /api/people не должен был произойти"
    canonical_name_wrong = "Каноническое имя не содержит ожидаемый фрагмент"

    # Concurrency
    etag_missing = "ETag header отсутствует в ответе"

    # Domain invariants
    delete_500_crash = "DELETE вернул 500 — cascade не обработан"

    # Profile edit
    confirm_text_wrong = "Текст диалога подтверждения не содержит ожидаемую фразу"
    delete_sent_on_dismiss = "DELETE отправлен после отмены диалога подтверждения"
    person_deleted_after_dismiss = "Персона удалена после отмены диалога"
    summary_not_persisted = "Описание не сохранено в бэкенде"

    # Photos
    photo_label_for_wrong = "label#photoAddBtn должен иметь for=photoFileInput"
    photo_input_count_wrong = "Ожидаем ровно один #photoFileInput"
    photo_accept_wrong = "accept-фильтр должен содержать image"

    # Sharing
    share_url_wrong = "URL ссылки шаринга не содержит /share/ сегмент"
    share_not_in_list = "Созданная share-ссылка не найдена в списке"
    share_token_leaked = "GET /api/share/list выдал секретный token url"
    share_url_missing = "Ответ create не содержит URL шаринга"
    share_list_empty = "Список шаринг-ссылок пуст"

    # Sources
    source_not_linked = "Источник не привязан к персоне"
    source_still_linked = "Источник всё ещё привязан после отвязки"
    source_name_wrong = "Имя источника не совпадает"
    source_not_deleted = "Удалённый источник всё ещё в списке"

    # Navigation
    hash_dropped_after_f5 = "Hash профиля потерян после F5"

    # Versioning
    app_version_empty = "app_version должен быть непустой строкой"

    # GEDCOM
    gedcom_export_failed = "Экспорт GEDCOM не удался"
    gedcom_header_missing = "GEDCOM header отсутствует"
    gedcom_skipped_missing = "DONE-сводка не содержит счётчик пропущенных"
    gedcom_round_trip_leaked = "Round-trip создал новые персоны"
    gedcom_new_person_missing = "Новая персона не найдена в дереве после импорта"
    gedcom_no_post_expected = "POST на import-gedcom не ожидался"
    gedcom_phantom_dates = "Минимальный INDI не должен содержать фантомные даты"

    # Owner UI
    save_config_failed = "Сохранение /api/site/config не удалось"
    site_name_wrong = "site_name не совпадает с ожидаемым"
    gedcom_content_type_wrong = "GEDCOM content-type неверный"
    gedcom_charset_wrong = "GEDCOM charset должен быть utf-8"
    gedcom_disposition_wrong = "GEDCOM должен скачиваться как attachment"
    gedcom_filename_wrong = "GEDCOM filename должен заканчиваться на .ged"
    gedcom_line_wrong = "Строка GEDCOM не совпадает с ожидаемой"
    zip_content_type_wrong = "Экспорт должен возвращать ZIP"
    zip_magic_wrong = "ZIP magic bytes не совпадают"
    zip_file_missing = "Файл отсутствует в ZIP-архиве"

    # Site config / multitenant
    tenant_value_leaked = "Значение тенанта утекло в другой тенант"
    tenant_value_corrupted = "Значение тенанта перезаписано другим тенантом"
    anon_value_leaked = "Анонимный запрос выдал приватное значение тенанта"

    # Subscription
    usage_keys_missing = "Обязательные ключи отсутствуют в ответе usage"
    usage_tier_wrong = "Тариф нового владельца должен быть free"
    usage_limit_wrong = "Лимит free-тарифа не совпадает"
    usage_used_wrong = "Использовано должно быть 0 для нового владельца"
    usage_remaining_wrong = "Остаток не совпадает с ожидаемым"
    usage_exhausted_wrong = "Флаг exhausted не совпадает"
    usage_soft_warn_wrong = "Флаг soft_warn не совпадает"

    # Seed / setup
    tenant_no_demo_people = "Тенант не содержит демо-персон"
    payload_sanity = "Sanity-проверка тестового payload не прошла"

    # Добавление родственника
    add_parent_should_be_removed = "Кнопка добавления родителя должна быть скрыта"

    # Аудит
    alert_severity_wrong = "Severity алерта не совпадает"
    audit_action_wrong = "Действие в аудит-логе не совпадает"
    audit_entry_missing = "Запись аудит-лога отсутствует"
    audit_filter_leak = "Фильтр аудита пропускает чужие записи"
    audit_ip_hash_wrong = "Хэш IP в аудит-логе не совпадает"
    audit_ip_raw = "Аудит-лог содержит сырой IP вместо хэша"
    audit_limit_wrong = "Лимит записей аудита не совпадает"
    audit_payload_wrong = "Payload аудит-записи не совпадает"
    backup_alert_missing = "Алерт бэкапа отсутствует"

    # Базовые / конфигурация
    base_url_not_http = "Base URL не начинается с http"
    bounding_box_missing = "Bounding box элемента отсутствует"
    config_leaked = "Конфигурация утекла в публичный ответ"
    constants_js_too_large = "constants.js превышает допустимый размер"
    contact_text_not_empty = "Контактный текст не должен быть пустым"
    content_type_not_html = "Content-Type не text/html"

    # Consent / GDPR
    consent_count_wrong = "Количество consent-записей не совпадает"

    # Покрытие API
    coverage_out_of_range = "Покрытие вне допустимого диапазона"
    covered_known_gaps = "KNOWN_GAPS содержит уже покрытые пути"

    # CSP / безопасность
    csp_directive_missing = "CSP-директива отсутствует"
    csp_missing = "Заголовок CSP отсутствует"

    # Дерево / персоны
    delete_should_not_fire = "DELETE-запрос не должен был отправиться"
    demo_people_missing = "Демо-персоны отсутствуют в тенанте"
    display_name_invalid = "Display name невалиден"

    # UI / вёрстка
    element_overflows_viewport = "Элемент выходит за пределы viewport"
    empty_page_title = "Заголовок страницы пуст"
    horizontal_scroll_detected = "Обнаружен горизонтальный скролл"
    touch_target_too_small = "Touch-target меньше минимального размера"
    tab_overflows_viewport = "Вкладка выходит за пределы viewport"

    # i18n
    error_not_russian = "Текст ошибки не на русском языке"
    html_lang_wrong = "Атрибут html lang не совпадает"
    lang_switcher_not_empty = "Переключатель языка не должен быть пустым"
    lang_switcher_not_hidden = "Переключатель языка не скрыт"
    rub_symbol_missing = "Символ рубля отсутствует"

    # Feature flags
    ff_data_flag_wrong = "Значение data-flag feature flag не совпадает"
    ff_db_not_updated = "Feature flag не обновился в БД"
    ff_group_count_wrong = "Количество групп feature flags не совпадает"
    ff_group_missing = "Группа feature flags отсутствует"
    ff_provider_not_mentioned = "Провайдер не упомянут в feature flag"
    ff_toggle_state_wrong = "Состояние toggle feature flag не совпадает"
    ff_tooltip_empty = "Tooltip feature flag пуст"

    # Аналитика / метрики
    bounce_rate_out_of_range = "Bounce rate вне допустимого диапазона"
    fill_ratio_out_of_range = "Fill ratio вне допустимого диапазона"
    filter_order_wrong = "Порядок фильтров не совпадает"
    funnel_steps_wrong = "Шаги воронки не совпадают"
    matrix_dimensions_wrong = "Размерность матрицы не совпадает"
    metric_key_missing = "Ключ метрики отсутствует"
    metric_type_wrong = "Тип метрики не совпадает"
    retention_buckets_wrong = "Retention-бакеты не совпадают"
    retention_show_type_wrong = "Тип show в retention не совпадает"
    year_less_than_month = "Значение year меньше month"

    # GEDCOM
    gedcom_leaked_foreign_data = "GEDCOM содержит чужие данные"
    gedcom_missing_own_data = "GEDCOM не содержит собственные данные"
    tree_changed_after_import = "Дерево изменилось после импорта"
    footer_ornament_wrong = "Орнамент в footer не совпадает"

    # Тарифы / подписка
    forbidden_tier_visible = "Запрещённый тариф виден"
    free_tier_not_zero = "Бесплатный тариф не нулевой"
    price_invalid = "Цена невалидна"
    subscribe_status_wrong = "Статус подписки не совпадает"
    tier_missing = "Тариф отсутствует"
    tiers_hidden_wrong = "Видимость тарифов не совпадает"
    tiers_not_sorted = "Тарифы не отсортированы по цене"

    # Формы
    form_method_not_post = "Метод формы не POST"
    native_select_not_synced = "Native select не синхронизирован с custom"

    # Безопасность / утечки
    foreign_person_visible = "Чужая персона видна в тенанте"
    geo_coordinates_leaked = "Гео-координаты утекли"
    inline_handlers_found = "Найдены inline event handlers"
    internal_tables_leaked = "Внутренние таблицы утекли в ответ"
    ipv4_leaked = "IPv4-адрес утёк"
    injection_status_unexpected = "Статус ответа на инъекцию неожидан"
    person_id_leaked = "ID персоны утёк в чужой тенант"
    person_name_leaked = "Имя персоны утекло"
    pii_leaked = "Персональные данные утекли"
    session_id_leaked = "Session ID утёк"
    server_error_on_injection = "Серверная ошибка при инъекции"
    sql_error_leaked_in_body = "SQL-ошибка утекла в тело ответа"
    sql_injection_changed_row_count = "Число персон изменилось после SQL-инъекции"
    demo_person_missing_after_injection = "Демо-персона исчезла после инъекции"
    timing_leak = "Обнаружена timing-утечка"
    hsts_on_http = "HSTS-заголовок на HTTP (должен быть только HTTPS)"
    permissions_policy_wrong = "Permissions-Policy не совпадает"
    security_header_wrong = "Security-заголовок не совпадает"

    # Здоровье / статус
    health_status_wrong = "Статус health-endpoint не совпадает"
    static_assets_failed = "Статические ресурсы не загрузились"

    # HTML / a11y
    html5_validity_passed = "HTML5 валидация пройдена (ожидался провал)"
    link_target_wrong = "Target ссылки не совпадает"
    no_headings_found = "Заголовки h1-h6 не найдены"
    raw_markdown_lines = "Обнаружены сырые строки Markdown"
    raw_markdown_links = "Обнаружены сырые Markdown-ссылки"

    # JS-ошибки
    js_errors_on_page = "JS-ошибки на странице"
    network_errors_on_page = "Сетевые ошибки на странице"

    # MFA
    mfa_configured_wrong = "Состояние configured MFA не совпадает"
    mfa_fresh_wrong = "Состояние fresh MFA не совпадает"
    mfa_otpauth_wrong = "otpauth URI не совпадает"
    mfa_secret_wrong = "MFA secret не совпадает"
    mfa_valid_until_missing = "valid_until отсутствует в MFA-ответе"
    mfa_verify_status_wrong = "Статус MFA verify не совпадает"
    recovery_code_format_wrong = "Формат recovery-кода неверный"
    recovery_not_invalidated = "Recovery-код не инвалидирован после использования"
    recovery_redeem_status_wrong = "Статус redeem recovery-кода не совпадает"
    recovery_unused_wrong = "Количество неиспользованных recovery-кодов не совпадает"

    # Step-up
    step_up_audit_missing = "Step-up запись в аудит-логе отсутствует"
    step_up_method_wrong = "Метод step-up не совпадает"
    step_up_required_missing = "step_up_required отсутствует в ответе"

    # Orbit / навигация
    orbit_card_missing_pid = "Orbit-карточка без person-id"
    own_person_missing = "Собственная персона не найдена"
    own_tenant_missing = "Собственный тенант не найден"
    page_navigation_failed = "Навигация на страницу не удалась"
    platform_navigation_failed = "Навигация на платформу не удалась"
    person_must_have_id = "Персона должна иметь ID"
    relationship_not_removed = "Связь не удалена"
    search_placeholder_wrong = "Placeholder поиска не совпадает"
    result_text_not_empty = "Текст результата не должен быть пустым"
    slug_collision = "Коллизия slug между тенантами"
    tenants_must_differ = "Тенанты должны отличаться"

    # API coverage
    stale_known_gaps = "KNOWN_GAPS содержит устаревшие записи"
    unknown_endpoints_found = "Обнаружены неизвестные эндпоинты"
    schema_drift_detected = "Поля Pydantic-модели отсутствуют в OpenAPI-схеме бэкенда"
    schema_not_found = "Pydantic-модель не найдена в OpenAPI-схемах бэкенда"

    # WebAuthn
    no_webauthn_credentials_missing = "no_webauthn_credentials отсутствует в ответе"
    webauthn_auth_status_wrong = "Статус WebAuthn аутентификации не совпадает"
    webauthn_btn_missing = "Кнопка WebAuthn отсутствует"
    webauthn_credential_count_wrong = "Количество WebAuthn credentials не совпадает"
    webauthn_label_wrong = "Label WebAuthn credential не совпадает"
    webauthn_list_not_empty = "Список WebAuthn credentials не пуст"
    webauthn_option_missing = "Опция WebAuthn отсутствует"
    webauthn_register_failed = "Регистрация WebAuthn не удалась"
    webauthn_valid_until_missing = "valid_until отсутствует в WebAuthn-ответе"

    # XSS
    xss_handler_rendered = "XSS event handler отрендерился"
    xss_script_rendered = "XSS script отрендерился"
    xss_executed = "XSS payload исполнился в браузере (появился JS-диалог)"
    xss_payload_not_stored = "XSS payload не сохранён как литеральный текст"

    # Playwright response
    pw_response_status_wrong = "Статус Playwright-ответа не совпадает"
    pw_response_not_ok = "Playwright-ответ не ok"


# ─────────────────────────────────────────────────────────────────────────
# Locale resolver
# ─────────────────────────────────────────────────────────────────────────


def t(value: str | dict[str, Any]) -> Any:
    """Pick the active-locale string (or pass through if not localised).

    Полиморфный резолвер каталога: возвращает значение по активной локали
    (str для большинства строк, tuple для Brand.TITLE_FRAGMENTS) — отсюда
    `-> Any` (сужение через @overload ломается на инвариантности dict).
    """
    if isinstance(value, dict):
        if LOCALE not in value:
            raise KeyError(
                f"locale {LOCALE!r} not defined for value with keys {list(value)}; "
                "extend src/texts.py"
            )
        return value[LOCALE]
    return value
