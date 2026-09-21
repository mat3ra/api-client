from .entity import EntityEndpoint
from .enums import DEFAULT_API_VERSION, SECURE
from .mixins.set import EntitySetEndpointsMixin, EntitySetUpdateEndpointsMixin


class MeasurementEndpoints(EntitySetEndpointsMixin, EntitySetUpdateEndpointsMixin, EntityEndpoint):
    """
    Measurement endpoints.

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
    """

    def __init__(self, host, port, account_id, auth_token, version=DEFAULT_API_VERSION, secure=SECURE, **kwargs):
        super(MeasurementEndpoints, self).__init__(host, port, account_id, auth_token, version, secure, **kwargs)
        self.name = "measurements"

    def files(self, id_):
        """
        Returns a list of measurement files.

        Args:
            id_ (str): measurement ID.

        Returns:
            list: [{"key": str, "signedUrl": str}]
        """
        return self.request("GET", "/".join((self.name, id_, "files")), headers=self.headers)
