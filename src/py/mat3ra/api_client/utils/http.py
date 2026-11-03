import requests
import urllib.parse


def _extract_server_message(response: requests.Response) -> str:
    """Extract human-readable message from a JSEND-formatted error response body."""
    try:
        body = response.json()
        return body.get("data", {}).get("message") or body.get("message") or ""
    except Exception:
        return ""


class BaseConnection(object):
    """
    Base connection class to inherit from. This class should not be instantiated directly.

    Args:
        kwargs (dict): a dictionary of HTTP session options.
            timeout (int): session timeout in seconds.

    Attributes:
        session (requests.sessions.Session): session instance.
        response (requests.models.Response): response instance.
    """

    def __init__(self, **kwargs):
        self.response = None
        self.session = requests.Session()
        self.session.timeout = kwargs.get("timeout", 60)

    def request(self, method, url, params=None, data=None, headers=None):
        """
        Sends an HTTP request with given params, headers and data to the given url.

        Args:
            method (str): HTTP method to use.
            url (str): URL to send.
            headers (dict): headers to send.
            data (dict): the body to attach to the request.
            params (dict): URL parameters to append to the URL.
        """
        self.response = self.session.request(
            method=method.lower(), url=url, params=params, data=data, headers=headers, timeout=self.session.timeout
        )
        try:
            self.response.raise_for_status()
        except requests.HTTPError:
            status_code = self.response.status_code
            server_message = _extract_server_message(self.response)
            detail = server_message or "HTTP Error"
            message = f"Error {status_code}: {detail}."
            raise requests.HTTPError(message, response=self.response) from None

    def get_response(self):
        """
        Returns the HTTP response.

        Returns:
             requests.models.Response
        """
        return self.response

    def get_headers(self):
        """
        Returns case-insensitive dictionary of response headers.

        Returns:
             dict
        """
        return self.response.headers

    @property
    def status(self):
        """
        Returns integer code of responded HTTP Status, e.g. 404 or 200.

        Returns:
            int
        """
        return self.response.status_code

    @property
    def reason(self):
        """
        Returns the textual reason of responded HTTP Status, e.g. "Not Found" or "OK".

        Returns:
             str
        """
        return self.response.reason

    def content(self):
        """
        Returns content of the response in bytes.

        Returns:
            str
        """
        return self.response.content

    def json(self):
        """
        Returns the json-encoded content of a response, if any.

        Returns:
            dict
        """
        return self.response.json()

    def text(self):
        """
        Returns content of the response in unicode.

        Returns:
            str
        """
        return self.response.text

    def __enter__(self):
        """
        Support for "with" context.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Support for "with" context.
        """
        self.session.close()


class Connection(BaseConnection):
    """
    Exabyte connection class.

    Args:
        host (str): API hostname.
        port (int): API port number.
        version (str): API version.
        secure (bool): whether to use secure http protocol (https vs http).
        kwargs (dict): a dictionary of HTTP session options.
            timeout (int): session timeout in seconds.

    Attributes:
        preamble (str): common part of URL endpoints, e.g. https://platform.mat3ra.com:4000/api/v1/.
    """

    def __init__(self, host, port, version, secure, **kwargs):
        self.preamble = "{}://{}:{}/api/{}/".format("https" if secure else "http", host, port, version)
        super(Connection, self).__init__(**kwargs)

    def request(self, method, endpoint_path, params=None, data=None, headers=None):
        """
        Sends an HTTP request with given params, headers and data to the given endpoint.

        Args:
            method (str): HTTP method to use.
            endpoint_path (str): endpoint path.
            headers (dict): headers to send.
            data (dict): the body to attach to the request.
            params (dict): URL parameters to append to the URL.
        """
        url = urllib.parse.urljoin(self.preamble, endpoint_path)
        super(Connection, self).request(method, url, params, data, headers)
