"""Coverage gate — backend API surface must not silently drift from the suite."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import re
import warnings
from http import HTTPStatus

import allure
import httpx
from pydantic import BaseModel as PydanticBaseModel

from api import routes
from assertions.base import should
from framework.response import expect_response
from framework.step import step
from src.texts import ErrMsg

# Принятые пробелы покрытия — реестр долга. Каждая строка помечена
# группой roadmap. Пробел закрывается новым journey-тестом, проверяющим
# endpoint + константой в `tests/_core/api_paths.py`; после этого строка
# удаляется. НЕ добавляйте строку только чтобы заглушить gate для
# нового endpoint'а без указания, какой journey его покроет.
KNOWN_GAPS: frozenset[str] = frozenset()
# Пусто: каждый backend `/api/*` путь покрыт journey- или
# backend-invariant тестом. Новые endpoint'ы должны попадать сюда с
# roadmap-тегом, или (предпочтительно) с покрывающим тестом в том же изменении.


_PARAM_RE = re.compile(r"\{[^}]+\}")


def _normalise(path: str) -> str:
    """Collapse a parameterised path to canonical form: `{anything}` → `{}`."""
    return _PARAM_RE.sub("{}", path)


def _catalogue_paths() -> set[str]:
    """Every `/api/*` path the suite knows via `tests._core.api_paths`."""
    paths: set[str] = set()
    for name, value in vars(routes).items():
        if name.startswith("_"):
            continue
        if isinstance(value, str) and value.startswith("/api/"):
            paths.add(_normalise(value))
        elif callable(value) and not isinstance(value, type):
            argc = len(inspect.signature(value).parameters)
            if argc == 0:
                continue
            rendered = value(*(["{X}"] * argc))
            if isinstance(rendered, str) and rendered.startswith("/api/"):
                paths.add(_normalise(rendered))
    return paths


def _backend_api_paths(base_url: str) -> set[str]:
    """Every `/api/*` path from the backend's live OpenAPI schema."""
    r = httpx.get(f"{base_url}/openapi.json")
    expect_response(
        r,
        label="GET /openapi.json (boot with GENEALOGY_DOCS_ENABLED=1)",
    ).status(HTTPStatus.OK)
    spec = r.json()
    return {
        _normalise(path) for path in spec["paths"] if path.startswith("/api/") and not path.startswith("/api/_test/")
    }


@allure.title("Покрытие: все backend API-пути известны каталогу тестов")
def test_every_backend_api_path_is_known(base_url: str) -> None:
    """Every backend `/api/*` endpoint is in the routes catalogue or `KNOWN_GAPS`."""
    with step("действие: сравнить backend OpenAPI с каталогом API"):
        backend = _backend_api_paths(base_url)
        catalogue = _catalogue_paths()
        unknown = backend - catalogue - KNOWN_GAPS

    with step("проверка: нет неизвестных эндпоинтов"):
        should.be_empty(unknown, ErrMsg.unknown_endpoints_found)


@allure.title("Покрытие: KNOWN_GAPS не содержит устаревших записей")
def test_known_gaps_not_stale(base_url: str) -> None:
    """`KNOWN_GAPS` must not rot."""
    with step("действие: проверить KNOWN_GAPS на устаревшие записи"):
        backend = _backend_api_paths(base_url)
        catalogue = _catalogue_paths()

    with step("проверка: нет удалённых upstream и нет уже покрытых"):
        removed_upstream = KNOWN_GAPS - backend
        should.be_empty(removed_upstream, ErrMsg.stale_known_gaps)
        now_covered = KNOWN_GAPS & catalogue
        should.be_empty(now_covered, ErrMsg.covered_known_gaps)


# ─────────────────────────────────────────────────────────────────────────
# Schema drift — field-level contract check
# ─────────────────────────────────────────────────────────────────────────

_SKIP_MODELS = frozenset(
    {
        "PersonCreate",  # request model, not in OpenAPI responses
        "EmailResponse",  # mock-sender internal, not a public schema
        "TenantInfo",  # nested model, not a top-level schema
        "AuditLogItem",  # nested inside AuditLogResponse
        "ShareListItem",  # nested inside ShareListResponse
        "TenantOverrideItem",  # nested inside response
    }
)


def _discover_response_models() -> dict[str, set[str]]:
    """Discover Pydantic response models with extra='allow' in models/."""
    import models

    result: dict[str, set[str]] = {}
    for info in pkgutil.iter_modules(models.__path__):
        mod = importlib.import_module(f"models.{info.name}")
        for name, cls in vars(mod).items():
            if (
                isinstance(cls, type)
                and issubclass(cls, PydanticBaseModel)
                and cls is not PydanticBaseModel
                and name not in _SKIP_MODELS
            ):
                extra_val = cls.model_config.get("extra")
                if extra_val is None:
                    # Pydantic v1 fallback: check inner Config class.
                    config_cls = getattr(cls, "Config", None)
                    if config_cls:
                        extra_val = getattr(config_cls, "extra", None)
                if extra_val != "allow":
                    continue
                result[name] = set(cls.model_fields.keys())
    return result


def _openapi_schema_fields(spec: dict, schema_name: str) -> set[str] | None:
    """Extract field names from an OpenAPI schema by name."""
    schemas = spec.get("components", {}).get("schemas", {})
    schema = schemas.get(schema_name)
    if schema is None:
        return None
    return set(schema.get("properties", {}).keys())


@allure.title("Дрифт схемы: поля моделей соответствуют OpenAPI")
def test_api_schema_drift(base_url: str) -> None:
    """Every field in our Pydantic response models exists in the OpenAPI schema."""
    with step("подготовка: загрузить OpenAPI спецификацию"):
        r = httpx.get(f"{base_url}/openapi.json")
        expect_response(r, label="GET /openapi.json").status(HTTPStatus.OK)
        spec = r.json()

    with step("подготовка: обнаружить response-модели"):
        model_map = _discover_response_models()
        should.not_empty(model_map, "response models должны быть обнаружены")

    drifted_fields: list[str] = []
    missing_schemas: list[str] = []

    with step("действие: проверить поля каждой модели"):
        for model_name, our_fields in sorted(model_map.items()):
            openapi_fields = _openapi_schema_fields(spec, model_name)

            if openapi_fields is None:
                missing_schemas.append(model_name)
                continue

            removed = our_fields - openapi_fields
            if removed:
                drifted_fields.append(f"{model_name}: {sorted(removed)}")

            added = openapi_fields - our_fields
            if added:
                warnings.warn(
                    f"OpenAPI schema {model_name!r} has fields not in our model: {sorted(added)}",
                    stacklevel=1,
                )

    with step("проверка: нет дрифта полей"):
        should.be_empty(drifted_fields, ErrMsg.schema_drift_detected)

    with step("информация: не найденные схемы"):
        if missing_schemas:
            warnings.warn(
                f"Models not found in OpenAPI schemas (name mismatch?): {sorted(missing_schemas)}",
                stacklevel=1,
            )
