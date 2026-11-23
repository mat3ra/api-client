from mat3ra.esse.models.workflow.unit.io.object_storage import ObjectStorageIoSchema


def to_object_storage_input(cloud_file: dict) -> ObjectStorageIoSchema:
    """
    Converts an upload record into an `object_storage` input item for a workflow IO unit.

    Args:
        cloud_file (dict): A record returned by `client.files.upload` (mat3ra-api-client).

    Returns:
        ObjectStorageIoSchema: IO unit input item. The runner fetches it into the job's working directory under
            `basename`, which is what makes the user script's relative paths resolve.
    """
    return ObjectStorageIoSchema.model_validate(
        {
            "type": "object_storage",
            "basename": cloud_file["key"].split("/")[-1],
            "pathname": "",
            "objectData": {
                "NAME": cloud_file["key"],
                "PROVIDER": cloud_file["provider"],
                "CONTAINER": cloud_file["bucket"],
                "REGION": cloud_file["region"],
            },
        }
    )
