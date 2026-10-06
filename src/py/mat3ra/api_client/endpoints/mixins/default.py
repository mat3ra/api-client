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

    def show_default(self, account_id=None):
        """
        Returns the default entity of the given account.

        Args:
            account_id (str): account ID. The user's default account is used if not specified.

        Returns:
             dict: default entity.
        """
        params = {"accountId": account_id} if account_id else None
        return self.request("GET", "/".join((self.name, "default")), params=params, headers=self.headers)
