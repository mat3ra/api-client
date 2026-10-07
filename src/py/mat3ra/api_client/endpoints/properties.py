from .entity import EntityEndpoint
from .enums import DEFAULT_API_VERSION, SECURE


class BasePropertiesEndpoints(EntityEndpoint):
    def build_property_selector(self, job_id, unit_flowchart_id, property_name):
        return {"source.info.jobId": job_id, "source.info.unitId": unit_flowchart_id, "data.name": property_name}

    def get_property(self, job_id, unit_flowchart_id, property_name):
        selector = self.build_property_selector(job_id, unit_flowchart_id, property_name)
        return self.list(query=selector)[0]

    def get_band_gap_by_type(self, job_id, unit_flowchart_id, type):
        band_gaps = self.get_property(job_id, unit_flowchart_id, "band_gaps")["data"]
        return next((v for v in band_gaps["values"] if v["type"] == type), None)["value"]

    def get_indirect_band_gap(self, job_id, unit_flowchart_id):
        return self.get_band_gap_by_type(job_id, unit_flowchart_id, "indirect")

    def get_direct_band_gap(self, job_id, unit_flowchart_id):
        return self.get_band_gap_by_type(job_id, unit_flowchart_id, "direct")


class PropertiesEndpoints(BasePropertiesEndpoints):
    """
    Properties endpoints.

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
        user_id (str): user ID.
        auth_token (str): authentication token.
        headers (dict): default HTTP headers.
    """

    def __init__(self, host, port, account_id, auth_token, version=DEFAULT_API_VERSION, secure=SECURE, **kwargs):
        super(PropertiesEndpoints, self).__init__(host, port, account_id, auth_token, version, secure, **kwargs)
        self.name = "properties"

    def delete(self, id_):
        raise NotImplementedError

    def update(self, id_, modifier):
        raise NotImplementedError

    def list_for_job(self, job_id):
        """
        List properties for a job grouped by unit.

        Args:
            job_id (str): Job ID.

        Returns:
            list[dict]: List of {"unit_id": str, "properties": [str, ...]}.
        """
        properties = self.list(query={"source.info.jobId": job_id})
        units = {}
        for prop in properties:
            unit_id = prop["source"]["info"]["unitId"]
            if unit_id not in units:
                units[unit_id] = []
            units[unit_id].append(prop["data"]["name"])
        return [{"unit_id": unit_id, "properties": names} for unit_id, names in units.items()]

    def get_for_job(self, job_id, property_name=None, unit_id=None):
        """
        Get property data for a job, optionally filtered by property name and/or unit.

        Args:
            job_id (str): Job ID.
            property_name (str, optional): Property name (e.g., "band_gaps", "total_energy").
            unit_id (str, optional): Unit flowchart ID (e.g., "pw-nscf").

        Returns:
            list[dict]: List of property data dicts.
        """
        query = {"source.info.jobId": job_id}
        if property_name:
            query["data.name"] = property_name
        if unit_id:
            query["source.info.unitId"] = unit_id
        return [prop["data"] for prop in self.list(query=query)]
