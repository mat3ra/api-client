"""File-based OIDC token cache storage."""

import json
import os
import time
from typing import Optional

_FILE_PATH = os.path.join(os.path.expanduser("~"), ".mat3ra", "oidc_token_cache.json")
_EXPIRY_BUFFER = 60 * 5  # to avoid using soon-to-expire tokens


async def read() -> dict:
    try:
        with open(_FILE_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


async def write(cache: dict) -> None:
    os.makedirs(os.path.dirname(_FILE_PATH), exist_ok=True)
    with open(_FILE_PATH, "w") as f:
        json.dump(cache, f)


def add_token_to_cache(cache: dict, oidc_url: str, token_data: dict) -> None:
    entry = dict(token_data)
    entry["expires_at"] = time.time() + entry.get("expires_in", 3600)
    cache[oidc_url] = entry


def get_token_from_cache(cache: dict, oidc_url: str) -> Optional[dict]:
    entry = cache.get(oidc_url)
    if not entry or entry.get("expires_at", 0) <= time.time() + _EXPIRY_BUFFER:
        return None
    return entry
