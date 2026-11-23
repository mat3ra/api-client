import os

import requests
from mat3ra.api_client import ACCESS_TOKEN_ENV_VAR, APIEnv, build_oidc_base_url

REFRESH_TOKEN_ENV_VAR = "OIDC_REFRESH_TOKEN"
TOKEN_REQUEST_TIMEOUT_SECONDS = 10
FORM_HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}


def get_oidc_base_url() -> str:
    env = APIEnv.from_env()
    return build_oidc_base_url(env.host, env.port, env.secure)


def request_device_flow_state(oidc_base_url: str, client_id: str, scope: str) -> dict:
    """
    Request an OAuth/OIDC Device Authorization flow state.

    Args:
        oidc_base_url: Base OIDC URL.
        client_id: OAuth client identifier for the device flow.
        scope: Space-separated scopes to request (e.g. "openid profile email").

    Returns:
        A dict with device_code, user_code, verification_uri_complete,
        polling_interval_seconds, expires_in_seconds.
    """
    device_response = requests.post(
        f"{oidc_base_url}/device/auth",
        data={"client_id": client_id, "scope": scope},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    device_response.raise_for_status()
    device_data = device_response.json()
    return {
        "device_code": device_data["device_code"],
        "user_code": device_data["user_code"],
        "verification_uri_complete": device_data.get("verification_uri_complete", device_data["verification_uri"]),
        "polling_interval_seconds": int(device_data.get("interval", 5)),
        "expires_in_seconds": int(device_data.get("expires_in", 600)),
    }


def store_token_data_in_environment(token_data: dict) -> None:
    os.environ[ACCESS_TOKEN_ENV_VAR] = token_data["access_token"]
    if "refresh_token" in token_data:
        os.environ[REFRESH_TOKEN_ENV_VAR] = token_data["refresh_token"]


def get_token_request_form_data(client_id: str, device_code: str) -> dict:
    return {
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "device_code": device_code,
        "client_id": client_id,
        "redirect_uris": [],
        "response_types": [],
        "token_endpoint_auth_method": "none",
    }


def get_token_data_from_response(status: int, response_data: dict) -> dict:
    """
    Token data of a confirmed device login; empty while the login is pending.
    """
    if status != 200 and status < 500 and response_data.get("error") not in ("authorization_pending", "slow_down"):
        raise Exception(f"Device login failed ({status}): {response_data.get('error')}.")
    return response_data if status == 200 else {}


def request_token_data(token_url: str, form_data: dict) -> dict:
    response = requests.post(token_url, data=form_data, headers=FORM_HEADERS, timeout=TOKEN_REQUEST_TIMEOUT_SECONDS)
    return get_token_data_from_response(response.status_code, response.json() if response.status_code < 500 else {})
