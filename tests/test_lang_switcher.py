"""TC-19.* — Lang switcher до раскатки публичной локализации СКРЫТ.

Контракт (Vadim 2026-05-02 решение в js/i18n/index.js:22):
`_LOCALE_PUBLIC_RELEASE = false` → setLang() — no-op,
getAvailableLangs() возвращает только ['ru'], lang-switcher container
рендерится с `display:none` (`js/components/lang-switcher.js:32`).

Этот тест — pin текущего design decision. Когда EN-локализация будет
включена (commit `_LOCALE_PUBLIC_RELEASE = true`) — тест начнёт fail'ить,
и нужно будет переписать на positive проверки TC-19.01..03 (switcher
показывает кнопки РУС/EN, click меняет язык, localStorage genealogy_lang
persist).

Связано с BUG-008 (deferred): public pages не локализуются в EN.
Закрытие BUG-008 = включение этого feature flag + перевод signup/login.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect


def test_lang_switcher_containers_are_hidden_when_only_one_language(page: Page):
    """TC-19.*-disabled: `.lang-switcher` контейнеры (в header и footer)
    пустые и display:none пока `_LOCALE_PUBLIC_RELEASE=false`.
    Lang-switcher.js при langs.length<=1 устанавливает
    `target.style.display = 'none'` и `innerHTML = ''`.

    Ловит и баг с дублированным id="langSwitcher" — HTML невалидный
    (два элемента с одинаковым id), но lang-switcher должен иметь
    target=один из них; реально initLangSwitcher вызывается дважды
    (init.js + footer init), поэтому оба контейнера должны быть скрыты.
    Селектор по классу — устойчив к этой особенности.
    """
    page.goto("/")
    page.wait_for_load_state("domcontentloaded")

    containers = page.locator(".lang-switcher").all()
    assert containers, "не найдено ни одного .lang-switcher container на /"

    for idx, container in enumerate(containers):
        inner_html = container.evaluate("(el) => el.innerHTML.trim()")
        display = container.evaluate("(el) => getComputedStyle(el).display")
        assert inner_html == "", (
            f".lang-switcher[{idx}] должен быть пустым при "
            f"_LOCALE_PUBLIC_RELEASE=false; innerHTML={inner_html[:80]!r}"
        )
        assert display == "none", (
            f".lang-switcher[{idx}] должен быть display:none пока "
            f"мультиязычность не включена; computed display={display!r}"
        )


def test_html_lang_attribute_is_ru(page: Page):
    """initLang() форс-резолвит в 'ru' (igноривает localStorage / navigator).
    Это контракт: пока локализация отложена, документ всегда RU.
    """
    page.goto("/")
    page.wait_for_load_state("domcontentloaded")
    html_lang = page.evaluate("() => document.documentElement.lang")
    assert html_lang == "ru", (
        f"document.documentElement.lang должен быть 'ru' пока "
        f"_LOCALE_PUBLIC_RELEASE=false; got {html_lang!r}"
    )


def test_localstorage_genealogy_lang_seed_does_not_change_active_lang(page: Page):
    """setLang() — no-op при отключённой локализации. Pre-seed
    `localStorage.genealogy_lang='en'` не должен переключить UI на EN.

    Pin'ит решение Vadim 2026-05-02: пока EN-словарь не отрелижен публично,
    ни одна точка входа (localStorage / navigator.language / config) не
    должна включать EN — иначе пользователь увидит частично-переведённую
    версию (BUG-008).
    """
    # Pre-seed localStorage ДО навигации, через init script
    page.add_init_script("try { localStorage.setItem('genealogy_lang', 'en'); } catch (e) {}")
    page.goto("/")
    page.wait_for_load_state("domcontentloaded")

    html_lang = page.evaluate("() => document.documentElement.lang")
    assert html_lang == "ru", (
        f"localStorage.genealogy_lang='en' не должен переключать lang пока "
        f"_LOCALE_PUBLIC_RELEASE=false; got {html_lang!r}"
    )
