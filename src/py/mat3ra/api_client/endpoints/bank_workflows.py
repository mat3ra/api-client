from .bank_entity import BankEntityEndpoints
from .enums import DEFAULT_API_VERSION, SECURE


class BankWorkflowEndpoints(BankEntityEndpoints):
    """
    Bank workflow endpoints.

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
        super(BankWorkflowEndpoints, self).__init__(host, port, account_id, auth_token, version, secure, **kwargs)
        self.name = "bank-workflows"
