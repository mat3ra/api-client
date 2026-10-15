import json
import os
import tempfile
from unittest import mock

import requests

from mat3ra.api_client.endpoints.files import FileEndpoints
from tests.py.unit import EndpointBaseUnitTest

FILE_NAME = "files/a.txt"
STORED_KEY = "user-rvuo7pgiyu/files/a.txt"
FILE_CONTENT = b"file data"
SIGNED_URL = "https://test-bucket.s3.amazonaws.com/user-rvuo7pgiyu/files/a.txt?X-Amz-Signature=test"

MOCK_SIGNED_URLS_RESPONSE = json.dumps({"status": "success", "data": [{"key": STORED_KEY, "signedUrl": SIGNED_URL}]})
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
    def test_signed_urls(self, mock_request):
        mock_request.return_value = self.mock_response(MOCK_SIGNED_URLS_RESPONSE)
        self.assertEqual(self.endpoints.signed_urls([FILE_NAME])[0]["signedUrl"], SIGNED_URL)
        self.assertEqual(mock_request.call_args[1]["url"], f"{self.base_url}/signed-urls")
        self.assertEqual(
            json.loads(mock_request.call_args[1]["data"]), {"names": [FILE_NAME], "operation": "getObject"}
        )

    @mock.patch("requests.sessions.Session.put")
    @mock.patch("requests.sessions.Session.request")
    def test_put(self, mock_request, mock_put):
        mock_request.return_value = self.mock_response(MOCK_SIGNED_URLS_RESPONSE)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "a.txt")
            with open(path, "wb") as file_:
                file_.write(FILE_CONTENT)
            result = self.endpoints.put(path, FILE_NAME)
        self.assertEqual(result, STORED_KEY)
        self.assertEqual(
            json.loads(mock_request.call_args[1]["data"]), {"names": [FILE_NAME], "operation": "putObject"}
        )
        self.assertEqual(mock_put.call_args[0][0], SIGNED_URL)
        self.assertEqual(mock_put.call_args[1]["data"].name, path)
        self.assertEqual(mock_put.call_args[1]["timeout"], self.endpoints.conn.session.timeout)

    @mock.patch("requests.sessions.Session.put")
    @mock.patch("requests.sessions.Session.request")
    def test_put_to_signed_url(self, mock_request, mock_put):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "a.txt")
            with open(path, "wb") as file_:
                file_.write(FILE_CONTENT)
            self.endpoints.put(path, FILE_NAME, SIGNED_URL)
        mock_request.assert_not_called()
        self.assertEqual(mock_put.call_args[0][0], SIGNED_URL)

    @mock.patch("requests.sessions.Session.put")
    def test_put_empty_file(self, mock_put):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "a.txt")
            open(path, "wb").close()
            self.endpoints.put(path, FILE_NAME, SIGNED_URL)
        self.assertEqual(mock_put.call_args[1]["data"], b"")

    @mock.patch("requests.sessions.Session.put")
    @mock.patch("requests.sessions.Session.request")
    def test_put_refused(self, mock_request, mock_put):
        mock_request.return_value = self.mock_response(MOCK_SIGNED_URLS_RESPONSE)
        mock_put.return_value = self.mock_response(MOCK_REFUSED_RESPONSE, 403, "Forbidden")
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "a.txt")
            with open(path, "wb") as file_:
                file_.write(FILE_CONTENT)
            with self.assertRaises(requests.HTTPError):
                self.endpoints.put(path, FILE_NAME)
