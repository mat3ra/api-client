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

    def signed_urls(self, names, operation="getObject"):
        """
        Returns pre-signed URLs for the given files.

        Args:
            names (list[str]): file names, relative to the account's folder.
            operation (str): getObject to download a file, putObject to upload one.

        Returns:
            list: [{"key": str, "signedUrl": str, "bucket": str, "region": str, "provider": str}]
        """
        data = {"names": names, "operation": operation}
        return self.request("POST", "/".join((self.name, "signed-urls")), data=json.dumps(data), headers=self.headers)

    def put(self, path, key):
        """
        Uploads a given file to the account's folder through a pre-signed URL.

        Args:
            path (str): path to the file to upload.
            key (str): file name, relative to the account's folder.

        Returns:
            str: the key the file is stored under.
        """
        signed_file = self.signed_urls([key], "putObject")[0]
        with open(path, "rb") as file_:
            content = file_.read()
        response = requests.put(signed_file["signedUrl"], data=content, timeout=self.conn.session.timeout)
        response.raise_for_status()
        return signed_file["key"]
