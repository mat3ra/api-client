"""Signs in once with the device login and stores API credentials that do not expire, for mat3ra-upload."""

import argparse
import json
import os

import requests

from ..constants import ACCOUNT_ID_ENV_VAR, AUTH_TOKEN_ENV_VAR, build_oidc_base_url
from ..models import APIEnv
from .device_login import authenticate_oidc

CREDENTIALS_FILE_PATH = os.path.join(os.path.expanduser("~"), ".mat3ra", "api_token_cache.json")


def main():
    """Signs in with the device login, mints an API token with it, and writes the account id and token to the file."""
    argparse.ArgumentParser(description=__doc__).parse_args()
    environment = APIEnv.from_env()
    token_data = authenticate_oidc(
        build_oidc_base_url(environment.host, environment.port, environment.secure),
        show_popup=lambda uri, code: print(f"Open {uri}, confirm code {code}"),
    )
    protocol = "https" if environment.secure else "http"
    response = requests.post(
        f"{protocol}://{environment.host}:{environment.port}/api/v1/tokens",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()["data"]
    os.makedirs(os.path.dirname(CREDENTIALS_FILE_PATH), mode=0o700, exist_ok=True)
    file_descriptor = os.open(CREDENTIALS_FILE_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(file_descriptor, "w") as credentials_file:
        json.dump({ACCOUNT_ID_ENV_VAR: data["accountId"], AUTH_TOKEN_ENV_VAR: data["authToken"]}, credentials_file)
    print(f"Account {data['accountId']}: credentials written to {CREDENTIALS_FILE_PATH}")


if __name__ == "__main__":
    main()
