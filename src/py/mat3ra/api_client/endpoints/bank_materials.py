from .bank_entity import BankEntityEndpoints
from .enums import DEFAULT_API_VERSION, SECURE
from ..utils.query import PAGINATION_PARAMETERS


class BankMaterialEndpoints(BankEntityEndpoints):
    """
    Bank material endpoints.

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

    list_parameters = (
        "id",
        "slug",
        "name",
        "quickSearch",
        "isCurated",
        "formula",
        *PAGINATION_PARAMETERS,
    )
    query_fields = {"_id": "id", "name": "name", "formula": "formula", "slug": "slug", "isCurated": "isCurated"}

    def __init__(self, host, port, account_id, auth_token, version=DEFAULT_API_VERSION, secure=SECURE, **kwargs):
        super(BankMaterialEndpoints, self).__init__(host, port, account_id, auth_token, version, secure, **kwargs)
        self.name = "bank-materials"
