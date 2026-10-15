import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import requests

from mat3ra.api_client.cli import upload
from tests.py.unit import EndpointBaseUnitTest

FOLDER_NAME = "upload_folder"
SAMPLE_SET = {"_id": "sample-set-id", "name": "sample-set"}
RUN_SAMPLE_SET = {"_id": "run-sample-set-id", "name": "set-1"}
SAMPLE = {"_id": "sample-id", "name": "sample-1"}
MEASUREMENT_SET = {"_id": "measurement-set-id", "name": "set-1"}
MEASUREMENT = {"_id": "measurement-id", "name": "measurement-1"}
PROPERTY = {"_id": "property-id"}
STORED_FILE = {"key": "account/measurements/measurement-id/a.txt"}
SIGNED_FILE = {"signedUrl": "https://storage/account/measurements/measurement-id/a.txt?signature"}
PROPERTY_SOURCE = {
    "type": "external",
    "info": {
        "origin": {"_id": "measurement-id", "cls": "Measurement"},
        "subject": {"_id": "sample-id", "cls": "Sample"},
        "unitId": "unit-1",
    },
}
STORED_CREDENTIALS = {
    "ACCOUNT_ID": "account-id",
    "AUTH_TOKEN": "auth-token",
    "API_HOST": "localhost",
    "API_PORT": 3000,
    "API_SECURE": False,
}


class UploadUnitTest(EndpointBaseUnitTest):
    """
    Class for testing the upload command.
    """

    def setUp(self):
        self.folder = Path(self.get_file_path(FOLDER_NAME))
        self.client = mock.Mock()
        self.client.samples.create_set.return_value = RUN_SAMPLE_SET
        self.client.samples.create.return_value = SAMPLE
        self.client.measurements.create_set.return_value = MEASUREMENT_SET
        self.client.measurements.create.return_value = MEASUREMENT
        self.client.files.signed_urls.return_value = [SIGNED_FILE]

    def upload(self, present=False):
        def found(record):
            return [record] if present else []

        self.client.samples.list.side_effect = [[SAMPLE_SET], found(RUN_SAMPLE_SET), found(SAMPLE)]
        self.client.measurements.list.side_effect = [found(MEASUREMENT_SET), found(MEASUREMENT)]
        self.client.measurements.list_files.return_value = found(STORED_FILE)
        self.client.properties.list.return_value = found(PROPERTY)
        upload.upload(lambda: self.client, SAMPLE_SET["name"], self.folder)

    def test_upload_creates_the_sample_set_inside_the_named_set(self):
        self.upload()
        self.client.samples.create_set.assert_called_once_with({"name": "set-1", "parentSetId": SAMPLE_SET["_id"]})

    def test_upload_creates_the_sample_inside_the_sample_set(self):
        self.upload()
        self.client.samples.move_to_set.assert_called_once_with(SAMPLE["_id"], None, RUN_SAMPLE_SET["_id"])

    def test_upload_creates_the_measurement_with_its_sample(self):
        self.upload()
        self.assertEqual(self.client.measurements.create.call_args[0][0]["_sample"], {"_id": SAMPLE["_id"]})

    def test_upload_creates_the_property_with_the_external_holder(self):
        self.upload()
        self.assertEqual(self.client.properties.create.call_args[0][0]["source"], PROPERTY_SOURCE)

    def test_upload_puts_the_file_under_the_measurement(self):
        self.upload()
        self.client.files.put.assert_called_once_with(
            self.folder / "measurement-1" / "files" / "a.txt",
            "measurements/measurement-id/a.txt",
            SIGNED_FILE,
        )

    def test_upload_signs_the_missing_files_once_per_measurement(self):
        self.upload()
        self.client.files.signed_urls.assert_called_once_with(["measurements/measurement-id/a.txt"], "putObject")

    def test_upload_does_not_list_the_files_of_a_new_measurement(self):
        self.upload()
        self.client.measurements.list_files.assert_not_called()

    def test_upload_again_creates_and_puts_nothing(self):
        self.upload(present=True)
        writes = [
            name
            for name, _, _ in self.client.mock_calls
            if name.endswith(("create", "create_set", "signed_urls", "put"))
        ]
        self.assertEqual(writes, [])

    @mock.patch("time.sleep")
    def test_upload_puts_a_file_again_after_network_errors(self, mock_sleep):
        self.client.files.put.side_effect = [requests.exceptions.ConnectionError()] * 2 + [None]
        self.upload()
        self.assertEqual(self.client.files.put.call_count, 3)

    @mock.patch.dict("os.environ", {}, clear=True)
    def test_load_credentials_takes_the_platform_from_the_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "api_token_cache.json")
            with open(path, "w") as file_:
                json.dump(STORED_CREDENTIALS, file_)
            with mock.patch.object(upload, "CREDENTIALS_FILE_PATH", path):
                environment = upload.load_credentials()[2]
        self.assertEqual((environment.host, environment.port, environment.secure), ("localhost", 3000, False))
