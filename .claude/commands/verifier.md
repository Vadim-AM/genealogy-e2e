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

# Rule 25: assert в Page Objects (кроме precondition)
grep -rn "^\s*assert " tests/pages/ --include="*.py" | grep -v "# precondition" | head -10

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
