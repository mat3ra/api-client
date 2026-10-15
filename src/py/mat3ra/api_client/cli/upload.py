"""Uploads a folder with one subfolder per measurement as one measurement set, with samples, properties and files."""

import argparse
import json
import os
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path

import requests

from ..client import APIClient
from ..constants import ACCOUNT_ID_ENV_VAR, AUTH_TOKEN_ENV_VAR
from ..models import APIEnv
from .auth import CREDENTIALS_FILE_PATH

WORKERS = 32


def load_credentials():
    """
    Returns the account id and API token from the environment, else from the file mat3ra-auth wrote, and the platform:
    host, port and secure from the environment where set, else from the file, else the defaults.
    """
    stored = json.loads(Path(CREDENTIALS_FILE_PATH).read_text()) if os.path.exists(CREDENTIALS_FILE_PATH) else {}
    if os.environ.get(ACCOUNT_ID_ENV_VAR) and os.environ.get(AUTH_TOKEN_ENV_VAR):
        credentials = os.environ
    elif stored:
        credentials = stored
    else:
        sys.exit("No API credentials: run `mat3ra-auth`, or set ACCOUNT_ID and AUTH_TOKEN.")
    environment = APIEnv.model_validate({**stored, **os.environ})
    return credentials[ACCOUNT_ID_ENV_VAR], credentials[AUTH_TOKEN_ENV_VAR], environment


def put_file(files_endpoint, path, key, signed_file):
    """Puts the file, again after 2 s and 4 s when the network fails; any other error stops the run."""
    for pause_seconds in (2, 4):
        try:
            return files_endpoint.put(path, key, signed_file)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            time.sleep(pause_seconds)
    return files_endpoint.put(path, key, signed_file)


def find_or_create_in_set(endpoint, config, set_id, counts):
    """Returns the entity named as in `config` directly inside the set and whether it was missing and created there."""
    found = endpoint.list({"name": config["name"], "inSet._id": set_id})
    counts[endpoint.name]["already present" if found else "created"] += 1
    if found:
        return found[0], False
    entity = endpoint.create(config)
    endpoint.move_to_set(entity["_id"], None, set_id)
    return entity, True


def upload(new_client, sample_set_name, folder):
    """Uploads each measurement subfolder, files WORKERS at a time, and returns per kind what was new and present."""
    client = new_client()
    sample_sets = client.samples.list({"isEntitySet": True, "name": sample_set_name})
    if len(sample_sets) != 1:
        sys.exit(
            f'Found {len(sample_sets)} sample sets named "{sample_set_name}", expected one: create it in the web app.'
        )
    set_config = json.loads((folder / "set.json").read_text())
    set_query = {"isEntitySet": True, "name": set_config["name"]}
    counts = defaultdict(Counter)
    files_to_put = []

    run_sample_sets = client.samples.list({**set_query, "inSet._id": sample_sets[0]["_id"]})
    counts["sample sets"]["already present" if run_sample_sets else "created"] += 1
    run_sample_set_config = {"name": set_config["name"], "parentSetId": sample_sets[0]["_id"]}
    run_sample_set = run_sample_sets[0] if run_sample_sets else client.samples.create_set(run_sample_set_config)

    measurement_sets = client.measurements.list(set_query)
    counts["measurement sets"]["already present" if measurement_sets else "created"] += 1
    measurement_set = measurement_sets[0] if measurement_sets else client.measurements.create_set(set_config)

    for path in sorted(folder.glob("*/measurement.json")):
        measurement = json.loads(path.read_text())
        unit_id = measurement["workflow"]["subworkflows"][0]["units"][0]["flowchartId"]
        sample_entry = measurement.pop("sample")
        property_documents = measurement.pop("properties", [])
        sample_config = {"name": sample_entry} if isinstance(sample_entry, str) else sample_entry
        sample, _ = find_or_create_in_set(client.samples, sample_config, run_sample_set["_id"], counts)
        config = {**measurement, "_sample": {"_id": sample["_id"]}}
        measurement_entity, created = find_or_create_in_set(client.measurements, config, measurement_set["_id"], counts)
        files_folder = path.parent / "files"
        stored_files = [] if created else client.measurements.list_files(measurement_entity["_id"])
        missing_files = {}
        for file_path in [file_path for file_path in files_folder.rglob("*") if file_path.is_file()]:
            key = f"measurements/{measurement_entity['_id']}/{file_path.relative_to(files_folder).as_posix()}"
            already_stored = any(stored_file["key"].endswith(f"/{key}") for stored_file in stored_files)
            counts["files"]["already present" if already_stored else "put"] += 1
            if not already_stored:
                missing_files[key] = file_path
        if missing_files:
            signed_files = client.files.signed_urls(list(missing_files), "putObject")
            files_to_put += zip(missing_files.values(), missing_files, signed_files)
        for property_document in property_documents:
            query = {"source.info.origin._id": measurement_entity["_id"], "data.name": property_document["name"]}
            found = client.properties.list(query)
            counts["properties"]["already present" if found else "created"] += 1
            if not found:
                origin = {"_id": measurement_entity["_id"], "cls": "Measurement"}
                subject = {"_id": sample["_id"], "cls": "Sample"}
                source = {"type": "external", "info": {"origin": origin, "subject": subject, "unitId": unit_id}}
                client.properties.create(
                    {"data": property_document, "source": source, "exabyteId": [], "repetition": 0}
                )
    worker = threading.local()
    with ThreadPoolExecutor(WORKERS, initializer=lambda: setattr(worker, "files", new_client().files)) as executor:
        list(executor.map(lambda file_to_put: put_file(worker.files, *file_to_put), files_to_put))
    return counts


def main():
    """Parses the two arguments, authenticates, uploads, and prints the counts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample_set_name")
    parser.add_argument("folder", type=Path)
    arguments = parser.parse_args()
    account_id, auth_token, environment = load_credentials()
    new_client = partial(
        APIClient.authenticate,
        host=environment.host,
        port=environment.port,
        secure=environment.secure,
        account_id=account_id,
        auth_token=auth_token,
    )
    for kind, kind_counts in upload(new_client, arguments.sample_set_name, arguments.folder).items():
        new_state = "put" if kind == "files" else "created"
        print(f"{kind}: {kind_counts[new_state]} {new_state}, {kind_counts['already present']} already present")


if __name__ == "__main__":
    main()
