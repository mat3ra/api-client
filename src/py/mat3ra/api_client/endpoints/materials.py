import json
from .entity import EntityEndpoint
from .enums import DEFAULT_API_VERSION, SECURE
from ..utils.http import BaseConnection, Connection
from .mixins.default import DefaultableEntityEndpointsMixin
from .mixins.set import EntitySetEndpointsMixin
from ..utils.materials import get_materialsproject_url

V1_API_VERSION = "v1"


class MaterialEndpoints(EntitySetEndpointsMixin, DefaultableEntityEndpointsMixin, EntityEndpoint):
    """
    Material endpoints. `get`, `create` and `update` go to `/api/v1`, the only route that carries a
    material's atomic constraints; the other methods stay on the given API version.

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
        self.account_id = account_id
        self.v1_conn = Connection(host, port, version=V1_API_VERSION, secure=secure, **kwargs)

    def get(self, id_):
        """
        Returns the material with the given ID, with its atomic constraints on `basis.constraints`.

        Args:
            id_ (str): material ID.

        Returns:
             dict: material.
        """
        return self._v1_request("GET", "/".join((self.name, id_)))["entity"]

    def create(self, config, owner_id=None):
        """
        Creates a new material, storing a non-empty `basis.constraints` with it.

        Args:
            config (dict): material config.
            owner_id (str): owner ID. Material is created under the client's account if not specified.

        Returns:
             dict: new material, as stored.
        """
        account_id = owner_id or (self.auth.account_id if self.auth else None) or self.account_id
        return self.get(self._save("POST", self.name, config, account_id)["id"])

    def update(self, id_, modifier, parameters=None):
        """
        Updates the material with the given ID, storing a non-empty `basis.constraints` with it.

        Args:
            id_ (str): material ID.
            modifier (dict): a dictionary of key-values to update the material with.
            parameters (dict): unused; the v1 route takes no request parameters.

        Returns:
             dict: updated material, as stored.
        """
        self._save("PUT", "/".join((self.name, id_)), modifier, self.get(id_)["owner"]["_id"])
        return self.get(id_)

    def _save(self, method, endpoint_path, material, account_id):
        data = {"accountId": account_id, "material": material}
        constraints = material.get("basis", {}).get("constraints")
        if constraints:
            data["constraints"] = constraints
        return self._v1_request(method, endpoint_path, data)

    def _v1_request(self, method, endpoint_path, data=None):
        """Sends a request to the v1 API, which reports a failure as a 200 response with status 0."""
        headers = {**self.headers, **self.auth.get_headers()} if self.auth else self.headers
        with self.v1_conn:
            self.v1_conn.request(method, endpoint_path, data=json.dumps(data) if data else None, headers=headers)
            response = self.v1_conn.json()
            if response["status"] != 1:
                raise BaseException(response["error"])
            return response["data"]

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
