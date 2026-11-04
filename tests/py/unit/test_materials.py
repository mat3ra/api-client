import json
from unittest import mock

from mat3ra.api_client.endpoints.materials import MaterialEndpoints
from tests.py.unit.entity import EntityEndpointsUnitTest

ENDPOINT_NAME = "materials"
MATERIAL_ID = "28FMvD5knJZZx452H"
OWNER_ID = "ubxMkAyx37Rjn8qK9"
CONSTRAINTS = [{"id": 0, "value": [False, False, False]}, {"id": 1, "value": [True, True, True]}]
MATERIAL_RESPONSE = json.dumps({"status": "success", "data": {"_id": MATERIAL_ID, "owner": {"_id": OWNER_ID}}})
V1_SUCCESS_RESPONSE = json.dumps({"status": 1, "data": {"id": MATERIAL_ID}})
V1_ERROR_RESPONSE = json.dumps({"status": 0, "error": {"code": "NOT_AUTHORIZED"}})
V1_MATERIAL_URL = f"https://platform.mat3ra.com:4000/api/v1/materials/{MATERIAL_ID}"
CONSTRAINED_MATERIAL = {"basis": {"constraints": CONSTRAINTS}}
STORE_CONSTRAINTS_DATA = {"accountId": OWNER_ID, "material": CONSTRAINED_MATERIAL, "constraints": CONSTRAINTS}
SAVE_BY_NAME = {
    "create": lambda endpoints, material: endpoints.create(material, owner_id=OWNER_ID),
    "update": lambda endpoints, material: endpoints.update(MATERIAL_ID, material),
}
MATERIAL_AND_EXTRA_REQUESTS = [
    (CONSTRAINED_MATERIAL, [("put", V1_MATERIAL_URL, STORE_CONSTRAINTS_DATA)]),
    ({"name": "material"}, []),
]


class EndpointMaterialsUnitTest(EntityEndpointsUnitTest):
    """
    Class for testing materials endpoint.
    """

    def __init__(self, *args, **kwargs):
        super(EndpointMaterialsUnitTest, self).__init__(*args, **kwargs)
        self.endpoint_name = ENDPOINT_NAME
        self.endpoints = MaterialEndpoints(self.host, self.port, self.account_id, self.auth_token)

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
    def test_delete(self, mock_request):
        self.create(mock_request)

    @mock.patch("requests.sessions.Session.request")
    def test_save_stores_constraints(self, mock_request):
        for save_name, save in SAVE_BY_NAME.items():
            for material, expected_extra_requests in MATERIAL_AND_EXTRA_REQUESTS:
                with self.subTest(save=save_name, material=material):
                    mock_request.reset_mock()
                    mock_request.side_effect = [
                        self.mock_response(MATERIAL_RESPONSE),
                        self.mock_response(V1_SUCCESS_RESPONSE),
                    ]
                    save(self.endpoints, json.loads(json.dumps(material)))
                    extra_requests = [
                        (call[1]["method"], call[1]["url"], json.loads(call[1]["data"]))
                        for call in mock_request.call_args_list[1:]
                    ]
                    self.assertEqual(extra_requests, expected_extra_requests)

    @mock.patch("requests.sessions.Session.request")
    def test_save_raises_on_rejected_constraints(self, mock_request):
        mock_request.side_effect = [self.mock_response(MATERIAL_RESPONSE), self.mock_response(V1_ERROR_RESPONSE)]
        with self.assertRaises(BaseException):
            self.endpoints.create(json.loads(json.dumps(CONSTRAINED_MATERIAL)), owner_id=OWNER_ID)
