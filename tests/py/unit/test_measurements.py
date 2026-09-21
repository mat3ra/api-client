import json
from unittest import mock

from mat3ra.api_client.endpoints.measurements import MeasurementEndpoints
from tests.py.unit.entity import TEST_ENTITY_ID, EntityEndpointsUnitTest

ENDPOINT_NAME = "measurements"

MOCK_FILE = {"key": "user-rvuo7pgiyu/loops/site-1.npy", "signedUrl": "https://test-bucket.s3.amazonaws.com/site-1.npy"}
MOCK_FILES_RESPONSE = json.dumps({"status": "success", "data": [MOCK_FILE]})


class EndpointMeasurementsUnitTest(EntityEndpointsUnitTest):
    """
    Class for testing measurements endpoint.
    """

    def __init__(self, *args, **kwargs):
        super(EndpointMeasurementsUnitTest, self).__init__(*args, **kwargs)
        self.endpoint_name = ENDPOINT_NAME
        self.endpoints = MeasurementEndpoints(self.host, self.port, self.account_id, self.auth_token)

    @mock.patch("requests.sessions.Session.request")
    def test_list(self, mock_request):
        self.list(mock_request)

    @mock.patch("requests.sessions.Session.request")
    def test_get(self, mock_request):
        self.get(mock_request)

    @mock.patch("requests.sessions.Session.request")
    def test_create(self, mock_request):
        self.create(mock_request)

    @mock.patch("requests.sessions.Session.request")
    def test_files(self, mock_request):
        mock_request.return_value = self.mock_response(MOCK_FILES_RESPONSE)
        self.assertEqual(self.endpoints.files(TEST_ENTITY_ID), [MOCK_FILE])
        self.assertEqual(mock_request.call_args[1]["url"], f"{self.base_url}/{TEST_ENTITY_ID}/files")
