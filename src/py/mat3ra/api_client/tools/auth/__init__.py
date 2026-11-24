import requests
from mat3ra.api_client import APIEnv, build_oidc_base_url


def get_oidc_base_url() -> str:
    environment = APIEnv.from_env()
    return build_oidc_base_url(environment.host, environment.port, environment.secure)


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
