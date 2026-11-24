import contextlib
from unittest.mock import MagicMock

import pytest
from mat3ra.api_client.tools.auth.token import request_token_data

TOKEN_URL = "https://platform.mat3ra.com/oidc/token"
TOKEN_DATA = {"access_token": "new-token", "expires_in": 3600}
PENDING_RESPONSE_DATA = {"error": "authorization_pending"}
REQUEST_TOKEN_DATA_CASES = [
    {"status_code": 200, "response_data": TOKEN_DATA, "expectation": contextlib.nullcontext(TOKEN_DATA)},
    {"status_code": 400, "response_data": PENDING_RESPONSE_DATA, "expectation": contextlib.nullcontext({})},
    {"status_code": 502, "response_data": {}, "expectation": contextlib.nullcontext({})},
    {
        "status_code": 400,
        "response_data": {"error": "access_denied"},
        "expectation": pytest.raises(Exception, match=r"\(400\): access_denied"),
    },
]


@pytest.mark.parametrize("case", REQUEST_TOKEN_DATA_CASES)
def test_request_token_data(case, monkeypatch):
    response = MagicMock(status_code=case["status_code"], json=MagicMock(return_value=case["response_data"]))
    monkeypatch.setattr("requests.post", MagicMock(return_value=response))
    with case["expectation"] as expected_token_data:
        assert request_token_data(TOKEN_URL, {}) == expected_token_data
