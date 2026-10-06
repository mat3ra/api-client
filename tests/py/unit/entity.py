from tests.py.unit import EndpointBaseUnitTest

TEST_ENTITY_ID = "28FMvD5knJZZx452H"
MOCK_SUCCESS_RESPONSE_LIST = '{"status": "success", "data": []}'
MOCK_SUCCESS_RESPONSE_OBJECT = '{"status": "success", "data": {}}'
HTTP_METHOD_GET = "get"
HTTP_METHOD_DELETE = "delete"
CONTENT_TYPE_JSON = "application/json"


class EntityEndpointsUnitTest(EndpointBaseUnitTest):
    """
    Base class for testing entity endpoints.
    """

    def __init__(self, *args, **kwargs):
        super(EntityEndpointsUnitTest, self).__init__(*args, **kwargs)
        self.endpoints = None
        self.endpoint_name = None

    @property
    def base_url(self):
        return f"https://{self.host}:{self.port}/api/{self.version}/{self.endpoint_name}"

    def list(self, mock_request):
        mock_request.return_value = self.mock_response(MOCK_SUCCESS_RESPONSE_LIST)
        self.assertEqual(self.endpoints.list(), [])
        self.assertEqual(mock_request.call_args[1]["method"], HTTP_METHOD_GET)

    def get(self, mock_request):
        mock_request.return_value = self.mock_response(MOCK_SUCCESS_RESPONSE_OBJECT)
        self.assertEqual(self.endpoints.get(TEST_ENTITY_ID), {})
        expected_url = f"{self.base_url}/{TEST_ENTITY_ID}"
        self.assertEqual(mock_request.call_args[1]["url"], expected_url)

    def create(self, mock_request):
        mock_request.return_value = self.mock_response(MOCK_SUCCESS_RESPONSE_OBJECT)
        self.endpoints.create({})
        self.assertEqual(mock_request.call_args[1]["headers"]["Content-Type"], CONTENT_TYPE_JSON)

    def delete(self, mock_request):
        mock_request.return_value = self.mock_response(MOCK_SUCCESS_RESPONSE_OBJECT)
        self.assertEqual(self.endpoints.delete(TEST_ENTITY_ID), {})
        self.assertEqual(mock_request.call_args[1]["method"], HTTP_METHOD_DELETE)
