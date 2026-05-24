"""Assertion error messages — single source of truth.

Usage:
    expect(locator, ErrMsg.profile_dates_wrong).to_contain_text("1980")

Keeps test files clean: no inline Russian error descriptions.
"""

from __future__ import annotations


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
