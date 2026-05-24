# Backlog: архитектурный техдолг e2e suite

Выявлено при ревью 2026-05-23. Целевое состояние:
- **API-тесты** → паттерны из `account_autotests`: Pydantic-модели для response, структурированные хелперы, ассерты через модели.
- **UI-тесты** → паттерны из `account_ui_autotests`: в тестах только высокоуровневые функции, всё остальное в PO. Локаторы как переменные. Страницы как фикстуры.

---

## 1. Куча текста в тестах

**Проблема:** Тестовые функции содержат длинные inline-строки, docstring'ы, комментарии. Тест должен читаться как сценарий, не как эссе.

**Целевое:** Убрать многострочные docstring'ы из test-функций. Оставить `@allure.title()` + 1 строку `"""F-XX-N: ..."""`. Всё остальное — в CLAUDE.md или test-plan.

---

## 2. Прямые API-вызовы в тестах

**Проблема:** Тесты делают `api.get(API.TREE)`, `api.post(API.PEOPLE, json={...})`, `api.patch(API.person(pid), json={...})` напрямую. Payload собирается inline.

**Целевое:** API-вызовы через типизированные хелперы:
```python
# плохо
r = api.post(API.PEOPLE, json={"id": pid, "name": name, "branch": "paternal", "gender": "m"})

# хорошо
person = tree_api.create_person(api, pid=pid, name=name)
```

---

## 3. Голые assert'ы без моделей

**Проблема:** `assert r.json()["tenant_slug"] == ...` — ручной доступ к JSON без валидации структуры. При изменении API контракта ломается по KeyError, не по assertion.

**Целевое:** Pydantic-модели для API response'ов (как в account_autotests):
```python
class PersonResponse(BaseModel):
    id: str
    name: str
    branch: str
    gender: str

person = PersonResponse.model_validate(r.json())
assert person.name == expected_name
```

---

## 4. Захардкоженные URL страниц

**Проблема:** `page.goto("/owner")`, `page.goto("/#/p/demo-self")`, `page.goto(f"/invite-accept?token={t}")` — URL разбросаны по тестам.

**Целевое:** Все URL в POM'ах. `BasePage.URL` уже есть, но тесты обходят его. `page.goto()` вызывается только через POM:
```python
# плохо
page.goto(f"/#/p/{person_id}")

# хорошо
ProfilePanel.navigate_to(page, person_id)
```

---

## 5. Текст (русский) в тестах

**Проблема:** `expect(panel.title).to_contain_text("Андрей")`, `has_text="Сергей"` — русские строки inline в тестах.

**Целевое:** Все UI-строки через `tests/messages.py`. Тестовые данные (имена персон) через `tests/constants.py::TestData`.

---

## 6. Локаторы в тестах (не в PO)

**Проблема:** Тесты содержат `page.locator('[data-testid="profile-family-group"]')`, `panel.container.locator('[data-testid="profile-dates"]')` — локаторы вне Page Objects.

**Целевое:** Все локаторы — атрибуты POM. Тест обращается к `panel.dates`, `panel.family_group("Родители")`, не к raw locators.

---

## 7. API-вызовы не используют Pydantic-модели

**Проблема:** Request payload собирается как `dict` inline. Response парсится через `.json()["key"]`. Нет валидации контракта.

**Целевое:** Pydantic-модели для request/response:
- `tests/models/person.py` — PersonCreate, PersonResponse, PersonPatch
- `tests/models/auth.py` — SignupRequest, LoginResponse, etc.
- `tests/models/tree.py` — TreeResponse, RelationshipResponse

---

## 8. Организация: в папке tests/ всё подряд

**Проблема:** `tests/response.py`, `tests/step.py`, `tests/api_paths.py`, `tests/constants.py`, `tests/messages.py`, `tests/settings.py`, `tests/timeouts.py` — инфраструктурные модули лежат рядом с тестами.

**Целевое:** Вынести в `tests/infra/` или `tests/_core/`:
```
tests/
├── _core/          # response, step, api_paths, constants, messages, settings, timeouts
├── _fixtures/      # глобальные фикстуры
├── _data/          # тестовые данные
├── _models/        # Pydantic модели API контрактов
├── pages/          # Page Objects
├── helpers/        # доменные хелперы
├── auth/           # тесты
├── tree/           # тесты
└── ...
```

---

## 9. JSON-фикстуры лежат в tests/fixtures/

**Проблема:** `tests/fixtures/ai_responses.json` — статический JSON лежит среди fixture-модулей.

**Целевое:** JSON-данные → `tests/_data/fixtures/ai_responses.json`. Директория `tests/fixtures/` → переименовать или объединить с `tests/_data/`.

---

## 10. UI-тесты: в тестах не только высокоуровневые функции

**Проблема:** UI-тесты содержат low-level Playwright вызовы: `page.wait_for_load_state()`, `page.locator(...)`, `expect(...)` на raw locators.

**Целевое (из account_ui_autotests):** В тесте только высокоуровневые функции PO:
```python
# плохо
page.goto("/login")
page.locator("#email").fill("test@test.com")
page.locator("#loginBtn").click()
expect(page.locator("#msg")).not_to_have_text("")

# хорошо
login_page = LoginPage(page)
login_page.goto()
login_page.login("test@test.com", "password")
login_page.expect_error()
```

---

## 11. Страницы не передаются как фикстуры

**Проблема:** Тесты создают POM inline: `tree = TreePage(page).goto()`, `signup = SignupPage(page)`.

**Целевое (из account_ui_autotests):** POM'ы передаются как pytest-фикстуры:
```python
@pytest.fixture
def login_page(owner_page) -> LoginPage:
    return LoginPage(owner_page).goto()

def test_login(login_page: LoginPage):
    login_page.login(email, password)
```

---

## Приоритет

1. **Pydantic-модели** (#3, #7) — самый высокий ROI, ловит API-drift на этапе парсинга
2. **Локаторы в PO** (#6) — убирает fragility из тестов
3. **API-хелперы** (#2) — убирает дублирование payload'ов
4. **Страницы как фикстуры** (#11) — чистит тесты
5. **Реорганизация** (#8, #9) — cosmetic но важно для onboarding
6. **Текст/URL cleanup** (#4, #5, #10) — последовательно при касании файлов
