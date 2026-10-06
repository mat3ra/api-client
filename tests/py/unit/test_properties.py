import json
from unittest import mock

from mat3ra.api_client.endpoints.properties import PropertiesEndpoints
from tests.py.unit.entity import EntityEndpointsUnitTest

ENDPOINT_NAME = "properties"

JOB_ID = "ukmnfWw9Q5ryXHK4X"
PROPERTY_NAME_0 = "total_energy"
PROPERTY_NAME_1 = "band_gaps"
UNIT_ID_0 = "pw-relax"
UNIT_ID_1 = "pw-nscf"

MOCK_PROPERTY_0 = {
    "data": {"name": PROPERTY_NAME_0, "value": -260.698, "units": "eV"},
    "source": {"info": {"jobId": JOB_ID, "unitId": UNIT_ID_0}},
}
MOCK_PROPERTY_1 = {
    "data": {"name": PROPERTY_NAME_1, "values": [{"type": "direct", "value": 0.5, "units": "eV"}]},
    "source": {"info": {"jobId": JOB_ID, "unitId": UNIT_ID_1}},
}

MOCK_PROPERTIES_RESPONSE = json.dumps({"status": "success", "data": [MOCK_PROPERTY_0, MOCK_PROPERTY_1]})
MOCK_SINGLE_PROPERTY_RESPONSE = json.dumps({"status": "success", "data": [MOCK_PROPERTY_1]})


class EndpointCharacteristicUnitTest(EntityEndpointsUnitTest):
    """
    Class for testing characteristic endpoint.
    """

    def __init__(self, *args, **kwargs):
        super(EndpointCharacteristicUnitTest, self).__init__(*args, **kwargs)
        self.endpoint_name = ENDPOINT_NAME
        self.endpoints = PropertiesEndpoints(self.host, self.port, self.account_id, self.auth_token)

    @mock.patch("requests.sessions.Session.request")
    def test_list(self, mock_request):
        self.list(mock_request)

    @mock.patch("requests.sessions.Session.request")
    def test_get(self, mock_request):
        self.get(mock_request)

    @mock.patch("requests.sessions.Session.request")
    def test_list_for_job(self, mock_request):
        mock_request.return_value = self.mock_response(MOCK_PROPERTIES_RESPONSE)
        result = self.endpoints.list_for_job(JOB_ID)
        print(result)
        self.assertEqual(result, [
            {"unit_id": UNIT_ID_0, "properties": [PROPERTY_NAME_0]},
            {"unit_id": UNIT_ID_1, "properties": [PROPERTY_NAME_1]},
        ])
        sent_query = json.loads(mock_request.call_args[1]["params"]["query"])
        self.assertEqual(sent_query["source.info.jobId"], JOB_ID)

    @mock.patch("requests.sessions.Session.request")
    def test_get_for_job(self, mock_request):
        mock_request.return_value = self.mock_response(MOCK_PROPERTIES_RESPONSE)
        result = self.endpoints.get_for_job(JOB_ID)
        self.assertEqual(len(result), 2)
        sent_query = json.loads(mock_request.call_args[1]["params"]["query"])
        self.assertEqual(sent_query["source.info.jobId"], JOB_ID)
        self.assertNotIn("data.name", sent_query)
        self.assertNotIn("source.info.unitId", sent_query)

    @mock.patch("requests.sessions.Session.request")
    def test_get_for_job_filtered_by_name(self, mock_request):
        mock_request.return_value = self.mock_response(MOCK_SINGLE_PROPERTY_RESPONSE)
        result = self.endpoints.get_for_job(JOB_ID, PROPERTY_NAME_1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], PROPERTY_NAME_1)
        sent_query = json.loads(mock_request.call_args[1]["params"]["query"])
        self.assertEqual(sent_query["data.name"], PROPERTY_NAME_1)


    @mock.patch("requests.sessions.Session.request")
    def test_get_for_job_filtered_by_unit_id_and_name(self, mock_request):
        mock_request.return_value = self.mock_response(MOCK_SINGLE_PROPERTY_RESPONSE)
        result = self.endpoints.get_for_job(JOB_ID, PROPERTY_NAME_1, unit_id=UNIT_ID_1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], PROPERTY_NAME_1)
        sent_query = json.loads(mock_request.call_args[1]["params"]["query"])
        self.assertEqual(sent_query["source.info.unitId"], UNIT_ID_1)
        self.assertEqual(sent_query["data.name"], PROPERTY_NAME_1)
