import json
from unittest import mock

from mat3ra.api_client.endpoints.samples import SampleEndpoints
from tests.py.unit.entity import MOCK_SUCCESS_RESPONSE_OBJECT, TEST_ENTITY_ID, EntityEndpointsUnitTest

ENDPOINT_NAME = "samples"

SET_CONFIG = {"name": "WAFER-1", "metadata": {"label": "WAFER-1"}}
HTTP_METHOD_PUT = "put"


class EndpointSamplesUnitTest(EntityEndpointsUnitTest):
    """
    Class for testing samples endpoint.
    """

    def __init__(self, *args, **kwargs):
        super(EndpointSamplesUnitTest, self).__init__(*args, **kwargs)
        self.endpoint_name = ENDPOINT_NAME
        self.endpoints = SampleEndpoints(self.host, self.port, self.account_id, self.auth_token)

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
    def test_update_set(self, mock_request):
        mock_request.return_value = self.mock_response(MOCK_SUCCESS_RESPONSE_OBJECT)
        self.endpoints.update_set(TEST_ENTITY_ID, SET_CONFIG)
        self.assertEqual(mock_request.call_args[1]["method"], HTTP_METHOD_PUT)
        self.assertEqual(mock_request.call_args[1]["url"], f"{self.base_url}/{TEST_ENTITY_ID}/update-set")
        self.assertEqual(json.loads(mock_request.call_args[1]["data"]), SET_CONFIG)
