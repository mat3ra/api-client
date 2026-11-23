import math
import re
from typing import Dict, List, Optional

from mat3ra.api_client import APIClient, BankWorkflowEndpoints
from mat3ra.wode import Workflow
from mat3ra.wode.context.providers import PlanewaveCutoffsContextProvider, PointsGridDataProvider


def copy_bank_workflow_by_system_name(endpoint: BankWorkflowEndpoints, system_name: str, account_id: str) -> dict:
    """
    Copies a bank workflow with given system name into the account's workflows.

    Args:
        endpoint (BankWorkflowEndpoints): an instance of BankWorkflowEndpoints class
        system_name (str): workflow system name.
        account_id (str): ID of account to copy the bank workflow into.

    Returns:
        dict: new account's workflow
    """
    bank_workflow_id = endpoint.list({"systemName": system_name})[0]["_id"]
    return endpoint.copy(bank_workflow_id, account_id)["_id"]


CUSTOM_SCRIPT_RUNNER = '''import json

with open("material.json", "w") as file:
    json.dump(json.loads(r"""{{ MATERIAL | default({}) | tojson }}"""), file)

with open("user_script.py") as file:
    exec(compile(file.read(), "user_script.py", "exec"))
'''


# The shell twin, rendered as `hello_world.sh`. The user's script is *sourced*, not run in a
# subshell, so `module` stays available - rupy runs the runner the same way.
CUSTOM_SCRIPT_RUNNER_SH = """#!/bin/bash
cat > material.json <<'MATERIAL_JSON_EOF'
{{ MATERIAL | default({}) | tojson }}
MATERIAL_JSON_EOF

. ./user_script.sh
"""


def set_execution_unit_input(unit: dict, template_name: str, content: str) -> None:
    """
    Replaces one input file of an execution unit with fixed content.

    `isManuallyChanged` stops the platform re-rendering the file at job creation, which is what
    lets the runner keep its `{{ ... }}` placeholders for the compute node to resolve, and keeps a
    user's requirements verbatim. Inputs are matched by template name rather than position, so
    adding a file to the flavor cannot silently write content into the wrong one.

    Args:
        unit (dict): Execution unit config from a workflow.
        template_name (str): Name of the input file to replace, e.g. "script.py".
        content (str): Content to write.

    Raises:
        KeyError: If the unit has no input with that template name.
    """
    for unit_input in unit["input"]:
        if unit_input["template"]["name"] == template_name:
            unit_input["template"]["content"] = content
            unit_input["rendered"] = content
            unit_input["isManuallyChanged"] = True
            return
    available = [unit_input["template"]["name"] for unit_input in unit["input"]]
    raise KeyError(f"No input named '{template_name}' in unit '{unit.get('name')}'. Available: {available}")


def get_or_create_workflow(api_client: APIClient, workflow: Workflow, owner_id: str) -> dict:
    """
    Creates a workflow in the collection if none with the same hash exists under the given owner.

    Args:
        api_client (APIClient): API client instance carrying the authorization context.
        workflow: mat3ra-wode Workflow object.
        owner_id (str): Account ID under which to search and create.

    Returns:
        dict: The workflow dict (existing or newly created).
    """
    existing = api_client.workflows.list({"hash": workflow.hash, "owner._id": owner_id})
    if existing:
        print(f"♻️  Reusing already existing Workflow: {existing[0]['_id']}")
        return existing[0]
    created = api_client.workflows.create(workflow.to_dict_without_special_keys(), owner_id=owner_id)
    print(f"✅ Workflow created: {created['_id']}")
    return created


FORTRAN_NUMBER_PATTERN = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[de][+-]?\d+)?$", re.IGNORECASE)


def _format_fortran_value(value: object) -> str:
    if isinstance(value, bool):
        return f".{str(value).lower()}."
    if isinstance(value, str) and not FORTRAN_NUMBER_PATTERN.match(value):
        return repr(value)
    return str(value)


def patch_workflow_qe_input(
    workflow: Workflow,
    parameters: Dict[str, Dict[str, object]],
    unit_names: List[str],
    input_name: Optional[str] = None,
) -> Workflow:
    """
    Patch QE inputs across workflow subworkflows for named units.

    Args:
        workflow: Workflow with subworkflows.
        parameters: Multi-section parameters {section: {key: val}}.
        unit_names: List of unit names to patch.
        input_name: Optional input file name filter.

    Example:
        patch_workflow_qe_input(workflow, {"system": {"vdw_corr": "d3_grimme"}}, ["pw_relax"])
    """
    for subworkflow in workflow.subworkflows:
        for unit_name in unit_names:
            if not (unit := subworkflow.get_unit_by_name(name=unit_name)):
                continue
            for input_item in getattr(unit, "input", []):
                template = input_item.template
                template_name = template.name
                content = template.content

                if input_name not in (None, template_name):
                    continue

                for section, updates in parameters.items():
                    name = section.lstrip("&")
                    match = re.search(rf"(?ims)(^&{re.escape(name)}\s*\n)(.*?)(^/\s*$)", content)
                    if not match:
                        raise ValueError(f"Namelist '&{name.upper()}' not found.")
                    header, body, footer = match.groups()
                    for key, value in updates.items():
                        line = f"    {key} = {_format_fortran_value(value)}"
                        pattern = rf"(?im)^\s*{re.escape(key)}\s*=.*$"
                        body = re.sub(pattern, line, body) if re.search(pattern, body) else f"{body.rstrip()}\n{line}\n"
                    content = content[: match.start()] + header + body + footer + content[match.end() :]

                template.set_content(content)
            subworkflow.set_unit(unit)
    return workflow


def kgrid_from_density(material, density: float, periodic_dims: tuple = (0, 1, 2)) -> List[int]:
    """
    Returns a k-point grid sized to a reciprocal-space density (points per Å⁻¹) per periodic
    dimension, 1 elsewhere.

    Args:
        material: Material the grid applies to; reciprocal vector norms come from its lattice.
        density (float): Points per Å⁻¹ of reciprocal length (GPAW's k-point density convention).
        periodic_dims (tuple[int]): Lattice dimensions (0, 1, 2) that are periodic.

    Returns:
        list[int]: Grid dimensions, e.g. [4, 4, 1].
    """
    norms = material.lattice.reciprocal_vector_norms
    grid = [1, 1, 1]
    for dim in periodic_dims:
        grid[dim] = max(1, math.ceil(density * 2 * math.pi * norms[dim]))
    return grid


def apply_scf_kgrid(
    workflow: Workflow, scf_kgrid=None, *, material=None, unit_name: str = "pw_scf", first_only: bool = False
) -> Workflow:
    """
    Attaches an edited SCF k-grid context to units named `unit_name`.

    Args:
        workflow: Workflow with subworkflows.
        scf_kgrid: K-grid dimensions, e.g. [4, 4, 1]. If None, the workflow is returned unchanged.
        material: Material the grid applies to. KPPRA is per reciprocal atom and the reciprocal
            vector ratios come from the lattice, so both are derived from it.
        unit_name: Name of the unit to attach the k-grid context to.
        first_only: If True, only patch the first matching subworkflow.
    """
    if scf_kgrid is None:
        return workflow
    context = PointsGridDataProvider(material=material, dimensions=scf_kgrid, isEdited=True).get_context_item_data()
    for subworkflow in workflow.subworkflows:
        if unit_name not in [unit.name for unit in subworkflow.units]:
            continue
        unit = subworkflow.get_unit_by_name(name=unit_name)
        unit.add_context(context)
        subworkflow.set_unit(unit)
        if first_only:
            break
    return workflow


# TODO: move to Wode
def set_assignment_value(workflow: Workflow, unit_name: str, value: str) -> Workflow:
    """
    Sets the value of the assignment units named `unit_name` in every subworkflow that has one.

    Args:
        workflow: Workflow with subworkflows.
        unit_name: Name of the assignment unit, e.g. "assign-charge".
        value: The unit's new value, as the Python expression the workflow evaluates, e.g. "-1".

    Raises:
        ValueError: If no subworkflow has a unit of that name.
    """
    subworkflows = [
        subworkflow for subworkflow in workflow.subworkflows if subworkflow.get_unit_by_name(name=unit_name)
    ]
    if not subworkflows:
        raise ValueError(f"The workflow has no '{unit_name}' unit.")
    for subworkflow in subworkflows:
        unit = subworkflow.get_unit_by_name(name=unit_name)
        unit.value = value
        subworkflow.set_unit(unit)
    return workflow


def apply_planewave_cutoffs(workflow: Workflow, wavefunction, density, *, unit_name: str = "pw_relax") -> Workflow:
    """Attaches an edited planewave cutoffs context to units named `unit_name`."""
    context = PlanewaveCutoffsContextProvider(
        wavefunction=wavefunction, density=density, isEdited=True
    ).get_context_item_data()
    for subworkflow in workflow.subworkflows:
        if unit_name not in [unit.name for unit in subworkflow.units]:
            continue
        unit = subworkflow.get_unit_by_name(name=unit_name)
        unit.add_context(context)
        subworkflow.set_unit(unit)
    return workflow
