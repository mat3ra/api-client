import json

from .entity import EntityEndpoint
from .enums import DEFAULT_API_VERSION, SECURE
from .mixins.set import EntitySetEndpointsMixin


class JobEndpoints(EntitySetEndpointsMixin, EntityEndpoint):
    """
    Job endpoints.

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

    advanced_searches = True
    searches_sets = True

    def __init__(self, host, port, account_id, auth_token, version=DEFAULT_API_VERSION, secure=SECURE, **kwargs):
        super(JobEndpoints, self).__init__(host, port, account_id, auth_token, version, secure, **kwargs)
        self.name = "jobs"

    def submit(self, id_):
        """
        Submits a given job.

        Args:
            id_ (str): job ID.
        """
        self.request("POST", "/".join((self.name, id_, "submit")), headers=self.headers)

    def purge(self, id_):
        """
        Purges a given job.

        Args:
            id_ (str): job ID.
        """
        self.request("POST", "/".join((self.name, id_, "submit")), headers=self.headers)

    def terminate(self, id_):
        """
        Terminates a given job.

        Args:
            id_ (str): job ID.
        """
        self.request("POST", "/".join((self.name, id_, "submit")), headers=self.headers)

    def build_config(self, material_ids, workflow_id, project_id, owner_id, name, compute=None,
                     is_multi_material=False):
        """
        Returns a job config based on the given parameters.

        Args:
            material_ids (list): list of material IDs.
            workflow_id (str): workflow ID.
            project_id (str): project ID.
            owner_id (str): owner ID.
            name (str): job name
            compute (dict): job compute configuration. Default config is used if not passed.
            is_multi_material (bool): whether the job is multi-material. Defaults to False.

        Returns:
            dict
        """
        config = {
            "_project": {"_id": project_id},
            "workflow": {"_id": workflow_id},
            "owner": {"_id": owner_id},
            "name": name,
        }

        if compute:
            config.update({"compute": compute})
        if is_multi_material:
            config.update({"_materials": [{"_id": id} for id in material_ids]})
        else:
            config.update({"_material": {"_id": material_ids[0]}})
        return config

    def build_compute_config(self, cluster, ppn=1, nodes=1, queue="D", time_limit="01:00:00", notify="abe"):
        """
        Returns job compute configuration.

        Args:
            cluster (str): cluster FQDN.
            ppn (int): processors per node.
            nodes (int): number of nodes.
            queue (str): queue name.
            time_limit (str): human walltime. Defaults to one hour.
            notify (str): RMS notification directives. Defaults to "abe" to receive email on abort, begin and end.

        Returns:
            dict
        """
        return {
            "ppn": ppn,
            "nodes": nodes,
            "queue": queue,
            "timeLimit": time_limit,
            "notify": notify,
            "cluster": {"fqdn": cluster},
            "arguments": {},
        }

    def create_by_ids(self, materials, workflow_id, project_id, prefix, owner_id=None, compute=None):
        """
        Creates jobs from the given materials

        Args:
            materials (list[dict]): list of materials.
            workflow_id (str): workflow ID.
            project_id (str): project ID.
            prefix (str): job prefix.
            owner_id (str, optional): owner ID.
            compute (dict, optional): compute configuration.

        Returns:
            list: List of created jobs.
        """
        jobs = []
        for material in materials:
            job_name = " ".join((prefix, material["formula"]))
            job_config = self.build_config([material["_id"]], workflow_id, project_id, owner_id, job_name, compute)
            jobs.append(self.create(job_config))
        return jobs

    def get_presigned_urls(self, id_, files):
        """
        Returns presigned URLS to upload given job files.

        Args:
            id_ (str): job ID.
            files (list): list of paths relative to the job working directory.

        Returns:
            list: [{"file": "", "URL": ""}]
        """
        data = json.dumps({"files": files})
        response = self.request("POST", "/".join((self.name, id_, "presigned-urls")), data=data, headers=self.headers)
        return response["presignedURLs"]

    def list_files(self, id_):
        """
        Returns a list of job files.

        Args:
            id_ (str): job ID.

        Returns:
            list: [{ "key" : str, "size" : int, "bucket" : str, "region" : str,
                     "provider" : str, "lastModified" : int, "name" : str, "signedURL" : str }]
        """
        response = self.request("GET", "/".join(("jobs", id_, "files")), headers=self.headers)
        return response

    def insert_output_files(self, id_, data):
        """
        Inserts job output files.
        Implements https://docs.mat3ra.com/api/#!/Job/post_jobs_id_output_files

        Args:
            id_ (str): job ID.

        Returns:
            None

        """
        self.request("POST", "/".join(("jobs", id_, "output-files")), data=data, headers=self.headers)
