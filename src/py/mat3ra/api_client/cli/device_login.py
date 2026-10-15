"""Signs in through the OIDC device authorization flow from a terminal."""

import time

import requests

from ..constants import CLIENT_ID, SCOPE

TOKEN_REQUEST_TIMEOUT_SECONDS = 10
FORM_HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}


def request_device_flow_state(oidc_base_url, client_id, scope):
    """
    Request an OAuth/OIDC Device Authorization flow state.

    Args:
        oidc_base_url (str): base OIDC URL.
        client_id (str): OAuth client identifier for the device flow.
        scope (str): space-separated scopes to request (e.g. "openid profile email").

    Returns:
        dict: device_code, user_code, verification_uri_complete, polling_interval_seconds, expires_in_seconds.
    """
    device_response = requests.post(
        f"{oidc_base_url}/device/auth",
        data={"client_id": client_id, "scope": scope},
        headers=FORM_HEADERS,
        timeout=TOKEN_REQUEST_TIMEOUT_SECONDS,
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


def poll_for_token_data(oidc_base_url, client_id, device_code, polling_interval_seconds, expires_in_seconds):
    """Polls for the token until the device login is confirmed."""
    form_data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "device_code": device_code,
        "client_id": client_id,
        "redirect_uris": [],
        "response_types": [],
        "token_endpoint_auth_method": "none",
    }
    deadline_seconds = time.time() + expires_in_seconds
    while time.time() < deadline_seconds:
        response = requests.post(
            f"{oidc_base_url}/token", data=form_data, headers=FORM_HEADERS, timeout=TOKEN_REQUEST_TIMEOUT_SECONDS
        )
        response_data = response.json() if response.status_code < 500 else {}
        if response.status_code == 200:
            return response_data
        if response.status_code < 500 and response_data.get("error") not in ("authorization_pending", "slow_down"):
            raise Exception(f"Device login failed ({response.status_code}): {response_data.get('error')}.")
        time.sleep(polling_interval_seconds)
    raise Exception("Timeout waiting for authorization.")


def authenticate_oidc(oidc_base_url, show_popup):
    """Starts the device login, shows its link and code, and returns the token data once it is confirmed."""
    device_flow_state = request_device_flow_state(oidc_base_url, CLIENT_ID, SCOPE)
    show_popup(device_flow_state["verification_uri_complete"], device_flow_state["user_code"])
    return poll_for_token_data(
        oidc_base_url,
        CLIENT_ID,
        device_flow_state["device_code"],
        device_flow_state["polling_interval_seconds"],
        device_flow_state["expires_in_seconds"],
    )
