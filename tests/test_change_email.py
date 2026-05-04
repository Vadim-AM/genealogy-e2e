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

from tests.constants import make_email, unique_email


def test_change_email_endpoint_initiates_confirmation(
    signup_via_api, tenant_client, read_email_token,
):
    """INV-EMAIL-002: POST /api/account/me/email c `{new_email,
    current_password}` → 200/202 + confirmation mail на new_email.

    Was xfail until upstream commit `64a206a` ("feat(auth-v2):
    change-email endpoint"). Now plain regression-trail.
    """
    user = signup_via_api(email=make_email("orig"))
    api = tenant_client(user)

    new_email = unique_email("changed")
    r = api.post(
        "/api/account/me/email",
        json={"new_email": new_email, "current_password": user.password},
    )

    assert r.status_code in (200, 202), (
        f"change-email should return 200/202 to initiate confirmation, "
        f"got {r.status_code} {r.text[:200]}"
    )

    token = read_email_token(new_email)
    assert token, f"no confirmation token sent to new email {new_email}"
