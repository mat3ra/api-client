import json
import os
import tempfile
from unittest import mock

import pytest
import requests

from mat3ra.api_client.endpoints.files import FileEndpoints
from tests.py.unit import EndpointBaseUnitTest

FILE_NAME = "loops/site-1.npy"
FILE_CONTENT = b"loop data"
FILE_SHA256 = "61719738f7cfbd0bb8e7fc91cbd2febe3b90732b4f31a994babf549e44537de8"
SIGNED_URL = "https://test-bucket.s3.amazonaws.com/user-rvuo7pgiyu/loops/site-1.npy?X-Amz-Signature=test"
OTHER_ACCOUNT_ID = "5dJXaqqhjPZrA5Qyw"

MOCK_CREATED_FILE = {"name": "record.json", "key": "user-rvuo7pgiyu/record.json", "size": 2}
MOCK_CREATE_RESPONSE = json.dumps({"status": "success", "data": MOCK_CREATED_FILE})
MOCK_SIGNED_URLS_RESPONSE = json.dumps(
    {"status": "success", "data": [{"key": "user-rvuo7pgiyu/loops/site-1.npy", "signedUrl": SIGNED_URL}]}
)
MOCK_REFUSED_RESPONSE = "<Error><Code>AccessDenied</Code></Error>"


class EndpointFilesUnitTest(EndpointBaseUnitTest):
    """
    Class for testing files endpoint.
    """

    def __init__(self, *args, **kwargs):
        super(EndpointFilesUnitTest, self).__init__(*args, **kwargs)
        self.base_url = f"https://{self.host}:{self.port}/api/{self.version}/files"
        self.endpoints = FileEndpoints(self.host, self.port, self.account_id, self.auth_token)

    @mock.patch("requests.sessions.Session.request")
    def test_create(self, mock_request):
        mock_request.return_value = self.mock_response(MOCK_CREATE_RESPONSE)
        self.assertEqual(self.endpoints.create("record.json", "{}"), MOCK_CREATED_FILE)
        self.assertEqual(mock_request.call_args[1]["url"], self.base_url)
        self.assertEqual(json.loads(mock_request.call_args[1]["data"]), {"name": "record.json", "body": "{}"})

    @mock.patch("requests.sessions.Session.request")
    def test_signed_urls(self, mock_request):
        mock_request.return_value = self.mock_response(MOCK_SIGNED_URLS_RESPONSE)
        self.assertEqual(self.endpoints.signed_urls([FILE_NAME])[0]["signedUrl"], SIGNED_URL)
        self.assertEqual(mock_request.call_args[1]["url"], f"{self.base_url}/signed-urls")
        self.assertEqual(
            json.loads(mock_request.call_args[1]["data"]), {"names": [FILE_NAME], "operation": "getObject"}
        )

    @mock.patch("requests.put")
    @mock.patch("requests.sessions.Session.request")
    def test_put(self, mock_request, mock_put):
        mock_request.return_value = self.mock_response(MOCK_SIGNED_URLS_RESPONSE)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "site-1.npy")
            with open(path, "wb") as file_:
                file_.write(FILE_CONTENT)
            result = self.endpoints.put(path, FILE_NAME)
        self.assertEqual(result, {"key": FILE_NAME, "bytes": len(FILE_CONTENT), "sha256": FILE_SHA256})
        self.assertEqual(
            json.loads(mock_request.call_args[1]["data"]), {"names": [FILE_NAME], "operation": "putObject"}
        )
        self.assertEqual(mock_put.call_args[0][0], SIGNED_URL)
        self.assertEqual(mock_put.call_args[1]["data"], FILE_CONTENT)

    @mock.patch("requests.sessions.Session.request")
    def test_create_for_account(self, mock_request):
        mock_request.return_value = self.mock_response(MOCK_CREATE_RESPONSE)
        self.endpoints.create("record.json", "{}", OTHER_ACCOUNT_ID)
        self.assertEqual(json.loads(mock_request.call_args[1]["data"])["accountId"], OTHER_ACCOUNT_ID)

    @mock.patch("requests.sessions.Session.request")
    def test_signed_urls_for_account(self, mock_request):
        mock_request.return_value = self.mock_response(MOCK_SIGNED_URLS_RESPONSE)
        self.endpoints.signed_urls([FILE_NAME], "getObject", OTHER_ACCOUNT_ID)
        self.assertEqual(json.loads(mock_request.call_args[1]["data"])["accountId"], OTHER_ACCOUNT_ID)

    @mock.patch("requests.put")
    @mock.patch("requests.sessions.Session.request")
    def test_put_for_account(self, mock_request, mock_put):
        mock_request.return_value = self.mock_response(MOCK_SIGNED_URLS_RESPONSE)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "site-1.npy")
            with open(path, "wb") as file_:
                file_.write(FILE_CONTENT)
            self.endpoints.put(path, FILE_NAME, OTHER_ACCOUNT_ID)
        self.assertEqual(json.loads(mock_request.call_args[1]["data"])["accountId"], OTHER_ACCOUNT_ID)

    @mock.patch("requests.put")
    @mock.patch("requests.sessions.Session.request")
    def test_put_refused(self, mock_request, mock_put):
        mock_request.return_value = self.mock_response(MOCK_SIGNED_URLS_RESPONSE)
        mock_put.return_value = self.mock_response(MOCK_REFUSED_RESPONSE, 403, "Forbidden")
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "site-1.npy")
            with open(path, "wb") as file_:
                file_.write(FILE_CONTENT)
            with pytest.raises(requests.HTTPError):
                self.endpoints.put(path, FILE_NAME)
