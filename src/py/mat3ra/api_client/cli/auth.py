"""Signs in once with the device login and stores API credentials that do not expire, for mat3ra-upload."""

import argparse
import json
import os

import requests

from ..constants import ACCOUNT_ID_ENV_VAR, AUTH_TOKEN_ENV_VAR, _build_base_url, build_oidc_base_url
from ..models import APIEnv
from .device_login import authenticate_oidc

CREDENTIALS_FILE_PATH = os.path.join(os.path.expanduser("~"), ".mat3ra", "api_token_cache.json")


def main():
    """Signs in to `host` by device login, mints an API token, and writes it to the file with its account and host."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host")
    environment = APIEnv.model_validate({**os.environ, "API_HOST": parser.parse_args().host})
    token_data = authenticate_oidc(
        build_oidc_base_url(environment.host, environment.port, environment.secure),
        show_popup=lambda uri, code: print(f"Open {uri}, confirm code {code}"),
    )
    response = requests.post(
        _build_base_url(environment.host, environment.port, environment.secure, "/api/v1/tokens"),
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()["data"]
    os.makedirs(os.path.dirname(CREDENTIALS_FILE_PATH), mode=0o700, exist_ok=True)
    file_descriptor = os.open(CREDENTIALS_FILE_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(file_descriptor, "w") as credentials_file:
        credentials = {
            ACCOUNT_ID_ENV_VAR: data["accountId"],
            AUTH_TOKEN_ENV_VAR: data["authToken"],
            "API_HOST": environment.host,
            "API_PORT": environment.port,
            "API_SECURE": environment.secure,
        }
        json.dump(credentials, credentials_file)
    print(f"Account {data['accountId']}: credentials written to {CREDENTIALS_FILE_PATH}")


if __name__ == "__main__":
    main()
