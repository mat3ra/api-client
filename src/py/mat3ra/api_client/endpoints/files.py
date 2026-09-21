import hashlib
import json

import requests

from . import BaseEndpoint
from .enums import DEFAULT_API_VERSION, SECURE


class FileEndpoints(BaseEndpoint):
    """
    File endpoints.

    Args:
        host (str): API hostname.
        port (int): API port number.
        account_id (str): account ID.
        auth_token (str): authentication token.
        version (str): API version.
        secure (bool): whether to use secure http protocol (https vs http).
        kwargs (dict): a dictionary of HTTP session options.
            timeout (int): session timeout in seconds.

    Attributes:
        name (str): endpoint name.
        headers (dict): default HTTP headers.
    """

    def __init__(self, host, port, account_id, auth_token, version=DEFAULT_API_VERSION, secure=SECURE, **kwargs):
        super(FileEndpoints, self).__init__(host, port, version, secure, **kwargs)
        self.name = "files"
        self.headers = self.get_headers(account_id, auth_token)

    def create(self, name, body, account_id=None):
        """
        Creates a file in the account's folder.

        Args:
            name (str): file name, relative to the account's folder.
            body (str): file content: text, or a data URL (data:<type>;base64,...) for a file that is not text.
            account_id (str): account to act under. The caller's default account is used if not specified.

        Returns:
            dict: new file.
        """
        data = {"name": name, "body": body}
        if account_id:
            data["accountId"] = account_id
        return self.request("POST", self.name, data=json.dumps(data), headers=self.headers)

    def signed_urls(self, names, operation="getObject", account_id=None):
        """
        Returns pre-signed URLs for the given files.

        Args:
            names (list[str]): file names, relative to the account's folder.
            operation (str): getObject to download a file, putObject to upload one.
            account_id (str): account to act under. The caller's default account is used if not specified.

        Returns:
            list: [{"key": str, "signedUrl": str, "bucket": str, "region": str, "provider": str}]
        """
        data = {"names": names, "operation": operation}
        if account_id:
            data["accountId"] = account_id
        return self.request("POST", "/".join((self.name, "signed-urls")), data=json.dumps(data), headers=self.headers)

    def put(self, path, key, account_id=None):
        """
        Uploads a given file to the account's folder through a pre-signed URL.

        Args:
            path (str): path to the file to upload.
            key (str): file name, relative to the account's folder.
            account_id (str): account to act under. The caller's default account is used if not specified.

        Returns:
            dict: {"key": str, "bytes": int, "sha256": str} with the key the file is stored under.
        """
        signed_file = self.signed_urls([key], "putObject", account_id)[0]
        with open(path, "rb") as file_:
            content = file_.read()
        response = requests.put(signed_file["signedUrl"], data=content)
        response.raise_for_status()
        return {"key": signed_file["key"], "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
