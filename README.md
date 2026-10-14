[![PyPI version](https://badge.fury.io/py/mat3ra-api-client.svg)](https://badge.fury.io/py/mat3ra-api-client)

This package provides access to Mat3ra.com [RESTful API](https://docs.mat3ra.com/rest-api/overview/).

# Installation

We recommend creating a virtual environment before installing:

```bash
virtualenv my-virtualenv
source my-virtualenv/bin/activate
```

Install using pip:

- from PyPI:

```bash
pip install mat3ra-api-client
```

- from source code in development mode:

```bash
git clone git@github.com:Exabyte-io/api-client.git
cd api-client
pip install -e .
```

# Usage

```python
from mat3ra.api_client import APIClient

# Authenticate with OIDC token
client = APIClient.authenticate()

# Access endpoints
materials = client.materials.list()
```

# Uploading measurements

1. In the platform, under Samples, create a Sample Set for the wafer with its name and a description. Synthesis notes
   are fine as free text in the description.

2. Install the commands:

   ```bash
   pip install "git+https://github.com/mat3ra/api-client.git@548df39"
   ```

3. Sign in once, then confirm the printed code in the browser:

   ```bash
   API_HOST=<platform host> mat3ra-auth
   ```

   The account id, an API token that does not expire and the host are stored in `~/.mat3ra/api_token_cache.json`.

4. Upload a folder:

   ```bash
   mat3ra-upload <wafer set name> <folder>
   ```

   The measurements go into a measurement set named as in `set.json`, their samples into a sample set of the same name
   inside the wafer's set. Running it again uploads only what is missing.

## The folder

```
<folder>/
    set.json                   name, description, metadata of the measurement set
    workflow.json              the procedure, as a workflow document; used for every measurement
    measurements/<label>.json  name, description, status, setup, sample, metadata of one measurement
    properties/<label>.json    optional: a property of that measurement
    files/<label>/...          optional: files of that measurement, any names and layout, uploaded as found
```

- `setup` holds `instrument`, `session` and `settings` as the lab has them.
- `sample` is `{name, description, metadata}`, or just the name; samples are matched by name.
- A property file is accepted only for a property type the platform defines, listed in the
  [esse properties directory](https://github.com/mat3ra/esse/tree/dev/schema/properties_directory).
- Anything the folder has no field for goes into `metadata` of the record it describes and is shown as JSON.

Example: `tests/py/data/upload_folder/`.

# Examples

[api-examples](https://github.com/Exabyte-io/api-examples) repository contains examples for performing most-common tasks in the Mat3ra.com platform through its RESTful API in Jupyter Notebook format.

# Testing

The package uses pytest for testing. Tests are organized into unit and integration tests.

## Running Tests

### Unit Tests (No environment setup required)

Run all unit tests:
```bash
pytest tests/py/unit
```

### Integration Tests (Requires API credentials)

Integration tests require the following environment variables to be set:

- `TEST_HOST` - API host (e.g., `platform.mat3ra.com`)
- `TEST_PORT` - API port (e.g., `443`)
- `TEST_ACCOUNT_ID` - Your account ID
- `TEST_AUTH_TOKEN` - Your authentication token
- `TEST_SECURE` - Use HTTPS (optional, default: `False`)
- `TEST_VERSION` - API version (optional, default: `2018-10-01`)

To run integration tests:
```bash
export TEST_HOST=platform.mat3ra.com
export TEST_PORT=443
export TEST_ACCOUNT_ID=your-account-id
export TEST_AUTH_TOKEN=your-auth-token
export TEST_SECURE=true

pytest tests/py/integration
```

### Run All Tests

```bash
pytest tests/py
```

### Run Tests with Coverage

```bash
pytest tests/py/unit --cov=mat3ra.api_client --cov-report=term --cov-report=html
```

**Note:** Integration tests will be automatically skipped if required environment variables are not set.


© 2020 Exabyte Inc.
