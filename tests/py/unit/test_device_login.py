import contextlib
from unittest import mock

import pytest

from mat3ra.api_client.cli import device_login

OIDC_BASE_URL = "https://oidc"
POLLING_INTERVAL_SECONDS = 5
PENDING_RESPONSE = (400, {"error": "authorization_pending"})
DENIED_RESPONSE = (400, {"error": "access_denied"})
TOKEN_DATA = {"access_token": "access-token"}


@pytest.mark.parametrize(
    ("token_responses", "expectation", "expected_pauses"),
    [
        ([PENDING_RESPONSE, (200, TOKEN_DATA)], contextlib.nullcontext(), [POLLING_INTERVAL_SECONDS]),
        ([DENIED_RESPONSE], pytest.raises(Exception, match="access_denied"), []),
    ],
)
def test_poll_for_token_data(monkeypatch, token_responses, expectation, expected_pauses):
    pauses = []
    monkeypatch.setattr(device_login.time, "sleep", pauses.append)
    responses = [mock.Mock(status_code=status, **{"json.return_value": body}) for status, body in token_responses]

    with mock.patch("requests.post", side_effect=responses), expectation:
        token_data = device_login.poll_for_token_data(
            OIDC_BASE_URL, "client-id", "device-code", POLLING_INTERVAL_SECONDS, 600
        )
        assert token_data == TOKEN_DATA
    assert pauses == expected_pauses
