import json

from ..utils.query import translate_projection, translate_query, uses_list_parameters
from . import BaseEndpoint
from .enums import DEFAULT_API_VERSION, SECURE


class EntityEndpoint(BaseEndpoint):
    """
    Exabyte Entity endpoint.

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
        list_parameters (tuple): flat parameters of the list endpoint, accepted by `list()` as they are.
        query_fields (dict): Mongo field path -> flat parameter, for endpoints whose list ignores the `query` blob.
            None where the endpoint still reads it.
    """

    list_parameters = ()
    query_fields = None

    def __init__(self, host, port, account_id, auth_token, version=DEFAULT_API_VERSION, secure=SECURE, **kwargs):
        super(EntityEndpoint, self).__init__(host, port, version, secure, **kwargs)
        self.name = None
        self.headers = self.get_headers(account_id, auth_token)

    def list(self, query=None, projection=None):
        """
        Returns a list of entities.

        Endpoints that filter on flat parameters take their list parameters directly (e.g. {"ownerId": id}); a
        Mongo-style query is translated into them (the `query` blob is still sent, for servers that read it).

        Args:
            query (dict): list parameters and/or a Mongo query. Defaults to {}.
            projection (dict): options: limit, skip, sort. Defaults to {}.

        Returns:
            list[dict]

        Raises:
            ValueError: if the endpoint cannot filter on a field or condition of the query.
        """
        params = {"query": json.dumps(query or {}), "projection": json.dumps(projection or {})}
        if self.query_fields is not None:
            filters = self.build_filter_parameters(query or {}, projection or {})
            if [] in filters.values():
                return []  # an empty $in matches nothing, but an empty parameter would be dropped and match everything
            params.update(filters)
        return self.request("GET", self.name, params=params, headers=self.headers)

    def build_filter_parameters(self, query, projection):
        """
        Translates a query and options into the flat parameters of the list endpoint.

        A Mongo-style query that does not mention a set means "anywhere", as it did before; set-aware endpoints would
        default to top-level entities. A query of list parameters means what the endpoint says: pass `globalSearch`.

        Args:
            query (dict): list parameters and/or a Mongo query.
            projection (dict): options: limit, skip, sort.

        Returns:
            dict
        """
        parameters = {
            **translate_query(query, self.query_fields, self.list_parameters),
            **translate_projection(projection),
        }
        is_mongo_style = not uses_list_parameters(query, self.query_fields, self.list_parameters)
        is_set_aware = "setId" in self.list_parameters
        if is_mongo_style and is_set_aware and "setId" not in parameters and parameters.get("isEntitySet") != "true":
            parameters["globalSearch"] = "true"
        return parameters

    def get(self, id_):
        """
        Returns a entity with given ID.

        Args:
            id_ (str): entity ID.

        Returns:
             dict: entity.
        """
        return self.request("GET", "/".join((self.name, id_)), headers=self.headers)

    def delete(self, id_):
        """
        Deletes a given entity.

        Args:
            id_ (str): entity ID.
        """
        return self.request("DELETE", "/".join((self.name, id_)), headers=self.headers)

    def update(self, id_, modifier, parameters=None):
        """
        Updates a entity with given ID.

        Args:
            id_ (str): entity ID.
            modifier (dict): a dictionary of key-values to update entity with.
            parameters (dict): additional request parameters.

        Returns:
             dict: updated entity.
        """
        return self.request("PATCH", "/".join((self.name, id_)), data=json.dumps(modifier), headers=self.headers,
                            params=parameters)

    def create(self, config, owner_id=None):
        """
        Creates a new entity.

        Args:
            config (dict): entity config.
            owner_id (str): owner ID. Entity is created under user's default account if not specified.

        Returns:
             dict: new entity.
        """
        if owner_id:
            config["owner"] = {"_id": owner_id}
        return self.request("PUT", "/".join((self.name, "create")), data=json.dumps(config), headers=self.headers)

    def copy(self, id_):
        """
        Copies a entity with given ID.

        Args:
            id_ (str): entity ID.

        Returns:
             dict: new entity.
        """
        return self.request("POST", "/".join((self.name, id_, "copy")), headers=self.headers)
