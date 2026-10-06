class DefaultableEntityEndpointsMixin(object):
    """
    Defaultable entity endpoints.
    """

    def set_default(self, id_):
        """
        Sets a entity with given ID as default.

        Args:
            id_ (str): entity ID.

        Returns:
             dict: new entity.
        """
        self.request("POST", "/".join((self.name, id_, "set-default")), headers=self.headers)
