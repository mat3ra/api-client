import json
from unittest import mock

import pytest
from mat3ra.api_client.endpoints.bank_workflows import BankWorkflowEndpoints
from mat3ra.api_client.endpoints.charges import ChargeEndpoints
from mat3ra.api_client.endpoints.jobs import JobEndpoints
from mat3ra.api_client.endpoints.materials import MaterialEndpoints
from mat3ra.api_client.endpoints.projects import ProjectEndpoints
from mat3ra.api_client.endpoints.properties import PropertiesEndpoints
from mat3ra.api_client.endpoints.workflows import WorkflowEndpoints
from mat3ra.api_client.utils.query import OWNED_ENTITY_QUERY_FIELDS, translate_projection, translate_query
from tests.py.unit import EndpointBaseUnitTest
from tests.py.unit.entity import MOCK_SUCCESS_RESPONSE_LIST

OWNER_ID = "ubxMkAyx37Rjn8qK9"
SET_ID = "setIdValue"


def test_translates_values_and_in_conditions():
    query = {"owner._id": OWNER_ID, "_id": {"$in": ["a", "b"]}, "name": {"$eq": "Si"}}

    assert translate_query(query, OWNED_ENTITY_QUERY_FIELDS) == {"ownerId": OWNER_ID, "id": ["a", "b"], "name": "Si"}


def test_list_parameters_are_passed_on_as_they_are():
    query = {"ownerId": OWNER_ID, "isEntitySet": False, "id": ["a", "b"], "limit": 5, "sort": {"name": -1}}
    parameters = ("ownerId", "isEntitySet", "id", "limit", "sort")

    assert translate_query(query, {}, parameters) == {
        "ownerId": OWNER_ID,
        "isEntitySet": "false",
        "id": ["a", "b"],
        "limit": 5,
        "sort": "-name",
    }


def test_a_condition_on_a_list_parameter_is_rejected():
    with pytest.raises(ValueError, match="list parameter"):
        translate_query({"ownerId": {"$in": ["a"]}}, {}, ("ownerId",))


def test_booleans_are_sent_as_lowercase_strings_and_ne_negates_them():
    query = {"isDefault": True, "isEntitySet": {"$ne": True}}
    fields = {**OWNED_ENTITY_QUERY_FIELDS, "isEntitySet": "isEntitySet"}

    assert translate_query(query, fields) == {"isDefault": "true", "isEntitySet": "false"}


@pytest.mark.parametrize(
    "query",
    [
        {"formula": "Si"},
        {"$or": [{"name": "Si"}]},
        {"name": {"$regex": "Si", "$options": "i"}},
        {"name": {"$ne": "Si"}},
        {"name": {"$in": ["a"], "$ne": "b"}},
    ],
)
def test_rejects_what_the_endpoint_cannot_filter_on(query):
    with pytest.raises(ValueError):
        translate_query(query, OWNED_ENTITY_QUERY_FIELDS)


def test_projection_limit_skip_and_sort():
    projection = {"limit": 1, "skip": 2, "sort": {"precision.value": -1}, "fields": {"status": 1}}

    assert translate_projection(projection) == {"limit": 1, "skip": 2, "sort": "-precision.value"}
    assert translate_projection({"sort": {"name": 1}}) == {"sort": "name"}


@pytest.mark.parametrize("projection", [{"hint": "x"}, {"sort": {"a": 1, "b": 1}}])
def test_rejects_unsupported_projection(projection):
    with pytest.raises(ValueError):
        translate_projection(projection)


class EndpointListQueryUnitTest(EndpointBaseUnitTest):
    """
    Class for testing the flat filters `list()` adds for endpoints that ignore the `query` blob.
    """

    def sent_params(self, endpoint_class, query=None, projection=None):
        endpoint = endpoint_class(self.host, self.port, self.account_id, self.auth_token)
        with mock.patch("requests.sessions.Session.request") as mock_request:
            mock_request.return_value = self.mock_response(MOCK_SUCCESS_RESPONSE_LIST)
            endpoint.list(query, projection)
        return mock_request.call_args[1]["params"]

    def test_materials_send_flat_filters_next_to_the_blob(self):
        query = {"hash": "abc", "owner._id": OWNER_ID}
        params = self.sent_params(MaterialEndpoints, query, {"limit": 1})

        self.assertEqual(json.loads(params["query"]), query)
        self.assertEqual(json.loads(params["projection"]), {"limit": 1})
        self.assertEqual((params["hashes"], params["ownerId"], params["limit"]), ("abc", OWNER_ID, 1))

    def test_materials_without_a_set_are_searched_everywhere(self):
        self.assertEqual(self.sent_params(MaterialEndpoints, {"owner._id": OWNER_ID})["globalSearch"], "true")
        self.assertEqual(self.sent_params(MaterialEndpoints)["globalSearch"], "true")

    def test_materials_filter_on_formula_and_properties_on_unit_and_precision(self):
        direct = self.sent_params(MaterialEndpoints, {"ownerId": OWNER_ID, "formula": ["Si", "Ge"]})
        mongo_style = self.sent_params(MaterialEndpoints, {"owner._id": OWNER_ID, "formula": "Si"})
        properties = self.sent_params(
            PropertiesEndpoints, {"source.info.unitId": "pw-nscf", "precision.value": 10, "jobId": "j"}
        )

        self.assertEqual(direct["formula"], ["Si", "Ge"])
        self.assertEqual(mongo_style["formula"], "Si")
        self.assertEqual((properties["unitId"], properties["precisionValue"]), ("pw-nscf", 10))

    def test_workflows_and_jobs_without_a_set_are_searched_everywhere(self):
        self.assertEqual(self.sent_params(WorkflowEndpoints, {"hash": "h"})["globalSearch"], "true")
        self.assertEqual(self.sent_params(JobEndpoints, {"status": "finished"})["globalSearch"], "true")
        self.assertNotIn("globalSearch", self.sent_params(JobEndpoints, {"inSet._id": SET_ID}))
        self.assertNotIn("globalSearch", self.sent_params(ProjectEndpoints, {"isDefault": True}))

    def test_jobs_requested_by_id_are_not_restricted_to_non_sets(self):
        self.assertNotIn("globalSearch", self.sent_params(JobEndpoints, {"_id": {"$in": ["j1"]}}))

    def test_an_empty_in_matches_nothing_and_sends_no_request(self):
        for endpoint_class in (MaterialEndpoints, JobEndpoints):
            for query in ({"_id": {"$in": []}}, {"id": []}):
                endpoint = endpoint_class(self.host, self.port, self.account_id, self.auth_token)
                with mock.patch("requests.sessions.Session.request") as mock_request:
                    self.assertEqual(endpoint.list(query), [])
                mock_request.assert_not_called()

    def test_materials_take_list_parameters_directly(self):
        params = self.sent_params(MaterialEndpoints, {"name": "Si", "ownerId": OWNER_ID, "hashes": ["h1", "h2"]})

        self.assertEqual((params["name"], params["ownerId"], params["hashes"]), ("Si", OWNER_ID, ["h1", "h2"]))

    def test_list_parameters_mean_what_the_endpoint_says(self):
        top_level = self.sent_params(MaterialEndpoints, {"name": "Si", "ownerId": OWNER_ID})
        anywhere = self.sent_params(MaterialEndpoints, {"name": "Si", "ownerId": OWNER_ID, "globalSearch": True})
        mixed = self.sent_params(MaterialEndpoints, {"owner._id": OWNER_ID, "hashes": "h"})

        self.assertNotIn("globalSearch", top_level)
        self.assertEqual(anywhere["globalSearch"], "true")
        self.assertNotIn("globalSearch", mixed)

    def test_the_unsupported_field_message_names_the_supported_ones(self):
        endpoint = MaterialEndpoints(self.host, self.port, self.account_id, self.auth_token)
        with self.assertRaisesRegex(ValueError, "ownerId.*owner._id"):
            endpoint.list({"lattice.type": "FCC"})

    def test_materials_in_a_set_or_sets_keep_the_set_semantics(self):
        in_set = self.sent_params(MaterialEndpoints, {"inSet._id": SET_ID, "isEntitySet": {"$ne": True}})
        sets = self.sent_params(MaterialEndpoints, {"owner._id": OWNER_ID, "isEntitySet": True})

        self.assertEqual((in_set["setId"], in_set["isEntitySet"]), (SET_ID, "false"))
        self.assertNotIn("globalSearch", in_set)
        self.assertEqual(sets["isEntitySet"], "true")
        self.assertNotIn("globalSearch", sets)

    def test_workflows_projects_jobs_properties_and_bank(self):
        self.assertEqual(self.sent_params(WorkflowEndpoints, {"hash": "h"})["hash"], "h")
        self.assertEqual(self.sent_params(ProjectEndpoints, {"isDefault": True})["isDefault"], "true")
        self.assertEqual(self.sent_params(BankWorkflowEndpoints, {"systemName": "s"})["systemName"], "s")
        jobs = self.sent_params(JobEndpoints, {"_material._id": {"$in": ["m1", "m2"]}, "status": "finished"})
        self.assertEqual((jobs["materialId"], jobs["status"]), (["m1", "m2"], "finished"))
        properties = self.sent_params(PropertiesEndpoints, {"source.info.jobId": "j", "data.name": "total_energy"})
        self.assertEqual((properties["jobId"], properties["propertyName"]), ("j", "total_energy"))
        unit_template_query = {
            "exabyteId": {"$in": ["e1"]},
            "slug": "total_energy",
            "group": "qe:dft",
            "owner.slug": {"$in": ["me", "curators"]},
        }
        template = self.sent_params(
            PropertiesEndpoints, unit_template_query, {"sort": {"precision.value": -1}, "limit": 1}
        )
        self.assertEqual(
            (template["exabyteId"], template["group"], template["ownerSlug"], template["sort"], template["limit"]),
            (["e1"], "qe:dft", ["me", "curators"], "-precision.value", 1),
        )

    def test_an_unsupported_field_raises_before_any_request(self):
        endpoint = MaterialEndpoints(self.host, self.port, self.account_id, self.auth_token)
        with mock.patch("requests.sessions.Session.request") as mock_request:
            with self.assertRaises(ValueError):
                endpoint.list({"lattice.type": "FCC"})
        mock_request.assert_not_called()

    def test_endpoints_that_still_read_the_blob_are_unchanged(self):
        params = self.sent_params(ChargeEndpoints, {"jid": "1"})

        self.assertEqual(set(params), {"query", "projection"})
