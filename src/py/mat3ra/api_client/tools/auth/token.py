"""OIDC token requests, token data in the environment, and the file-based token cache."""

import json
import os
import time
from typing import Optional

import requests
from mat3ra.api_client import ACCESS_TOKEN_ENV_VAR

from .settings import (
    FORM_HEADERS,
    OIDC_TOKEN_CACHE_FILENAME,
    OIDC_TOKEN_EXPIRY_BUFFER_SECONDS,
    REFRESH_TOKEN_ENV_VAR,
    TOKEN_REQUEST_TIMEOUT_SECONDS,
)


async def read() -> dict:
    try:
        with open(OIDC_TOKEN_CACHE_FILENAME) as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


async def write(cache: dict) -> None:
    os.makedirs(os.path.dirname(OIDC_TOKEN_CACHE_FILENAME), exist_ok=True)
    with open(OIDC_TOKEN_CACHE_FILENAME, "w") as file:
        json.dump(cache, file)


def add_token_to_cache(cache: dict, oidc_url: str, token_data: dict) -> None:
    entry = dict(token_data)
    entry["expires_at"] = time.time() + entry.get("expires_in", 3600)
    cache[oidc_url] = entry


def get_token_from_cache(cache: dict, oidc_url: str) -> Optional[dict]:
    entry = cache.get(oidc_url)
    if not entry or entry.get("expires_at", 0) <= time.time() + OIDC_TOKEN_EXPIRY_BUFFER_SECONDS:
        return None
    return entry


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
