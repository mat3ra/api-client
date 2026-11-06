import json
from unittest import mock

from mat3ra.api_client.endpoints.jobs import JobEndpoints
from mat3ra.api_client.endpoints.materials import MaterialEndpoints
from tests.py.unit.entity import TEST_ENTITY_ID, EntityEndpointsUnitTest

ENDPOINT_NAME = "materials"
OWNER_ID = "Y4qZ2Gd7sKbnW3TmA"
CONSTRAINTS = [{"id": 0, "value": [False, False, False]}, {"id": 1, "value": [True, True, True]}]
MATERIAL = {"name": "material", "basis": {"constraints": CONSTRAINTS}}
STORED_MATERIAL = {"_id": TEST_ENTITY_ID, "owner": {"_id": OWNER_ID}, **MATERIAL}
V1_PREAMBLE = "https://platform.mat3ra.com:4000/api/v1/"
V1_MATERIALS_URL = f"{V1_PREAMBLE}materials"
V1_MATERIAL_URL = f"{V1_MATERIALS_URL}/{TEST_ENTITY_ID}"
V1_GET_RESPONSE = json.dumps({"status": 1, "data": {"entity": STORED_MATERIAL, "bestProperties": []}})
V1_SAVE_RESPONSE = json.dumps({"status": 1, "data": {"id": TEST_ENTITY_ID}})
V1_ERROR_RESPONSE = json.dumps({"status": 0, "error": {"code": "NOT_AUTHORIZED", "message": ""}})
SAVE_DATA = {"material": MATERIAL, "constraints": CONSTRAINTS}
SAVE_BY_NAME = {
    "create": (lambda endpoints: endpoints.create(MATERIAL, owner_id=OWNER_ID), "post", V1_MATERIALS_URL),
    "update": (lambda endpoints: endpoints.update(TEST_ENTITY_ID, MATERIAL), "put", V1_MATERIAL_URL),
}


class EndpointMaterialsUnitTest(EntityEndpointsUnitTest):
    """
    Class for testing materials endpoint.
    """

    def __init__(self, *args, **kwargs):
        super(EndpointMaterialsUnitTest, self).__init__(*args, **kwargs)
        self.endpoint_name = ENDPOINT_NAME
        self.endpoints = MaterialEndpoints(self.host, self.port, self.account_id, self.auth_token)

    def v1_response(self, **kwargs):
        """A GET reads a material back; a POST/PUT answers with the saved material's ID."""
        return self.mock_response(V1_GET_RESPONSE if kwargs["method"] == "get" else V1_SAVE_RESPONSE)

    @mock.patch("requests.sessions.Session.request")
    def test_list(self, mock_request):
        self.list(mock_request)
        self.assertEqual(mock_request.call_args[1]["url"], self.base_url)

    @mock.patch("requests.sessions.Session.request")
    def test_delete(self, mock_request):
        self.delete(mock_request)

    @mock.patch("requests.sessions.Session.request")
    def test_get(self, mock_request):
        mock_request.return_value = self.mock_response(V1_GET_RESPONSE)
        self.assertEqual(self.endpoints.get(TEST_ENTITY_ID), STORED_MATERIAL)
        self.assertEqual(mock_request.call_args[1]["url"], V1_MATERIAL_URL)

    @mock.patch("requests.sessions.Session.request")
    def test_save_sends_constraints_and_returns_the_stored_material(self, mock_request):
        for save_name, (save, method, url) in SAVE_BY_NAME.items():
            with self.subTest(save=save_name):
                mock_request.reset_mock()
                mock_request.side_effect = self.v1_response
                self.assertEqual(save(self.endpoints), STORED_MATERIAL)
                write = next(call[1] for call in mock_request.call_args_list if call[1]["method"] == method)
                self.assertEqual((write["url"], json.loads(write["data"])), (url, SAVE_DATA))

    @mock.patch("requests.sessions.Session.request")
    def test_create_without_constraints_omits_them(self, mock_request):
        mock_request.side_effect = self.v1_response
        self.endpoints.create({"name": "material"})
        self.assertNotIn("constraints", json.loads(mock_request.call_args_list[0][1]["data"]))

    @mock.patch("requests.sessions.Session.request")
    def test_create_raises_when_the_material_lands_under_another_account(self, mock_request):
        mock_request.side_effect = self.v1_response
        with self.assertRaisesRegex(BaseException, self.account_id):
            self.endpoints.create(MATERIAL, owner_id=self.account_id)

    @mock.patch("requests.sessions.Session.request")
    def test_save_raises_on_a_rejected_write(self, mock_request):
        mock_request.return_value = self.mock_response(V1_ERROR_RESPONSE)
        with self.assertRaisesRegex(BaseException, "NOT_AUTHORIZED"):
            self.endpoints.create(MATERIAL, owner_id=OWNER_ID)

    def test_v1_version_does_not_leak_to_other_endpoints(self):
        jobs = JobEndpoints(self.host, self.port, self.account_id, self.auth_token)
        self.assertEqual(self.endpoints._v1_conn.preamble, V1_PREAMBLE)
        self.assertEqual(self.endpoints.conn.preamble, jobs.conn.preamble)
        self.assertIn(f"/api/{self.version}/", jobs.conn.preamble)
