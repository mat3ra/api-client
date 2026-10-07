from unittest import mock

import pytest
from mat3ra.api_client import APIClient, AuthContext
from mat3ra.api_client.endpoints import BaseEndpoint

OIDC_ACCESS_TOKEN = "oidc-access-token"
OIDC_ACCESS_TOKEN_AFTER_LOGIN = "oidc-access-token-after-login"
ACCOUNT_ID = "ubxMkAyx37Rjn8qK9"
AUTH_TOKEN = "legacy-auth-token"

OIDC_AUTH = {"access_token": OIDC_ACCESS_TOKEN}
API_TOKEN_AUTH = {"account_id": ACCOUNT_ID, "auth_token": AUTH_TOKEN}
OIDC_AND_API_TOKEN_AUTH = OIDC_AUTH | API_TOKEN_AUTH

BEARER_HEADERS = {"Authorization": f"Bearer {OIDC_ACCESS_TOKEN}"}
API_TOKEN_HEADERS = {"X-Account-Id": ACCOUNT_ID, "X-Auth-Token": AUTH_TOKEN}
BEARER_HEADERS_AFTER_LOGIN = {"Authorization": f"Bearer {OIDC_ACCESS_TOKEN_AFTER_LOGIN}"}
CONTENT_TYPE_HEADERS = {"Content-Type": "application/json"}


@pytest.mark.parametrize(
    "auth, expected_headers",
    [
        (OIDC_AUTH, BEARER_HEADERS),
        (API_TOKEN_AUTH, API_TOKEN_HEADERS),
        (OIDC_AND_API_TOKEN_AUTH, BEARER_HEADERS),
    ],
)
def test_get_headers(auth, expected_headers):
    assert AuthContext(**auth).get_headers() == expected_headers


def list_jobs(client):
    return client.jobs.list


def post_files(client):
    endpoint = BaseEndpoint("localhost", 443, auth=client.auth)
    headers = endpoint.get_headers(ACCOUNT_ID, AUTH_TOKEN)
    return lambda: endpoint.request("POST", "files", headers=headers)


@pytest.mark.parametrize("prepare_request", [list_jobs, post_files])
@pytest.mark.parametrize(
    "auth, access_token_after_login, expected_headers",
    [
        (OIDC_AUTH, OIDC_ACCESS_TOKEN_AFTER_LOGIN, BEARER_HEADERS_AFTER_LOGIN),
        (API_TOKEN_AUTH, None, API_TOKEN_HEADERS),
    ],
)
def test_request_sends_current_auth_headers(prepare_request, auth, access_token_after_login, expected_headers):
    client = APIClient(host="localhost", port=443, version="2018-10-01", secure=True, auth=AuthContext(**auth))
    send_request = prepare_request(client)
    client.auth.access_token = access_token_after_login
    with mock.patch("requests.sessions.Session.request") as request:
        request.return_value.json.return_value = {"status": "success", "data": []}
        send_request()
    assert client.jobs.auth is client.auth
    assert client.jobs.get_request_headers() == expected_headers | CONTENT_TYPE_HEADERS
    assert request.call_args[1]["headers"] == expected_headers | CONTENT_TYPE_HEADERS
