try:
    from ._version import version as __version__
except ModuleNotFoundError:
    __version__ = None

from .client import APIClient
from .constants import ACCESS_TOKEN_ENV_VAR, CLIENT_ID, SCOPE, build_oidc_base_url
from .models import Account, APIEnv, AuthContext, AuthEnv
from .endpoints.bank_materials import BankMaterialEndpoints
from .endpoints.bank_workflows import BankWorkflowEndpoints
from .endpoints.files import FileEndpoints
from .endpoints.jobs import JobEndpoints
from .endpoints.login import LoginEndpoint
from .endpoints.logout import LogoutEndpoint
from .endpoints.materials import MaterialEndpoints
from .endpoints.metaproperties import MetaPropertiesEndpoints
from .endpoints.projects import ProjectEndpoints
from .endpoints.properties import PropertiesEndpoints
from .endpoints.workflows import WorkflowEndpoints
