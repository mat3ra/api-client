import os
import re
from typing import Any, List, Optional, Tuple

import requests
from pydantic import BaseModel, ConfigDict

from .constants import ACCESS_TOKEN_ENV_VAR, _build_base_url
from .endpoints.bank_materials import BankMaterialEndpoints
from .endpoints.bank_workflows import BankWorkflowEndpoints
from .endpoints.clusters import ClustersEndpoint
from .endpoints.files import FileEndpoints
from .endpoints.jobs import JobEndpoints
from .endpoints.materials import MaterialEndpoints
from .endpoints.measurements import MeasurementEndpoints
from .endpoints.metaproperties import MetaPropertiesEndpoints
from .endpoints.projects import ProjectEndpoints
from .endpoints.properties import PropertiesEndpoints
from .endpoints.samples import SampleEndpoints
from .endpoints.workflows import WorkflowEndpoints
from .models import Account, APIEnv, AuthContext, AuthEnv


class APIClient(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow", validate_assignment=True)

    host: str
    port: int
    version: str
    secure: bool
    auth: AuthContext
    timeout_seconds: int = 60

    def model_post_init(self, __context: Any) -> None:
        self.my_account = Account(client=self)
        self.account = self.my_account
        self._my_organization: Optional[Account] = None
        self._init_endpoints(self.timeout_seconds)

    @property
    def my_organization(self) -> Optional[Account]:
        if self._my_organization is None:
            self._my_organization = self.get_default_organization()
        return self._my_organization

    @classmethod
    def env(cls) -> APIEnv:
        return APIEnv.from_env()

    @classmethod
    def auth_env(cls) -> AuthEnv:
        return AuthEnv.from_env()

    def _init_endpoints(self, timeout_seconds: int) -> None:
        base_args = (self.host, self.port, self.auth.account_id or "", self.auth.auth_token or "")
        base_kwargs = {"version": self.version, "secure": self.secure, "timeout": timeout_seconds, "auth": self.auth}

        self.materials = MaterialEndpoints(*base_args, **base_kwargs)
        self.samples = SampleEndpoints(*base_args, **base_kwargs)
        self.measurements = MeasurementEndpoints(*base_args, **base_kwargs)
        self.files = FileEndpoints(*base_args, **base_kwargs)
        self.workflows = WorkflowEndpoints(*base_args, **base_kwargs)
        self.jobs = JobEndpoints(*base_args, **base_kwargs)
        self.projects = ProjectEndpoints(*base_args, **base_kwargs)
        self.properties = PropertiesEndpoints(*base_args, **base_kwargs)
        self.metaproperties = MetaPropertiesEndpoints(*base_args, **base_kwargs)
        self.bank_materials = BankMaterialEndpoints(*base_args, **base_kwargs)
        self.bank_workflows = BankWorkflowEndpoints(*base_args, **base_kwargs)
        self.clusters = ClustersEndpoint(*base_args, **base_kwargs)

    @staticmethod
    def _resolve_config(
            host: Optional[str],
            port: Optional[int],
            version: Optional[str],
            secure: Optional[bool],
            env: APIEnv,
    ) -> Tuple[str, int, str, bool]:
        return (
            host if host is not None else env.host,
            port if port is not None else env.port,
            version if version is not None else env.version,
            secure if secure is not None else env.secure,
        )

    @classmethod
    def _auth_from_env(
            cls,
            *,
            access_token: Optional[str],
            account_id: Optional[str],
            auth_token: Optional[str],
    ) -> AuthContext:
        env = cls.auth_env()
        return AuthContext(
            access_token=access_token if access_token is not None else env.access_token,
            account_id=account_id if account_id is not None else env.account_id,
            auth_token=auth_token if auth_token is not None else env.auth_token,
        )

    @staticmethod
    def _validate_auth(auth: AuthContext) -> None:
        if auth.access_token:
            return
        if auth.account_id and auth.auth_token:
            return
        raise ValueError("Missing auth. Provide OIDC_ACCESS_TOKEN or ACCOUNT_ID and AUTH_TOKEN.")

    @classmethod
    def authenticate(
            cls,
            *,
            host: Optional[str] = None,
            port: Optional[int] = None,
            version: Optional[str] = None,
            secure: Optional[bool] = None,
            access_token: Optional[str] = None,
            account_id: Optional[str] = None,
            auth_token: Optional[str] = None,
            timeout_seconds: int = 60,
    ) -> "APIClient":
        host_value, port_value, version_value, secure_value = cls._resolve_config(
            host, port, version, secure, cls.env()
        )
        auth = cls._auth_from_env(access_token=access_token, account_id=account_id, auth_token=auth_token)
        cls._validate_auth(auth)
        return cls(
            host=host_value,
            port=port_value,
            version=version_value,
            secure=secure_value,
            auth=auth,
            timeout_seconds=timeout_seconds,
        )

    def _fetch_data(self) -> dict:
        access_token = self.auth.access_token or os.environ.get(ACCESS_TOKEN_ENV_VAR)
        if not access_token:
            raise ValueError("Access token is required to fetch user data")

        url = _build_base_url(self.host, self.port, self.secure, "/api/v1/users/me")
        response = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=30)
        response.raise_for_status()
        return response.json()["data"]

    def _fetch_user_accounts(self) -> List[dict]:
        return self._fetch_data().get("accounts", [])

    def list_accounts(self) -> List[dict]:
        accounts = self._fetch_user_accounts()
        return [
            {
                "_id": account["entity"]["_id"],
                "name": account["entity"].get("name", ""),
                "type": account["entity"].get("type", "personal"),
                "isDefault": account.get("isDefault", False),
            }
            for account in accounts
        ]

    def get_account(self, name: Optional[str] = None, index: Optional[int] = None) -> Account:
        """Get account by name (partial regex match) or index from the list of user accounts."""
        if name is None and index is None:
            raise ValueError("Either 'name' or 'index' must be provided")

        accounts = self._fetch_user_accounts()

        if index is not None:
            return Account(client=self, entity_cache=accounts[index]["entity"])

        pattern = re.compile(name, re.IGNORECASE)
        matches = [account for account in accounts if pattern.search(account["entity"].get("name", ""))]

        if not matches:
            raise ValueError(f"No account found matching '{name}'")
        if len(matches) > 1:
            names = [acc["entity"].get("name", "") for acc in matches]
            raise ValueError(f"Multiple accounts match '{name}': {names}")

        return Account(client=self, entity_cache=matches[0]["entity"])

    def get_default_organization(self) -> Optional[Account]:
        accounts = self._fetch_user_accounts()
        organizations = [account for account in accounts if
                         account["entity"].get("type") in ("organization", "enterprise")]

        if not organizations:
            return None

        default_org = next((org for org in organizations if org.get("isDefault")), organizations[0])
        return Account(client=self, entity_cache=default_org["entity"])
