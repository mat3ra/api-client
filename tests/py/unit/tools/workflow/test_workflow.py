from unittest.mock import MagicMock

import pytest
from mat3ra.api_client.tools.workflow import get_or_create_workflow
from mat3ra.standata.workflows import WorkflowStandata
from mat3ra.wode.workflows import Workflow

OWNER_ID = "account-1"
SAVED_WORKFLOW = {**WorkflowStandata.get_by_name_first_match("total_energy"), "_id": "workflow-1"}


@pytest.mark.parametrize(("existing", "created"), [([SAVED_WORKFLOW], None), ([], SAVED_WORKFLOW)])
def test_get_or_create_workflow_returns_the_saved_workflow(existing, created):
    client = MagicMock()
    client.workflows.list.return_value = existing
    client.workflows.create.return_value = created

    workflow = get_or_create_workflow(client, Workflow.create(SAVED_WORKFLOW), OWNER_ID)

    assert isinstance(workflow, Workflow)
    assert workflow.id == SAVED_WORKFLOW["_id"]
