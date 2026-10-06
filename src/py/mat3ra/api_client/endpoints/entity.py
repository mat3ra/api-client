import json

from ..utils.query import set_parameters, translate_projection
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
        advanced_searches (bool): whether the list endpoint filters on `advancedSearches` instead of the `query` blob.
        searches_sets (bool): whether the entities can be in sets (list endpoints default to the top level).
    """

    advanced_searches = False
    searches_sets = False

    def __init__(self, host, port, account_id, auth_token, version=DEFAULT_API_VERSION, secure=SECURE, **kwargs):
        super(EntityEndpoint, self).__init__(host, port, version, secure, **kwargs)
        self.name = None
        self.headers = self.get_headers(account_id, auth_token)

    def list(self, query=None, projection=None):
        """
        Returns a list of entities.

        Endpoints that filter on `advancedSearches` get the query as such (the `query` blob is still sent, for servers
        that read it). A query is answered "anywhere" unless it names a set, as it was before.

        Args:
            query (dict): Mongo query. Defaults to {}.
            projection (dict): options: limit, skip, sort. Defaults to {}.

        Returns:
            list[dict]

        Raises:
            ValueError: for an option or sort the endpoint does not support.
        """
        params = {"query": json.dumps(query or {}), "projection": json.dumps(projection or {})}
        if self.advanced_searches:
            params.update(self.build_advanced_search_parameters(query or {}, projection or {}))
        return self.request("GET", self.name, params=params, headers=self.headers)

    def build_advanced_search_parameters(self, query, projection):
        """
        Builds the parameters of an `advancedSearches` list.

        Args:
            query (dict): Mongo query.
            projection (dict): options: limit, skip, sort.

        Returns:
            dict
        """
        parameters = translate_projection(projection)
        if query:
            parameters["advancedSearches"] = json.dumps([query])
        if self.searches_sets:
            parameters.update(set_parameters(query))
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
