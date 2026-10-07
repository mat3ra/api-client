import pytest
from mat3ra.api_client import AuthContext

OIDC_ACCESS_TOKEN = "oidc-access-token"
ACCOUNT_ID = "ubxMkAyx37Rjn8qK9"
AUTH_TOKEN = "legacy-auth-token"

OIDC_AUTH = {"access_token": OIDC_ACCESS_TOKEN}
API_TOKEN_AUTH = {"account_id": ACCOUNT_ID, "auth_token": AUTH_TOKEN}
OIDC_AND_API_TOKEN_AUTH = OIDC_AUTH | API_TOKEN_AUTH

BEARER_HEADERS = {"Authorization": f"Bearer {OIDC_ACCESS_TOKEN}"}
API_TOKEN_HEADERS = {"X-Account-Id": ACCOUNT_ID, "X-Auth-Token": AUTH_TOKEN}


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
