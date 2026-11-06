import json
import mimetypes
from typing import Dict, List, Optional, Union

import requests

from . import BaseEndpoint
from .enums import DEFAULT_API_VERSION, SECURE

DEFAULT_CONTENT_TYPE = "application/octet-stream"
FileContent = Union[str, bytes]


class FileEndpoints(BaseEndpoint):
    """
    Files in the account's object storage folder ("Dropbox"). Names are relative to that folder.

    The file bytes never pass through the platform: it signs a URL per file, and the client sends
    the bytes to storage (or reads them from it) directly.

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
        self.timeout = kwargs.get("timeout", 60)

    def upload(self, files: Dict[str, FileContent], account_id: Optional[str] = None) -> List[dict]:
        """
        Uploads files to the account's folder. Text is uploaded as UTF-8.

        Args:
            files (dict): file content (str or bytes) by name, relative to the account's folder.
            account_id (str): account to upload under, the caller's default account if omitted.

        Returns:
            list[dict]: one record per file, in the order given, with `name`, `key`, `size`,
                `bucket`, `region` and `provider`.
        """
        contents = {name: _to_bytes(content) for name, content in files.items()}
        uploads = self.get_upload_urls([_describe(name, content) for name, content in contents.items()], account_id)
        records = []
        for (name, content), upload in zip(contents.items(), uploads):
            self._put(upload["signedUrl"], content, upload["headers"])
            records.append(_to_cloud_file(name, len(content), upload))
        return records

    def get_upload_urls(self, files: List[dict], account_id: Optional[str] = None) -> List[dict]:
        """
        Signs one PUT URL per file. The size and content type are part of the signature.

        Args:
            files (list[dict]): `name`, `size` (bytes) and `contentType` of each file.
            account_id (str): account to upload under, the caller's default account if omitted.

        Returns:
            list[dict]: `key`, `signedUrl`, `headers` (to send with the PUT as given), `bucket`,
                `region` and `provider` of each file.
        """
        return self._sign({"files": files, "operation": "putObject"}, account_id)

    def get_download_urls(self, names: List[str], account_id: Optional[str] = None) -> List[dict]:
        """
        Signs one GET URL per file. A name ending in "/" is a folder: every file under it is signed.

        Args:
            names (list[str]): file names, relative to the account's folder.
            account_id (str): account the files belong to, the caller's default account if omitted.

        Returns:
            list[dict]: `key` and `signedUrl` of each file.
        """
        return self._sign({"names": names, "operation": "getObject"}, account_id)

    def delete(self, names: List[str], account_id: Optional[str] = None) -> dict:
        """
        Deletes files. A name ending in "/" is a folder: everything under it is deleted.

        Args:
            names (list[str]): file names, relative to the account's folder.
            account_id (str): account the files belong to, the caller's default account if omitted.

        Returns:
            dict: `message` confirming the deletion.
        """
        data = json.dumps(_with_account({"names": names}, account_id))
        return self.request("DELETE", self.name, data=data, headers=self.headers)

    def _sign(self, payload: dict, account_id: Optional[str]) -> List[dict]:
        data = json.dumps(_with_account(payload, account_id))
        return self.request("POST", f"{self.name}/signed-urls", data=data, headers=self.headers)

    def _put(self, url: str, content: bytes, headers: Dict[str, str]) -> None:
        """PUTs the bytes to storage. The headers are part of the signature, so they are sent as given."""
        response = requests.put(url, data=content, headers=headers, timeout=self.timeout)
        if not response.ok:
            raise requests.HTTPError(
                f"Upload to storage failed with HTTP {response.status_code}: {response.text}", response=response
            )


def _to_bytes(content: FileContent) -> bytes:
    return content.encode("utf-8") if isinstance(content, str) else content


def _describe(name: str, content: bytes) -> dict:
    """What the platform signs for an upload: the name, the exact size and the content type."""
    return {"name": name, "size": len(content), "contentType": mimetypes.guess_type(name)[0] or DEFAULT_CONTENT_TYPE}


def _with_account(payload: dict, account_id: Optional[str]) -> dict:
    return {**payload, "accountId": account_id} if account_id else payload


def _to_cloud_file(name: str, size: int, upload: dict) -> dict:
    return {
        "name": name,
        "key": upload["key"],
        "size": size,
        "bucket": upload["bucket"],
        "region": upload["region"],
        "provider": upload["provider"],
    }
