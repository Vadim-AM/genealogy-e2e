"""INV-EMAIL-002: endpoint для смены email отсутствует.

Compromised account нельзя восстановить кроме как через delete +
re-signup (потеря данных). Run security 28.04 night confirmed:
POST /me/email, PATCH /me, POST change-email — все 404/405.

Этот тест **pin'ит конкретный канонический контракт**: после
`POST /api/account/me/email` с правильным payload — backend должен
вернуть 200 + отправить confirmation mail на новый адрес. Это
двух-шаговый flow (новый адрес подтверждается ссылкой); тест
проверяет первый шаг — initiation.

Если backend выберет другой path/method — тест fail с понятным
сообщением; обновить на canonical contract когда product решит.
"""

from __future__ import annotations

from http import HTTPStatus

import allure

from tests._core import api_paths as routes
from tests._core.constants import make_email, unique_email
from tests._core.step import step


@allure.title("Запрос смены email отправляет токен подтверждения на новый адрес")
def test_change_email_endpoint_initiates_confirmation(
    signup_via_api, tenant_client, read_email_token,
):
    """INV-EMAIL-002: POST /api/account/me/email c `{new_email,
    current_password}` → 200/202 + confirmation mail на new_email.

    Was xfail until upstream commit `64a206a` ("feat(auth-v2):
    change-email endpoint"). Now plain regression-trail.
    """
    with step("подготовка: signup и получение клиента"):
        user = signup_via_api(email=make_email("orig"))
        api = tenant_client(user)

    with step("действие: запрос смены email"):
        new_email = unique_email("changed")
        r = api.post(
            routes.ACCOUNT_EMAIL,
            json={"new_email": new_email, "current_password": user.password},
        )

    with step("проверка: статус 200 и токен подтверждения отправлен"):
        assert r.status_code == HTTPStatus.OK, (
            f"change-email should return 200/202 to initiate confirmation, "
            f"got {r.status_code} {r.text[:200]}"
        )

        token = read_email_token(new_email)
        assert token, f"no confirmation token sent to new email {new_email}"
