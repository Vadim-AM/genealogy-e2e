"""TC-10.02 — Map: украинский флаг в leaflet attribution скрыт.

BUG-003 (closed): leaflet `<a class="leaflet-attribution-flag">` показывал
флажок справа от ссылки «Leaflet» в bottom-right углу карты. Для
русскоязычной аудитории — политически чувствительно.

Fix: оба стиля `/css/leaflet.css` и `/fonts/leaflet.css` имеют
`.leaflet-attribution-flag { display: none !important }`. Этот тест —
регрессионный pin: при любом upstream-обновлении leaflet или потере
правила тест ловит регрессию **до** релиза.

Map tab — auth-gated (`AUTHED_TABS` в TreePage), поэтому используется
`owner_page` (logged-in browser context).
"""

from __future__ import annotations

from playwright.sync_api import Page, expect


def test_map_attribution_flag_is_hidden_on_logged_in_owner(owner_page: Page):
    """TC-10.02: после переключения на map tab — leaflet рендерится,
    `.leaflet-attribution-flag` имеет computed display=none.

    Если leaflet не отрендерил attribution-flag элемент вовсе — это тоже
    valid (флаг и так не виден). Тест fail'ится только когда элемент
    есть И его computed display != "none".
    """
    owner_page.goto("/")
    owner_page.wait_for_load_state("domcontentloaded")

    # Switch to map tab. AUTHED_TABS enabled только для logged-in юзеров —
    # owner_page фикстура даёт authenticated context.
    owner_page.locator('[data-tab="map"]').click()

    # Leaflet lazy-loaded (см. index.html mapTab loader, BUG-003 history) —
    # дождаться сначала корневого .leaflet-container, потом attribution.
    # Без этого тест flaky на медленной первичной загрузке (запуск
    # после batch'а других тестов).
    expect(owner_page.locator(".leaflet-container")).to_be_visible()
    attribution = owner_page.locator(".leaflet-control-attribution")
    expect(attribution).to_be_visible()

    # leaflet-attribution-flag — child элемент внутри attribution. Может
    # отсутствовать (если leaflet >=1.9 убрал в upstream), либо быть
    # скрыт через CSS.
    flags = owner_page.locator(".leaflet-attribution-flag").all()
    if not flags:
        # leaflet upstream удалил элемент — наш CSS-fix больше не нужен,
        # но регрессии нет (флага не видно по дефолту).
        return

    for idx, flag in enumerate(flags):
        display = flag.evaluate("(el) => getComputedStyle(el).display")
        assert display == "none", (
            f"BUG-003 regression: leaflet-attribution-flag[{idx}] "
            f"computed display={display!r}, expected 'none'. "
            f"Проверь /css/leaflet.css и /fonts/leaflet.css — правило "
            f"`.leaflet-attribution-flag {{ display: none !important }}` "
            f"должно быть в обоих."
        )
