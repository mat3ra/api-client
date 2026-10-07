import json
from unittest import mock

from mat3ra.api_client.endpoints.jobs import JobEndpoints
from tests.py.unit.entity import EntityEndpointsUnitTest

ENDPOINT_NAME = "jobs"
WORKFLOW = {"_id": "workflowId", "name": "Total Energy", "subworkflows": [{"name": "scf", "units": []}]}


class EndpointJobsUnitTest(EntityEndpointsUnitTest):
    """
    Class for testing jobs endpoint.
    """

    def __init__(self, *args, **kwargs):
        super(EndpointJobsUnitTest, self).__init__(*args, **kwargs)
        self.endpoint_name = ENDPOINT_NAME
        self.endpoints = JobEndpoints(self.host, self.port, self.account_id, self.auth_token)

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

    def respond(self, mock_request, *data):
        responses = [json.dumps({"status": "success", "data": item}) for item in data]
        mock_request.side_effect = [self.mock_response(response) for response in responses]

    @mock.patch("requests.sessions.Session.request")
    def test_create_embeds_a_workflow_given_by_id(self, mock_request):
        self.respond(mock_request, WORKFLOW, {"_id": "job"})
        config = {"name": "job", "workflow": {"_id": WORKFLOW["_id"]}}

        self.assertEqual(self.endpoints.create(config), {"_id": "job"})

        fetch, create = mock_request.call_args_list
        self.assertEqual(fetch[1]["method"], "get")
        self.assertEqual(fetch[1]["url"], f"https://{self.host}:{self.port}/api/{self.version}/workflows/{WORKFLOW['_id']}")
        self.assertEqual(create[1]["url"], f"{self.base_url}/create")
        self.assertEqual(json.loads(create[1]["data"]), {"name": "job", "workflow": WORKFLOW})
        self.assertEqual(config["workflow"], {"_id": WORKFLOW["_id"]})

    @mock.patch("requests.sessions.Session.request")
    def test_create_leaves_a_full_workflow_alone(self, mock_request):
        self.respond(mock_request, {"_id": "job"})

        self.endpoints.create({"name": "job", "workflow": WORKFLOW})

        self.assertEqual(mock_request.call_count, 1)
        self.assertEqual(json.loads(mock_request.call_args[1]["data"])["workflow"], WORKFLOW)

    @mock.patch("requests.sessions.Session.request")
    def test_create_without_a_workflow_fetches_nothing(self, mock_request):
        self.respond(mock_request, {"_id": "job"})

        self.endpoints.create({"name": "job"}, owner_id="owner")

        self.assertEqual(mock_request.call_count, 1)
        self.assertEqual(json.loads(mock_request.call_args[1]["data"]), {"name": "job", "owner": {"_id": "owner"}})

    @mock.patch("requests.sessions.Session.request")
    def test_create_by_ids_embeds_the_workflow(self, mock_request):
        self.respond(mock_request, WORKFLOW, {"_id": "job"})

        jobs = self.endpoints.create_by_ids(
            [{"_id": "material", "formula": "Si"}], WORKFLOW["_id"], "project", "prefix", owner_id="owner"
        )

        self.assertEqual(jobs, [{"_id": "job"}])
        self.assertEqual(json.loads(mock_request.call_args[1]["data"])["workflow"], WORKFLOW)
