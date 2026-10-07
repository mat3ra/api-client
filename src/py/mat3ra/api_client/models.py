import os
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from .constants import ACCESS_TOKEN_ENV_VAR, ACCOUNT_ID_ENV_VAR, AUTH_TOKEN_ENV_VAR


class AuthContext(BaseModel):
    access_token: Optional[str] = None
    account_id: Optional[str] = None
    auth_token: Optional[str] = None

    def get_headers(self) -> dict:
        if self.access_token:
            return {"Authorization": f"Bearer {self.access_token}"}
        return {"X-Account-Id": self.account_id, "X-Auth-Token": self.auth_token}


class APIEnv(BaseModel):
    host: str = Field(default="platform.mat3ra.com", validation_alias="API_HOST")
    port: int = Field(default=443, validation_alias="API_PORT")
    version: str = Field(default="2018-10-01", validation_alias="API_VERSION")
    secure: bool = Field(default=True, validation_alias="API_SECURE")

    @classmethod
    def from_env(cls) -> "APIEnv":
        return cls.model_validate(os.environ)


class AuthEnv(BaseModel):
    access_token: Optional[str] = Field(None, validation_alias=ACCESS_TOKEN_ENV_VAR)
    account_id: Optional[str] = Field(None, validation_alias=ACCOUNT_ID_ENV_VAR)
    auth_token: Optional[str] = Field(None, validation_alias=AUTH_TOKEN_ENV_VAR)

    @classmethod
    def from_env(cls) -> "AuthEnv":
        return cls.model_validate(os.environ)


class Account(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)

    client: Any = Field(exclude=True, repr=False)
    entity_cache: Optional[dict] = None

    @property
    def id(self) -> str:
        if not self.entity_cache:
            self._get_entity()
        return self.entity_cache["_id"]

    @property
    def name(self) -> str:
        if not self.entity_cache:
            self._get_entity()
        return self.entity_cache.get("name", "")

    def _get_entity(self) -> None:
        account_id, accounts = self._get_account_id_and_accounts()
        self.entity_cache = self._find_account_entity(account_id, accounts)

    def _get_account_id_and_accounts(self) -> tuple[str, Optional[list]]:
        account_id = self.client.auth.account_id or os.environ.get(ACCOUNT_ID_ENV_VAR)
        
        if account_id:
            return account_id, None
        
        if not (self.client.auth.access_token or os.environ.get(ACCESS_TOKEN_ENV_VAR)):
            raise ValueError("ACCOUNT_ID is not set and no OIDC access token is available.")
        
        data = self.client._fetch_data()
        account_id = data["user"]["entity"]["defaultAccountId"]
        os.environ[ACCOUNT_ID_ENV_VAR] = account_id
        self.client.auth.account_id = account_id
        return account_id, data.get("accounts", [])

    def _find_account_entity(self, account_id: str, accounts: Optional[list]) -> dict:
        if accounts is None and (self.client.auth.access_token or os.environ.get(ACCESS_TOKEN_ENV_VAR)):
            accounts = self.client._fetch_user_accounts()

        if accounts:
            for account in accounts:
                if account["entity"]["_id"] == account_id:
                    return account["entity"]
        
        return {"_id": account_id}

