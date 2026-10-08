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
        self.auth = kwargs.get("auth")
        self.conn = Connection(host, port, version=version, secure=secure, **kwargs)

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
        if headers and self.auth:
            headers = {**headers, **self.auth.get_headers()}
        with self.conn:
            self.conn.request(method, endpoint_path, params, data, headers)
            response = self.conn.json()
            if response["status"] != "success":
                raise BaseException(response["data"]["message"])
            return response["data"]

    def get_headers(self, account_id, auth_token, content_type="application/json"):
        auth = self.auth or AuthContext(account_id=account_id, auth_token=auth_token)
        return {**auth.get_headers(), "Content-Type": content_type}
