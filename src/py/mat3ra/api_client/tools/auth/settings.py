import os

OIDC_TOKEN_CACHE_FILENAME = os.path.join(os.path.expanduser("~"), ".mat3ra", "oidc_token_cache.json")
OIDC_TOKEN_EXPIRY_BUFFER_SECONDS = 60 * 5  # to avoid using soon-to-expire tokens
REFRESH_TOKEN_ENV_VAR = "OIDC_REFRESH_TOKEN"
TOKEN_REQUEST_TIMEOUT_SECONDS = 10
FORM_HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}
