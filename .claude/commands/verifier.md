Ты — агент верификации. Проверяй с недоверием: не верь что код работает, пока не убедишься.

## Фаза 1 — Автоматические проверки (запусти ВСЕ)

```bash
# 1. Drift-lint (Rule 5, 9, 10)
python scripts/check_drift.py

# 2. Ruff (стиль + ошибки)
ruff check tests/ tests/pages/

# 3. Ruff format check
ruff format --check tests/ tests/pages/

# 4. Import validation
python -c "
import importlib, pathlib, sys
sys.path.insert(0, '.')
errors = []
for f in sorted(pathlib.Path('tests').rglob('*.py')):
    if f.name == '__init__.py': continue
    mod = str(f).replace('/', '.').removesuffix('.py')
    try: importlib.import_module(mod)
    except Exception as e:
        if 'backend_url' not in str(e).lower(): errors.append(f'{f}: {e}')
for e in errors: print(f'ERROR: {e}')
if not errors: print('All imports OK')
"
```

Если что-то из этого падает — зафиксируй и продолжай.

## Фаза 2 — Grep-проверки по правилам (запусти ВСЕ)

```bash
# Rule 13: нет xfail/skip
grep -rn "xfail\|pytest.mark.skip\|pytest.skip\|xpass" tests/ --include="test_*.py"

# Rule 24: expect() без ErrMsg
grep -rn 'expect(' tests/ --include="test_*.py" | grep -v "ErrMsg\|expect_response\|page.expect_\|context.expect_\|#.*expect\|\"\"\"" | grep -v "page\.on"

# Rule 10: raw /api/ строки
grep -rn '"/api/' tests/ --include="test_*.py" | grep -v "test_api_coverage.py\|# noqa\|\"\"\"" | grep -v '^\s*#'

# Rule 21: data-testid без обоснования
grep -rn 'data-testid\|locator("#' tests/ --include="test_*.py" | grep -v "no semantic\|# noqa" | head -20

# Rule 5: хардкожённые таймауты
grep -rn "timeout=" tests/ --include="test_*.py" | grep -v "TIMEOUTS\|# noqa\|\"\"\"" | head -10

# Rule 20: navigate_to() без захвата результата
grep -rn "pages.navigate_to\|anon_pages.navigate_to" tests/ --include="test_*.py" | grep -v "= " | head -10

# Rule 34: голые assert в тестах (должно быть 0)
grep -rn "^\s*assert " tests/ --include="test_*.py" | grep -v "\"\"\"" | wc -l

# Rule 34: inline строки в should.* (должны быть через ErrMsg)
grep -rn "should\.\w*(.*\"" tests/ --include="test_*.py" | grep -v "ErrMsg\|\"\"\"" | head -10

# Rule 36: длинные docstrings (>2 строки)
python3 -c "
import re, pathlib
for f in sorted(pathlib.Path('tests').rglob('test_*.py')):
    text = f.read_text()
    for m in re.finditer(r'\"\"\"(.+?)\"\"\"', text, re.DOTALL):
        lines = m.group().count(chr(10))
        if lines > 2: print(f'{f}: docstring {lines+1} lines')
" | head -10

# Rule 35: низкоуровневые Playwright-вызовы в тестах (должно быть 0)
grep -rn "\.locator(\|\.get_attribute(\|\.click(\|\.fill(\|\.wait_for_load_state\|\.wait_for(" tests/ --include="test_*.py" | grep -v "conftest\|# \|\"\"\"" | wc -l

# Rule 36: standalone helpers вместо POM-методов
grep -rn "auth_name(\|logout_link(\|login_link(\|wait_for_authed_shell(" tests/ --include="test_*.py" | wc -l

# Rule 37: eager locators в POM __init__ (должно быть 0)
grep -rn "self\.\w* = .*locator\|self\.\w* = .*get_by_" pages/ --include="*.py" | grep -v "@property\|def " | wc -l

# Rule 37: inline locator strings в POM-методах (должно быть 0)
grep -rn "\.locator(\|\.get_by_" pages/ --include="*.py" | grep -v "return \|@property\|_CS_\|_ORBIT\|format(\|# " | grep -v '"""' | wc -l

# Rule 25: assert в Page Objects (кроме precondition)
grep -rn "^\s*assert " pages/ --include="*.py" | grep -v "# precondition" | head -10

# Rule 17: файлы без step()
comm -23 <(find tests/ -name "test_*.py" | sort) <(grep -rln "with step(" tests/ --include="test_*.py" | sort)
```

## Фаза 3 — Ручная верификация изменённых файлов

Для каждого файла из `$ARGUMENTS` (или `git diff --name-only HEAD~1`):

1. **Прочитай целиком** — не только diff
2. **Rule 1** — тест верифицирует, не просто «страница открылась»
3. **Rule 2** — линейный flow, нет if/else в тестах
4. **Rule 19** — type hints + docstring на public функциях
5. **Rule 20/23** — fluent chain, PageFactory
6. **Rule 17** — step() имена: подготовка/действие/проверка
7. **Rule 24** — ErrMsg подходит по смыслу (не generic для специфичных проверок)
8. **Rule 15** — shared state → serial маркировка

## Фаза 4 — Отчёт

```
## Результат верификации

### Автоматические проверки
- drift-lint: ✅/❌
- ruff: ✅/❌
- imports: ✅/❌
- format: ✅/❌

### Нарушения правил
| # | Правило | Файл:строка | Проблема |
|---|---------|-------------|----------|
| 1 | Rule N  | path:line   | описание |

### Ручная верификация
- [файл] — ✅/❌ (проблемы если есть)

### Вердикт
ГОТОВО К КОММИТУ / ТРЕБУЮТСЯ ПРАВКИ
```

$ARGUMENTS
