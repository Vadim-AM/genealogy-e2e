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

import pytest

from tests.api_paths import API
from tests.constants import make_email, unique_email


@pytest.mark.xfail(
    reason="INV-EMAIL-002: endpoint смены email отсутствует. POST "
           "/me/email возвращает 404 на dev tip. Compromised account "
           "нельзя восстановить без потери данных. Fix: добавить "
           "POST /api/account/me/email двух-шаговый flow (новый email "
           "получает confirmation link, старый — notification).",
    strict=False,
)
def test_change_email_endpoint_initiates_confirmation(
    signup_via_api, tenant_client, read_email_token, base_url: str,
):
    """INV-EMAIL-002 (canonical contract): POST /me/email с
    `{new_email, password}` → 200/202 + confirmation mail на new_email.

    Pin'нутый contract — не probe-of-existence. Если backend вернёт
    другой shape, тест fail с понятным сообщением, и нужно будет
    обновить под canonical decision.
    """
    user = signup_via_api(email=make_email("orig"))
    api = tenant_client(user)

    new_email = unique_email("changed")
    r = api.post(
        "/api/account/me/email",  # canonical path; см. API namespace
        json={"new_email": new_email, "password": user.password},
    )

    assert r.status_code in (200, 202), (
        f"change-email should return 200/202 to initiate confirmation, "
        f"got {r.status_code} {r.text[:200]}"
    )

    # Confirmation mail должна прийти на NEW адрес (с токеном).
    # `read_email_token` raises если ничего не пришло — что и нужно.
    token = read_email_token(new_email)
    assert token, f"no confirmation token sent to new email {new_email}"
