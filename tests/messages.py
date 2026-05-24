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

from tests.settings import settings

_LOCALE = settings.locale


class _Catalogue:
    """Subclass and define attributes as `dict[locale, str]` or plain `str`.

    Plain `str` = same value across all locales (proper nouns like 'ЦАМО',
    structural strings like '0 HEAD').
    """


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
    RESET_PASSWORD = {"ru": "Сбросить пароль", "en": "Reset password"}
    WAITLIST_SUBMIT = {"ru": "Записаться в ранний доступ", "en": "Join early access"}


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
    LOGIN_LINK = Buttons.LOGIN
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
    # Confirm-button label — accepts consent and runs the enrichment.
    CONFIRM_LABEL = {"ru": "Запустить", "en": "Run"}


class Enrichment(_Catalogue):
    """Strings in the enrichment result UI (accept/revert into the card)."""

    # okLabel of the revert promptDialog (view-mode.js:268).
    REVERT_OK = {"ru": "Снять", "en": "Remove"}
    # Tooltip on disabled AI button when platform flag is off.
    BETA_KEYWORD = {"ru": "публичной бете", "en": "public beta"}
    # Disabled-button marker text (enrichment is "coming soon").
    COMING_SOON = {"ru": "скоро", "en": "soon"}


class Mfa(_Catalogue):
    """Strings in the 2FA settings panel — substring keywords on the
    status line ("✅ 2FA включена" / "❌ 2FA отключена")."""

    STATUS_ON = {"ru": "включена", "en": "enabled"}
    STATUS_OFF = {"ru": "отключена", "en": "disabled"}


class Onboarding(_Catalogue):
    """confirmDialog button labels for the demo-data actions (owner.js)."""

    CLEAR_DEMO_CONFIRM = {"ru": "Стереть", "en": "Erase"}
    KEEP_DEMO_CONFIRM = {"ru": "Использовать как шаблон", "en": "Use as template"}


class FamilyGroups(_Catalogue):
    """Profile family-group labels — used to scope `+`-buttons to a relation."""

    PARENTS = {"ru": "Родители", "en": "Parents"}
    SPOUSE = {"ru": "Супруг", "en": "Spouse"}  # Substring; matches «Супруг(а)»
    CHILDREN = {"ru": "Дети", "en": "Children"}
    SIBLINGS = {"ru": "Братья/сёстры", "en": "Siblings"}


class LinkedChip(_Catalogue):
    """Copy on the `link-existing-record` chip — FEATURE-PARENT-SEARCH-001.

    Substring keywords — assert chip semantics survive copy edits.
    """

    # Title row above the chip body («Привязка к существующей записи»).
    TITLE_KEYWORD = {"ru": "Привязка", "en": "Linked"}
    # Hint line under the body — narrows the semantic («…создаётся только связь»).
    HINT_KEYWORD = {"ru": "связь", "en": "relationship"}
    # The unlink button label.
    UNLINK = {"ru": "Отвязать", "en": "Unlink"}


class TestData(_Catalogue):
    """Fixed values supplied BY the test (not from product)."""

    SAMPLE_SITE_NAME = "Тестовая семья"
    GEDCOM_HEAD = "0 HEAD"
    DEMO_PERSON_ID = "demo-self"
    # Default `full_name` used by `signup_via_api` — also becomes the
    # tenant's display_name and the demo-self person's name.
    DEFAULT_FULL_NAME = "Тестовый Пользователь"
    # Fixture surname/given for add-relative tests — used as input AND
    # as assertion target (search the created person in the tree).
    ADD_REL_SURNAME = "Тестовый"
    ADD_REL_GIVEN = "Брат"
    # Source CRUD fixture data.
    SOURCE_NAME = "Архив 1"
    SOURCE_NAME_PATCHED = "Архив 1 (испр.)"


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


class Waitlist(_Catalogue):
    """Strings on the waitlist/overflow modal (signup.html)."""

    OVERFLOW_TITLE = {"ru": "Сейчас принимаем не всех", "en": "Not accepting everyone"}
    WAITLIST_KEYWORD = {"ru": "список ожидания", "en": "waiting list"}


class ConfirmDialog(_Catalogue):
    """Keyword fragments in the delete-person confirm modal."""

    IRREVERSIBLE = {"ru": "необратим", "en": "irreversible"}
    RELATIONS_KEYWORD = {"ru": "связ", "en": "relat"}


class RelationLabels(_Catalogue):
    """Orbit-card relation labels (parent role by gender)."""

    FATHER = {"ru": "отец", "en": "father"}
    MOTHER = {"ru": "мать", "en": "mother"}


class Labels(_Catalogue):
    """Form input labels — used in `get_by_label(...)`."""

    EMAIL = "Email"
    PASSWORD = {"ru": "Пароль", "en": "Password"}
    SITE_NAME = {"ru": "Название", "en": "Name"}
    FAMILY_NAME = {"ru": "Фамилия", "en": "Family name"}
    REGIONS = {"ru": "Регионы", "en": "Regions"}
    CONTACT_EMAIL = {"ru": "Контактный email", "en": "Contact email"}
    ABOUT = {"ru": "О проекте", "en": "About"}
    WAITLIST_EMAIL = {"ru": "Email для уведомления о запуске", "en": "Email for launch notification"}


class Placeholders(_Catalogue):
    """Placeholder text on input fields."""

    SEARCH = {"ru": "Поиск", "en": "Search"}
    SEARCH_TREE = {"ru": "Найти...", "en": "Find..."}


class AboutTab(_Catalogue):
    """Strings on the about-tab placeholder."""

    FAMILY_TREE_KEYWORD = {"ru": "семейное древо", "en": "family tree"}


# ─────────────────────────────────────────────────────────────────────────
# Resolver
# ─────────────────────────────────────────────────────────────────────────


def t(value):
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
