"""Owner UI: настройки, экспорт GEDCOM/ZIP."""

from __future__ import annotations

import io
import zipfile
from typing import TYPE_CHECKING

import allure
from playwright.sync_api import Page, expect

from api import routes, site_api
from assertions.base import should
from config.timeouts import TIMEOUTS
from framework.response import expect_response
from framework.step import step
from pages.owner_page import OwnerPage
from src.texts import ErrMsg, TestData

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from fixtures.page_factory import PageFactory
    from fixtures.users import AuthUser


@allure.title("Админка владельца: вкладка настроек содержит поля ввода")
def test_owner_settings_tab_has_inputs(owner_page: Page, pages: PageFactory) -> None:
    """Вкладка настроек содержит поле site_name и кнопку сохранения."""
    with step("действие: открытие вкладки настроек"):
        owner = pages.navigate_to(OwnerPage)
        owner.open_tab("settings")

    with step("проверка: поле site_name и кнопка сохранения видны"):
        expect(owner.cfg_site_name, ErrMsg.element_not_visible).to_be_visible()
        expect(owner.cfg_save, ErrMsg.button_not_visible).to_be_visible()


@allure.title("Админка владельца: сохранение site_name попадает в бэкенд")
def test_owner_settings_save_persists(
    owner_page: Page, owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client], pages: PageFactory
) -> None:
    """Сохранение site_name через UI отражается в бэкенде."""
    with step("действие: сохранение нового site_name через UI"):
        owner = pages.navigate_to(OwnerPage)

        new_name = TestData.SAMPLE_SITE_NAME
        with owner_page.expect_response(
            lambda r: r.url.endswith(routes.SITE_CONFIG) and r.request.method != "GET"
        ) as resp_info:
            owner.update_settings(site_name=new_name)
        should.playwright_ok(resp_info.value, ErrMsg.save_config_failed)

    with step("проверка: backend отдаёт новое значение"):
        api = tenant_client(owner_user)
        cfg = site_api.get_site_config(api)
        should.be_equal(cfg.site_name, new_name, ErrMsg.site_name_wrong)


@allure.title("Экспорт: GEDCOM содержит заголовок 5.5.1 и SOUR проекта")
def test_owner_export_gedcom_returns_valid_dump(
    owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """GEDCOM export: 5.5.1 header, attachment disposition, SOUR identifier."""
    with step("действие: экспорт GEDCOM"):
        api = tenant_client(owner_user)
        r = api.get(routes.TENANT_EXPORT, params={"format": "gedcom"}, timeout=TIMEOUTS.api_long)
        expect_response(r, label="GEDCOM export").status_ok()

    with step("проверка: заголовки Content-Type и Content-Disposition"):
        ct = r.headers.get("content-type", "")
        should.be_true(ct.startswith("text/plain"), ErrMsg.gedcom_content_type_wrong)
        should.contain(ct.lower(), "charset=utf-8", ErrMsg.gedcom_charset_wrong)
        cd = r.headers.get("content-disposition", "")
        should.contain(cd.lower(), "attachment", ErrMsg.gedcom_disposition_wrong)
        should.contain(cd.lower(), ".ged", ErrMsg.gedcom_filename_wrong)

    with step("проверка: body содержит GEDCOM 5.5.1 header и SOUR"):
        head = r.text.lstrip().splitlines()[:2]
        should.be_equal(head[0], TestData.GEDCOM_HEAD, ErrMsg.gedcom_line_wrong)
        should.be_true(head[1].startswith("1 SOUR NashaRodoslovnaya"), ErrMsg.gedcom_line_wrong)


@allure.title("Экспорт: ZIP содержит people.json и MANIFEST.txt")
def test_owner_export_zip_contains_manifest_and_people(
    owner_user: AuthUser, tenant_client: Callable[[AuthUser], httpx.Client]
) -> None:
    """ZIP export: magic bytes, people.json и MANIFEST.txt внутри."""
    with step("действие: экспорт ZIP"):
        api = tenant_client(owner_user)
        r = api.get(routes.TENANT_EXPORT, params={"format": "zip"}, timeout=TIMEOUTS.api_long)
        expect_response(r, label="ZIP export").status_ok()

    with step("проверка: ZIP содержит people.json и MANIFEST.txt"):
        should.be_equal(r.headers["content-type"], "application/zip", ErrMsg.zip_content_type_wrong)
        should.be_equal(r.content[:4], b"PK\x03\x04", ErrMsg.zip_magic_wrong)
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            names = zf.namelist()
            should.be_in("people.json", names, ErrMsg.zip_file_missing)
            should.be_in("MANIFEST.txt", names, ErrMsg.zip_file_missing)
