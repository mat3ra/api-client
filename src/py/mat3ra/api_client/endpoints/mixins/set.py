import json


class EntitySetEndpointsMixin(object):
    """
    Entity Set endpoints mixin.
    """

    def create_set(self, config):
        """
        Creates a new entity set.

        Args:
            config (dict): entity set config.

        Returns:
             dict: new entity set.
        """
        path_ = "/".join((self.name, "create-set"))
        return self.request("PUT", path_, data=json.dumps(config), headers=self.headers)

    def move_to_set(self, _id, old_set_id, new_set_id):
        """
        Moves a entity with given ID to a new set.

        Args:
            _id (str): entity ID.
            old_set_id (str): old entity set ID.
            new_set_id (str): new entity set ID.
        """
        params = {"oldSetId": old_set_id, "newSetId": new_set_id}
        self.request("POST", "/".join((self.name, _id, "move-to-set")), params=params, headers=self.headers)


class EntitySetUpdateEndpointsMixin(object):
    """
    Entity Set update endpoints mixin.
    """

    def update_set(self, _id, config):
        """
        Updates a entity set with given ID.

        Args:
            _id (str): entity set ID.
            config (dict): entity set config.

        Returns:
             dict: updated entity set.
        """
        path_ = "/".join((self.name, _id, "update-set"))
        return self.request("PUT", path_, data=json.dumps(config), headers=self.headers)
