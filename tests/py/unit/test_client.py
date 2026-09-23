import os
from unittest import mock

from mat3ra.api_client import APIClient

from tests.py.unit import EndpointBaseUnitTest

API_HOST = "platform.mat3ra.com"
API_PORT = "4000"
API_VERSION = "2018-10-01"
API_SECURE_FALSE = "false"

OIDC_ACCESS_TOKEN = "oidc-access-token"
AUTH_TOKEN = "legacy-auth-token"
ACCOUNT_ID = "ubxMkAyx37Rjn8qK9"

AUTH_ENV_AND_USERS_ME_HEADERS = [
    ({"OIDC_ACCESS_TOKEN": OIDC_ACCESS_TOKEN}, {"Authorization": f"Bearer {OIDC_ACCESS_TOKEN}"}),
    (
        {"ACCOUNT_ID": ACCOUNT_ID, "AUTH_TOKEN": AUTH_TOKEN},
        {"X-Account-Id": ACCOUNT_ID, "X-Auth-Token": AUTH_TOKEN},
    ),
]

ME_ACCOUNT_ID = "my-account-id"
USERS_ME_RESPONSE = {"data": {"user": {"entity": {"defaultAccountId": ME_ACCOUNT_ID}}}}

ACCOUNTS_RESPONSE = {
    "data": {
        "user": {
            "entity": {"defaultAccountId": ME_ACCOUNT_ID}
        },
        "accounts": [
            {
                "entity": {"_id": "user-acc-1", "name": "John Doe", "type": "personal"},
                "isDefault": True,
            },
            {
                "entity": {"_id": "org-acc-1", "name": "Acme Corp", "type": "enterprise"},
                "isDefault": True,
            },
            {
                "entity": {"_id": "org-acc-2", "name": "Beta Industries", "type": "organization"},
                "isDefault": False,
            },
        ],
    }
}


class APIClientUnitTest(EndpointBaseUnitTest):
    def _base_env(self):
        return {
            "API_HOST": API_HOST,
            "API_PORT": API_PORT,
            "API_VERSION": API_VERSION,
            "API_SECURE": API_SECURE_FALSE,
        }

    def _mock_users_me(self, mock_get, response=None):
        mock_resp = mock.Mock()
        mock_resp.json.return_value = response or USERS_ME_RESPONSE
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

    def test_authenticate_requires_auth(self):
        env = self._base_env()
        with mock.patch.dict("os.environ", env, clear=True):
            with self.assertRaises(ValueError):
                APIClient.authenticate()

    def test_authenticate_oidc_builds_client(self):
        env = self._base_env() | {"OIDC_ACCESS_TOKEN": OIDC_ACCESS_TOKEN}
        with mock.patch.dict("os.environ", env, clear=True):
            client = APIClient.authenticate()
        self.assertEqual(client.host, API_HOST)
        self.assertEqual(client.port, int(API_PORT))
        self.assertEqual(client.version, API_VERSION)
        self.assertFalse(client.secure)
        self.assertTrue(hasattr(client, "materials"))
        self.assertTrue(hasattr(client, "my_account"))

    @mock.patch("requests.get")
    def test_my_account_id_uses_existing_account_id(self, mock_get):
        env = self._base_env() | {"ACCOUNT_ID": ACCOUNT_ID, "AUTH_TOKEN": AUTH_TOKEN}
        with mock.patch.dict("os.environ", env, clear=True):
            client = APIClient.authenticate()
            self.assertEqual(client.my_account.id, ACCOUNT_ID)
        mock_get.assert_not_called()

    @mock.patch("requests.get")
    def test_my_account_id_fetches_and_caches(self, mock_get):
        env = self._base_env() | {"OIDC_ACCESS_TOKEN": OIDC_ACCESS_TOKEN}
        response_with_account = {
            "data": {
                "user": {"entity": {"defaultAccountId": ME_ACCOUNT_ID}},
                "accounts": [
                    {"entity": {"_id": ME_ACCOUNT_ID, "name": "Test User", "type": "personal"}, "isDefault": True}
                ],
            }
        }
        with mock.patch.dict("os.environ", env, clear=True):
            self._mock_users_me(mock_get, response_with_account)
            client = APIClient.authenticate()
            self.assertEqual(client.my_account.id, ME_ACCOUNT_ID)
            self.assertEqual(client.my_account.id, ME_ACCOUNT_ID)
            self.assertEqual(mock_get.call_count, 1)
            self.assertTrue(mock_get.call_args[0][0].endswith("/api/v1/users/me"))
            self.assertEqual(mock_get.call_args[1]["headers"]["Authorization"], f"Bearer {OIDC_ACCESS_TOKEN}")
            self.assertEqual(mock_get.call_args[1]["timeout"], 30)
            self.assertEqual(os.environ.get("ACCOUNT_ID"), ME_ACCOUNT_ID)

    @mock.patch("requests.get")
    def test_list_accounts(self, mock_get):
        for auth_env, expected_headers in AUTH_ENV_AND_USERS_ME_HEADERS:
            with self.subTest(auth_env=auth_env), mock.patch.dict(
                "os.environ", self._base_env() | auth_env, clear=True
            ):
                self._mock_users_me(mock_get, ACCOUNTS_RESPONSE)
                accounts = APIClient.authenticate().list_accounts()

                self.assertEqual(mock_get.call_args[1]["headers"], expected_headers)
                self.assertEqual(len(accounts), 3)
                self.assertEqual(accounts[0]["_id"], "user-acc-1")
                self.assertEqual(accounts[0]["name"], "John Doe")
                self.assertEqual(accounts[0]["type"], "personal")
                self.assertTrue(accounts[0]["isDefault"])
                self.assertEqual(accounts[1]["_id"], "org-acc-1")
                self.assertEqual(accounts[1]["name"], "Acme Corp")
                self.assertEqual(accounts[1]["type"], "enterprise")

    @mock.patch("requests.get")
    def test_get_account(self, mock_get):
        env = self._base_env() | {"OIDC_ACCESS_TOKEN": OIDC_ACCESS_TOKEN}
        with mock.patch.dict("os.environ", env, clear=True):
            self._mock_users_me(mock_get, ACCOUNTS_RESPONSE)
            client = APIClient.authenticate()
            
            account = client.get_account(index=1)
            self.assertEqual(account.id, "org-acc-1")
            self.assertEqual(account.name, "Acme Corp")
            
            self.assertEqual(client.get_account(name="Acme").id, "org-acc-1")
            self.assertEqual(client.get_account(name="Beta.*").id, "org-acc-2")

    @mock.patch("requests.get")
    def test_my_organization(self, mock_get):
        env = self._base_env() | {"OIDC_ACCESS_TOKEN": OIDC_ACCESS_TOKEN}
        with mock.patch.dict("os.environ", env, clear=True):
            self._mock_users_me(mock_get, ACCOUNTS_RESPONSE)
            client = APIClient.authenticate()
            org = client.my_organization
            self.assertEqual(org.id, "org-acc-1")
            self.assertEqual(org.name, "Acme Corp")
