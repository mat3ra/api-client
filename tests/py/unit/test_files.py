import json
from unittest import mock

from mat3ra.api_client.endpoints.files import FileEndpoints
from tests.py.unit import EndpointBaseUnitTest

SIGNED_UPLOAD = {
    "signedUrl": "https://storage/put?signature",
    "headers": {"Content-Type": "text/x-python", "x-amz-meta-mode": "33188"},
    "bucket": "dropbox",
    "region": "us-west-2",
    "provider": "aws",
}


class EndpointFilesUnitTest(EndpointBaseUnitTest):
    """
    Class for testing files endpoint.
    """

    def __init__(self, *args, **kwargs):
        super(EndpointFilesUnitTest, self).__init__(*args, **kwargs)
        self.endpoints = FileEndpoints(self.host, self.port, self.account_id, self.auth_token)
        self.base_url = f"https://{self.host}:{self.port}/api/{self.version}/files"

    def respond(self, mock_request, data):
        mock_request.return_value = self.mock_response(json.dumps({"status": "success", "data": data}))

    def sign_each_file(self, mock_request):
        """The platform answers one signed upload per requested file."""
        mock_request.side_effect = lambda **request: self.mock_response(
            json.dumps(
                {
                    "status": "success",
                    "data": [
                        {**SIGNED_UPLOAD, "key": f"user/{file['name']}"}
                        for file in json.loads(request["data"])["files"]
                    ],
                }
            )
        )

    @mock.patch("requests.put")
    @mock.patch("requests.sessions.Session.request")
    def test_upload_signs_each_file_with_its_size_and_content_type(self, mock_request, mock_put):
        self.sign_each_file(mock_request)
        mock_put.return_value = self.mock_response("")

        self.endpoints.upload({"script.py": "print(1)", "blob.bin": bytes(range(4))}, account_id="organization")

        request = mock_request.call_args[1]
        self.assertEqual(request["method"], "post")
        self.assertEqual(request["url"], f"{self.base_url}/signed-urls")
        self.assertEqual(
            json.loads(request["data"]),
            {
                "files": [
                    {"name": "script.py", "size": 8, "contentType": "text/x-python"},
                    {"name": "blob.bin", "size": 4, "contentType": "application/octet-stream"},
                ],
                "operation": "putObject",
                "accountId": "organization",
            },
        )

    @mock.patch("requests.put")
    @mock.patch("requests.sessions.Session.request")
    def test_upload_puts_the_bytes_with_the_signed_headers(self, mock_request, mock_put):
        self.sign_each_file(mock_request)
        mock_put.return_value = self.mock_response("")

        self.endpoints.upload({"script.py": "print('é')", "blob.bin": bytes(range(4))})

        text_put, binary_put = mock_put.call_args_list
        self.assertEqual(text_put[0][0], SIGNED_UPLOAD["signedUrl"])
        self.assertEqual(text_put[1]["data"], "print('é')".encode("utf-8"))
        self.assertEqual(text_put[1]["headers"], SIGNED_UPLOAD["headers"])
        self.assertEqual(binary_put[1]["data"], bytes(range(4)))

    @mock.patch("requests.put")
    @mock.patch("requests.sessions.Session.request")
    def test_upload_returns_a_record_per_file(self, mock_request, mock_put):
        self.sign_each_file(mock_request)
        mock_put.return_value = self.mock_response("")

        records = self.endpoints.upload({"script.py": "print(1)"})

        self.assertEqual(
            records,
            [
                {
                    "name": "script.py",
                    "key": "user/script.py",
                    "size": 8,
                    "bucket": "dropbox",
                    "region": "us-west-2",
                    "provider": "aws",
                }
            ],
        )
        self.assertNotIn("accountId", json.loads(mock_request.call_args[1]["data"]))

    @mock.patch("requests.put")
    @mock.patch("requests.sessions.Session.request")
    def test_upload_fails_when_storage_refuses_the_bytes(self, mock_request, mock_put):
        self.sign_each_file(mock_request)
        mock_put.return_value = self.mock_response("SignatureDoesNotMatch", status_code=403, reason="Forbidden")

        with self.assertRaisesRegex(Exception, "HTTP 403: SignatureDoesNotMatch"):
            self.endpoints.upload({"script.py": "print(1)"})

    @mock.patch("requests.sessions.Session.request")
    def test_get_download_urls(self, mock_request):
        self.respond(mock_request, [{"key": "user/a.txt", "signedUrl": "https://storage/get"}])

        urls = self.endpoints.get_download_urls(["a.txt"])

        self.assertEqual(urls, [{"key": "user/a.txt", "signedUrl": "https://storage/get"}])
        self.assertEqual(json.loads(mock_request.call_args[1]["data"]), {"names": ["a.txt"], "operation": "getObject"})

    @mock.patch("requests.sessions.Session.request")
    def test_delete(self, mock_request):
        self.respond(mock_request, {"message": "Files a.txt are successfully deleted"})

        self.endpoints.delete(["a.txt"])

        request = mock_request.call_args[1]
        self.assertEqual(request["method"], "delete")
        self.assertEqual(request["url"], self.base_url)
        self.assertEqual(json.loads(request["data"]), {"names": ["a.txt"]})
