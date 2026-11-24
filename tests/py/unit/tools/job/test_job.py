from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest
from mat3ra.api_client.tools.job import (
    create_job,
    find_job_for_material,
    find_job_for_material_with_property,
)
from mat3ra.ide.compute import Compute, QueueName
from mat3ra.jode import Job
from mat3ra.made.material import Material
from mat3ra.standata.materials import Materials
from mat3ra.standata.workflows import WorkflowStandata
from mat3ra.wode import Workflow

OWNER_ID = "account-1"
PROJECT_ID = "project-1"
JOB_PREFIX = "NEB H2+H"
MATERIAL_SET_ID = "set-1"
MATERIAL_SET_NAME = "H2+H"

MATERIAL_INITIAL: Dict[str, Any] = {"_id": "m-initial", "name": "initial"}
MATERIAL_FINAL: Dict[str, Any] = {"_id": "m-final", "name": "final"}
SILICON: Dict[str, Any] = Materials.get_by_name_first_match("Silicon")
MATERIALS: List[Material] = [
    Material.create({**SILICON, **material}) for material in (MATERIAL_INITIAL, MATERIAL_FINAL)
]

MULTI_MATERIAL_WORKFLOW = Workflow.create(WorkflowStandata.get_by_name_first_match("neb"))
SINGLE_MATERIAL_WORKFLOW = Workflow.create(WorkflowStandata.get_by_name_first_match("total_energy"))
COMPUTE = Compute(cluster={"fqdn": "cluster-001.mat3ra.com"}, queue=QueueName.D, ppn=2)
MATERIALS_SET: Dict[str, Any] = {
    "_id": MATERIAL_SET_ID,
    "name": MATERIAL_SET_NAME,
    "slug": MATERIAL_SET_NAME,
    "isEntitySet": True,
}
MATERIALS_SET_REFERENCE: Dict[str, Any] = {"_id": MATERIAL_SET_ID, "cls": "Material", "slug": MATERIAL_SET_NAME}
CREATED_JOB: Dict[str, Any] = {"_id": "job-1", "name": JOB_PREFIX}
EXISTING_JOB: Dict[str, Any] = {"_id": "job-0", "name": "Fixed-cell Relaxation V_B pbe-us", "status": "finished"}
RELAX_WORKFLOW_NAME = "Fixed-cell Relaxation V_B pbe-us"
CHARGE_TAGS = ["charge:-1"]


JOB_CONFIGURATION: Dict[str, Any] = {"_project": {"_id": PROJECT_ID}, "owner": {"_id": OWNER_ID}, "name": JOB_PREFIX}
CREATE_JOB_CASES = [
    {
        "workflow": SINGLE_MATERIAL_WORKFLOW,
        "materials_set": None,
        "tags": CHARGE_TAGS,
        "configuration": {**JOB_CONFIGURATION, "tags": CHARGE_TAGS},
    },
    {"workflow": MULTI_MATERIAL_WORKFLOW, "materials_set": None, "tags": None, "configuration": JOB_CONFIGURATION},
    {
        "workflow": MULTI_MATERIAL_WORKFLOW,
        "materials_set": MATERIALS_SET,
        "tags": None,
        "configuration": {**JOB_CONFIGURATION, "_materialsSet": MATERIALS_SET_REFERENCE},
    },
]


@pytest.mark.parametrize("case", CREATE_JOB_CASES)
def test_create_job(case):
    client = MagicMock()
    client.jobs.create.side_effect = lambda config: {**config, **CREATED_JOB}

    job = create_job(
        client,
        MATERIALS,
        case["workflow"],
        PROJECT_ID,
        OWNER_ID,
        JOB_PREFIX,
        COMPUTE,
        case["materials_set"],
        case["tags"],
    )

    expected_job = Job.create_from_workflow(
        case["workflow"], MATERIALS, compute=COMPUTE.to_dict(), **case["configuration"]
    )
    assert client.jobs.create.call_args.args[0] == expected_job.to_dict()
    assert job.id == CREATED_JOB["_id"]


@pytest.mark.parametrize(
    "statuses",
    [("finished",), ("submitted", "queued", "active")],
)
def test_find_job_for_material_returns_the_job_when_found(statuses):
    client = MagicMock()
    client.jobs.list.return_value = [EXISTING_JOB]

    job = find_job_for_material(client, MATERIAL_INITIAL["_id"], RELAX_WORKFLOW_NAME, OWNER_ID, statuses=statuses)

    assert job == EXISTING_JOB
    client.jobs.list.assert_called_once_with(
        {
            "_material._id": MATERIAL_INITIAL["_id"],
            "owner._id": OWNER_ID,
            "workflow.name": RELAX_WORKFLOW_NAME,
            "status": {"$in": list(statuses)},
        },
        {"limit": 1},
    )


def test_find_job_for_material_returns_none_when_not_found():
    client = MagicMock()
    client.jobs.list.return_value = []

    job = find_job_for_material(client, MATERIAL_INITIAL["_id"], RELAX_WORKFLOW_NAME, OWNER_ID)

    assert job is None


def test_find_job_for_material_defaults_to_finished_only():
    client = MagicMock()
    client.jobs.list.return_value = []

    find_job_for_material(client, MATERIAL_INITIAL["_id"], RELAX_WORKFLOW_NAME, OWNER_ID)

    assert client.jobs.list.call_args.args[0]["status"] == {"$in": ["finished"]}


PROPERTY_NAME = "total_energy"
JOB_WITHOUT_PROPERTY: Dict[str, Any] = {"_id": "job-2", "name": "Band Gap", "status": "finished"}


def test_find_job_for_material_with_property_returns_the_first_job_that_reported_it():
    client = MagicMock()
    client.jobs.list.return_value = [JOB_WITHOUT_PROPERTY, EXISTING_JOB]
    client.properties.get_for_job.side_effect = lambda job_id, property_name: (
        [{"name": property_name}] if job_id == EXISTING_JOB["_id"] else []
    )

    job = find_job_for_material_with_property(
        client, MATERIAL_INITIAL["_id"], PROPERTY_NAME, OWNER_ID, tags=CHARGE_TAGS
    )

    assert job == EXISTING_JOB
    client.jobs.list.assert_called_once_with(
        {
            "_material._id": MATERIAL_INITIAL["_id"],
            "owner._id": OWNER_ID,
            "status": "finished",
            "tags": {"$all": CHARGE_TAGS},
        }
    )


def test_find_job_for_material_with_property_returns_none_when_no_job_reported_it():
    client = MagicMock()
    client.jobs.list.return_value = [JOB_WITHOUT_PROPERTY]
    client.properties.get_for_job.return_value = []

    job = find_job_for_material_with_property(client, MATERIAL_INITIAL["_id"], PROPERTY_NAME, OWNER_ID)

    assert job is None
    assert "tags" not in client.jobs.list.call_args.args[0]


SCF_KGRID_QUERY: Dict[str, Any] = {
    "workflow.subworkflows.units": {
        "$elemMatch": {"name": "pw_scf", "context": {"$elemMatch": {"name": "kgrid", "data.dimensions": [4, 4, 4]}}}
    }
}
RELAX_KGRID_QUERY: Dict[str, Any] = {
    "workflow.subworkflows.units": {
        "$elemMatch": {"name": "pw_relax", "context": {"$elemMatch": {"name": "kgrid", "data.dimensions": [4, 4, 4]}}}
    }
}


def test_find_job_for_material_with_property_matches_the_pw_scf_kgrid():
    client = MagicMock()
    client.jobs.list.return_value = [EXISTING_JOB]
    client.properties.get_for_job.return_value = [{"name": PROPERTY_NAME}]

    job = find_job_for_material_with_property(client, MATERIAL_INITIAL["_id"], PROPERTY_NAME, OWNER_ID, kgrid=[4, 4, 4])

    assert job == EXISTING_JOB
    assert SCF_KGRID_QUERY.items() <= client.jobs.list.call_args.args[0].items()


def test_find_job_for_material_matches_the_kgrid_of_the_unit():
    client = MagicMock()
    client.jobs.list.return_value = [EXISTING_JOB]

    job = find_job_for_material(
        client, MATERIAL_INITIAL["_id"], RELAX_WORKFLOW_NAME, OWNER_ID, kgrid=[4, 4, 4], unit_name="pw_relax"
    )

    assert job == EXISTING_JOB
    assert RELAX_KGRID_QUERY.items() <= client.jobs.list.call_args.args[0].items()
