import json  # noqa: F401

from ..models import AuthContext
from ..utils.http import Connection


class BaseEndpoint(object):
    """
    Base class for Exabyte RESTful API endpoints.

    Args:
        host (str): API hostname.
        port (int): API port number.
        version (str): API version. Defaults to 2018-10-1.
        secure (bool): whether to use secure http protocol (https vs http). Defaults to True.

    Attributes:
        conn (httplib.Connection): Connection instance.
    """

    def __init__(self, host, port, version="2018-10-1", secure=True, **kwargs):
        self._auth = kwargs.get("auth")
        self.conn = Connection(host, port, version=version, secure=secure, **kwargs)

    @property
    def auth(self):
        """
        Returns the auth context shared with the API client and its other endpoints.

        Returns:
            AuthContext
        """
        return self._auth

    def request(self, method, endpoint_path, params=None, data=None, headers=None):
        """
        Sends an HTTP request with given params, headers and data to the given endpoint.

        Args:
            method (str): HTTP method to use.
            endpoint_path (str): endpoint path.
            headers (dict): headers to send.
            data (dict): the body to attach to the request.
            params (dict): URL parameters to append to the URL.

        Returns:
            json: response
        """
        if headers:
            headers = self.get_request_headers(headers)
        with self.conn:
            self.conn.request(method, endpoint_path, params, data, headers)
            response = self.conn.json()
            if response["status"] != "success":
                raise BaseException(response["data"]["message"])
            return response["data"]

    def get_headers(self, account_id, auth_token, content_type="application/json"):
        auth = self._auth or AuthContext(account_id=account_id, auth_token=auth_token)
        return {**auth.get_headers(), "Content-Type": content_type}

    def get_request_headers(self, headers=None):
        """
        Returns the given headers, or the endpoint's own, with the current credentials of the auth context. Read per
        request, not at construction, so a token replaced on the shared AuthContext (a re-login) reaches every endpoint.

        Args:
            headers (dict): headers to send. Defaults to the endpoint's `headers`.

        Returns:
            dict
        """
        headers = self.headers if headers is None else headers
        return {**headers, **self._auth.get_headers()} if self._auth else headers
