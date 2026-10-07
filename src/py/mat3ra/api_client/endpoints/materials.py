import json
from .entity import EntityEndpoint
from .enums import DEFAULT_API_VERSION, SECURE
from ..utils.http import BaseConnection
from .mixins.default import DefaultableEntityEndpointsMixin
from .mixins.set import EntitySetEndpointsMixin
from ..utils.materials import get_materialsproject_url


class MaterialEndpoints(EntitySetEndpointsMixin, DefaultableEntityEndpointsMixin, EntityEndpoint):
    """
    Material endpoints.

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
        super(MaterialEndpoints, self).__init__(host, port, account_id, auth_token, version, secure, **kwargs)
        self.name = "materials"

    def import_from_file(self, name, content, owner_id=None, format="poscar", tags=()):
        """
        Imports a material from the given file.

        Args:
            name (str): material name.
            content (str): material as string.
            format (str): material format, either cif or poscar.
            owner_id (str): owner ID. Material is created under user's default account by default.
            tags (tuple[str]) a list of tags that should be assigned to the material.

        Returns:
            dict
        """
        data = {"name": name, "content": content, "format": format, "owner._id": owner_id, "tags": tags}
        return self.request("POST", "/".join((self.name, "import")), headers=self.headers, data=json.dumps(data))

    def import_from_materialsproject(self, api_key, material_ids, owner_id=None, tags=[]):
        """
        Imports a given material from materialsproject

        Args:
            api_key (str): materialsproject API key.
            material_ids (list): a list of materialsproject IDs.
            owner_id (str): material owner Id.
            tags (list): material tags,

        Returns:
            list[dict]: list of imported materials
        """
        materials = []
        conn = BaseConnection()
        with conn:
            for material_id in material_ids:
                conn.request("GET", get_materialsproject_url(material_id), params={"API_KEY": api_key})
                material = conn.json()["response"][0]
                tags.extend(material.get("tags", []))
                materials.append(self.import_from_file(material["material_id"], material["cif"], owner_id, "cif", tags))
        return materials
