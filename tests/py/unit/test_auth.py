import json
import sys
from unittest import mock

from mat3ra.api_client.cli import auth

DEVICE_RESPONSE = {"device_code": "device-code", "user_code": "ABCD-EFGH", "verification_uri": "https://oidc/device"}
TOKEN_RESPONSE = {"access_token": "access-token"}
API_TOKEN_RESPONSE = {"status": "success", "data": {"accountId": "account-id", "authToken": "auth-token"}}


def test_main(tmp_path, monkeypatch):
    credentials_file_path = tmp_path / ".mat3ra" / "api_token_cache.json"
    monkeypatch.setattr(auth, "CREDENTIALS_FILE_PATH", str(credentials_file_path))
    monkeypatch.setattr(sys, "argv", ["mat3ra-auth"])
    responses = [
        mock.Mock(status_code=200, **{"json.return_value": body})
        for body in (DEVICE_RESPONSE, TOKEN_RESPONSE, API_TOKEN_RESPONSE)
    ]

    with mock.patch("requests.post", side_effect=responses) as post:
        auth.main()

    assert post.call_args[0][0].endswith("/api/v1/tokens")
    assert post.call_args[1]["headers"] == {"Authorization": "Bearer access-token"}
    assert json.loads(credentials_file_path.read_text()) == {"ACCOUNT_ID": "account-id", "AUTH_TOKEN": "auth-token"}
    assert credentials_file_path.stat().st_mode & 0o777 == 0o600
