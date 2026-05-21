"""Localised UI strings used by tests.

Single source of truth for every Russian-language text the suite asserts on
or selects by. When the product gains an English locale, switch via the
`E2E_LOCALE` env var (or expand `_LOCALES`).

Rationale: tests should not embed copy. Two reasons:
  1. Locale switch (ru → en) renames every visible string at once. With the
     catalogue, that's one file to edit. With inline literals, ~30% of the
     suite breaks at random places.
  2. Copy refactors in product (e.g. "Сохранить" → "Сохранить изменения") cause
     a single grep-and-replace here, not a tree-wide hunt.

Convention: every string is referenced as `Buttons.SAVE` / `Auth.WRONG_PWD`
etc., never inlined in tests. POM classes import from here too.

When the product adds `data-testid` to interactive elements, prefer those
over text-based locators — and the corresponding strings here are still
useful for assertions on visible copy (warning messages, error texts).
"""

from __future__ import annotations

import os


_LOCALE = os.environ.get("E2E_LOCALE", "ru")


class _Catalogue:
    """Subclass and define attributes as `dict[locale, str]` or plain `str`.

    Plain `str` = same value across all locales (proper nouns like 'ЦАМО',
    structural strings like '0 HEAD').
    """


class Buttons(_Catalogue):
    """Button names — used in `get_by_role("button", name=...)` until we
    move products to `data-testid`."""

    LOGIN = {"ru": "Войти", "en": "Sign in"}
    SAVE = {"ru": "Сохранить", "en": "Save"}
    CANCEL = {"ru": "Отмена", "en": "Cancel"}
    DELETE = {"ru": "Удалить", "en": "Delete"}
    EDIT = {"ru": "Редактировать", "en": "Edit"}
    CLOSE = {"ru": "Закрыть", "en": "Close"}
    ACCEPT = {"ru": "Принять", "en": "Accept"}
    REJECT = {"ru": "Отклонить", "en": "Reject"}
    ENRICH = {"ru": "Найти больше", "en": "Find more"}


class Links(_Catalogue):
    """Anchor / role=link names."""

    SIGNUP = {"ru": "Регистрация", "en": "Sign up"}
    FORGOT_PASSWORD = {"ru": "Забыли пароль", "en": "Forgot password"}


class Brand(_Catalogue):
    """Brand fragments expected in `<title>`. Match-any semantics: title
    must contain at least one fragment."""

    TITLE_FRAGMENTS = {
        "ru": ("Родословн", "Семейн", "древо"),
        "en": ("Genealogy", "Family", "tree"),
    }


class Invite(_Catalogue):
    """Strings on /invite-accept."""

    OWNER_WARNING = {
        "ru": "владелец",       # narrow keyword for "you are already the owner"
        "en": "owner",
    }
    # Title after fresh accept ("Готово!") — keyword substring.
    ACCEPT_SUCCESS_TITLE = {"ru": "Готово", "en": "Done"}
    # Title when invitee is already a member of this tenant.
    ALREADY_MEMBER_TITLE = {"ru": "уже здесь", "en": "already here"}
    # CTA on the page after accept — leads to the tree dashboard.
    OPEN_TREE_LINK = {"ru": "Открыть древо", "en": "Open tree"}
    # v2-Phase1 magic-link: an emailed invite opened by an anonymous
    # visitor is auto-accepted (backend creates a passwordless user) —
    # success copy "Вы добавлены в древо …".
    ADDED_TO_TREE = {"ru": "добавлены в древо", "en": "added to the tree"}
    # The login-prompt path now only fires for an *email-less* invite
    # (401): "Это приглашение требует входа."
    LOGIN_REQUIRED_MSG = {"ru": "требует входа", "en": "requires sign-in"}
    LOGIN_LINK = {"ru": "Войти", "en": "Sign in"}
    SIGNUP_LINK = {"ru": "зарегистрироваться", "en": "sign up"}


class PII(_Catalogue):
    """Owner personal data that must NOT leak to public pages.

    Same across locales (proper nouns).
    """

    OWNER_FAMILY_NAMES = ("Данилюк", "Макаров")


class AiConsent(_Catalogue):
    """Fragments expected in the GDPR/152-FZ consent confirm() dialog
    rendered by `js/components/enrichment-modal.js` before the first AI
    enrichment request. Substring match — survives copy edits as long as
    the legal core stays."""

    # Brand of the upstream LLM. Locale-independent (proper noun).
    PROVIDER = "Anthropic"
    # Privacy reference — required by 152-FZ Art. 9 §1 / GDPR Art. 7
    # (active consent must reference data subjects' privacy). Wave-9 переписал
    # текст modal'а — раньше было «политика конфиденциальности», теперь
    # «защищает их приватность». Substring match на корень слова.
    POLICY_KEYWORD = {"ru": "приватность", "en": "privacy"}
    # Localised reference to what data is sent. Wave-9 переписал modal —
    # вместо positive-list «Передаётся:» теперь negative-list через
    # фразу «на основе данных карточки» (что обрабатывается) и
    # «Данные живущих родственников исключаются» (что НЕ отправляется).
    SHARED_DATA_KEYWORD = {"ru": "данных карточки", "en": "data from the card"}
    # Decline-button label in the consent modal (enrichment-modal.js:112).
    DECLINE_LABEL = {"ru": "Не сейчас", "en": "Not now"}


class FamilyGroups(_Catalogue):
    """Profile family-group labels — used to scope `+`-buttons to a relation."""

    PARENTS = {"ru": "Родители", "en": "Parents"}
    SPOUSE = {"ru": "Супруг", "en": "Spouse"}  # Substring; matches «Супруг(а)»
    CHILDREN = {"ru": "Дети", "en": "Children"}
    SIBLINGS = {"ru": "Братья/сёстры", "en": "Siblings"}


class TestData(_Catalogue):
    """Fixed values supplied BY the test (not from product)."""

    SAMPLE_SITE_NAME = "Тестовая семья"
    GEDCOM_HEAD = "0 HEAD"
    DEMO_PERSON_ID = "demo-self"
    # Default `full_name` used by `signup_via_api` — also becomes the
    # tenant's display_name and the demo-self person's name.
    DEFAULT_FULL_NAME = "Тестовый Пользователь"


class GedcomImport(_Catalogue):
    """UI labels shown by the GEDCOM import widget. Substring match —
    survives copy edits as long as semantic core stays."""

    # DONE-summary mentions skipped (already-existing) rows count.
    SKIPPED_LABEL = {"ru": "Пропущено", "en": "Skipped"}
    # alertDialog when no `.ged` extension on chosen file.
    FILE_EXTENSION_HINT = ".ged"
    # alertDialog for 0-byte file.
    EMPTY_LABEL = {"ru": "пустой", "en": "empty"}
    # alertDialog for > size-limit file.
    TOO_LARGE_LABEL = {"ru": "слишком большой", "en": "too large"}


class AgeValidation(_Catalogue):
    """Substring match for backend's parent-age validation error."""

    PARENT_AGE_KEYWORD = {"ru": "Возраст родителя", "en": "Parent age"}


# ─────────────────────────────────────────────────────────────────────────
# Resolver
# ─────────────────────────────────────────────────────────────────────────


def t(value):  # noqa: ANN001
    """Pick the active-locale string (or pass through if not localised).

    Examples:
        t(Buttons.LOGIN)            → "Войти"  (locale=ru)
        t(Brand.TITLE_FRAGMENTS)    → ("Родословн", "Семейн", "древо")
        t(TestData.GEDCOM_HEAD)     → "0 HEAD"  (plain str passes through)
    """
    if isinstance(value, dict):
        if _LOCALE not in value:
            raise KeyError(
                f"locale {_LOCALE!r} not defined for value with keys {list(value)}; "
                "extend tests/messages.py"
            )
        return value[_LOCALE]
    return value
