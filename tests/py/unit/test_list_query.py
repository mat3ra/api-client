import json
from unittest import mock

import pytest
from mat3ra.api_client.endpoints.bank_materials import BankMaterialEndpoints
from mat3ra.api_client.endpoints.bank_workflows import BankWorkflowEndpoints
from mat3ra.api_client.endpoints.charges import ChargeEndpoints
from mat3ra.api_client.endpoints.jobs import JobEndpoints
from mat3ra.api_client.endpoints.materials import MaterialEndpoints
from mat3ra.api_client.endpoints.metaproperties import MetaPropertiesEndpoints
from mat3ra.api_client.endpoints.projects import ProjectEndpoints
from mat3ra.api_client.endpoints.properties import PropertiesEndpoints
from mat3ra.api_client.endpoints.workflows import WorkflowEndpoints
from mat3ra.api_client.utils.query import set_parameters, translate_projection
from tests.py.unit import EndpointBaseUnitTest
from tests.py.unit.entity import MOCK_SUCCESS_RESPONSE_LIST

OWNER_ID = "ubxMkAyx37Rjn8qK9"
SET_ID = "setIdValue"


def test_projection_limit_skip_and_sort():
    projection = {"limit": 1, "skip": 2, "sort": {"precision.value": -1}, "fields": {"status": 1}}

    assert translate_projection(projection) == {"limit": 1, "skip": 2, "sort": "-precision.value"}
    assert translate_projection({"sort": {"name": 1}}) == {"sort": "name"}
    assert translate_projection({"sort": "-name"}) == {"sort": "-name"}


@pytest.mark.parametrize("projection", [{"hint": "x"}, {"sort": {"a": 1, "b": 1}}])
def test_rejects_unsupported_projection(projection):
    with pytest.raises(ValueError):
        translate_projection(projection)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ({"inSet._id": SET_ID}, {"setId": SET_ID}),
        ({"owner._id": OWNER_ID, "inSet._id": SET_ID, "isEntitySet": {"$ne": True}}, {"setId": SET_ID}),
        ({"isEntitySet": True}, {}),
        ({"inSet._id": {"$in": [SET_ID]}}, {"globalSearch": "true"}),
        ({"isEntitySet": {"$ne": True}}, {"globalSearch": "true"}),
        ({"owner._id": OWNER_ID, "hash": "h"}, {"globalSearch": "true"}),
        ({}, {"globalSearch": "true"}),
    ],
)
def test_set_parameters(query, expected):
    assert set_parameters(query) == expected


class EndpointListQueryUnitTest(EndpointBaseUnitTest):
    """
    Class for testing how `list()` sends a Mongo query to the endpoints that filter on `advancedSearches`.
    """

    def sent_params(self, endpoint_class, query=None, projection=None):
        endpoint = endpoint_class(self.host, self.port, self.account_id, self.auth_token)
        with mock.patch("requests.sessions.Session.request") as mock_request:
            mock_request.return_value = self.mock_response(MOCK_SUCCESS_RESPONSE_LIST)
            endpoint.list(query, projection)
        return mock_request.call_args[1]["params"]

    def test_the_query_is_sent_as_advanced_searches_next_to_the_blob(self):
        query = {"hash": "abc", "owner._id": OWNER_ID, "name": {"$regex": "Si", "$options": "i"}}
        params = self.sent_params(MaterialEndpoints, query, {"limit": 1})

        self.assertEqual(json.loads(params["advancedSearches"]), [query])
        self.assertEqual(json.loads(params["query"]), query)
        self.assertEqual(json.loads(params["projection"]), {"limit": 1})
        self.assertEqual(params["limit"], 1)

    def test_operators_and_empty_lists_are_left_to_the_server(self):
        query = {"_id": {"$in": []}}

        self.assertEqual(json.loads(self.sent_params(JobEndpoints, query)["advancedSearches"]), [query])

    def test_an_empty_query_sends_no_advanced_searches(self):
        params = self.sent_params(ProjectEndpoints, None, {"limit": 5})

        self.assertNotIn("advancedSearches", params)
        self.assertEqual(params["limit"], 5)

    def test_every_advanced_searches_endpoint_sends_the_query(self):
        for endpoint_class in (
            MaterialEndpoints,
            WorkflowEndpoints,
            ProjectEndpoints,
            JobEndpoints,
            PropertiesEndpoints,
            BankMaterialEndpoints,
            BankWorkflowEndpoints,
        ):
            params = self.sent_params(endpoint_class, {"name": "x"})
            self.assertEqual(json.loads(params["advancedSearches"]), [{"name": "x"}], endpoint_class.__name__)

    def test_entities_that_can_be_in_sets_are_searched_everywhere_unless_a_set_is_named(self):
        for endpoint_class in (MaterialEndpoints, WorkflowEndpoints, JobEndpoints):
            self.assertEqual(self.sent_params(endpoint_class, {"owner._id": OWNER_ID})["globalSearch"], "true")
            self.assertEqual(self.sent_params(endpoint_class)["globalSearch"], "true")
            in_set = self.sent_params(endpoint_class, {"inSet._id": SET_ID})
            self.assertEqual(in_set["setId"], SET_ID)
            self.assertNotIn("globalSearch", in_set)
        sets = self.sent_params(MaterialEndpoints, {"owner._id": OWNER_ID, "isEntitySet": True})
        self.assertNotIn("globalSearch", sets)
        self.assertNotIn("setId", sets)

    def test_entities_without_sets_get_no_global_search(self):
        for endpoint_class in (ProjectEndpoints, PropertiesEndpoints, BankMaterialEndpoints, BankWorkflowEndpoints):
            self.assertNotIn("globalSearch", self.sent_params(endpoint_class, {"name": "x"}))

    def test_an_unsupported_option_raises_before_any_request(self):
        endpoint = MaterialEndpoints(self.host, self.port, self.account_id, self.auth_token)
        with mock.patch("requests.sessions.Session.request") as mock_request:
            with self.assertRaises(ValueError):
                endpoint.list({"name": "x"}, {"hint": "y"})
        mock_request.assert_not_called()

    def test_endpoints_that_still_read_the_blob_are_unchanged(self):
        for endpoint_class in (ChargeEndpoints, MetaPropertiesEndpoints):
            params = self.sent_params(endpoint_class, {"jid": "1"})

            self.assertEqual(set(params), {"query", "projection"}, endpoint_class.__name__)
