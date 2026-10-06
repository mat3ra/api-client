"""
Helpers for the list endpoints that filter on `advancedSearches`.

A migrated list endpoint validates its parameters against the flat keys of its use case and silently drops
anything else - including the `query=<json>` blob `list()` sends. It does accept `advancedSearches`: raw Mongo
selectors, sent as a JSON string, applied next to the access scope. `list()` carries the whole query that way.
"""

PROJECTION_OPTIONS = ("limit", "skip", "sort", "fields")


def _translate_sort(sort):
    if isinstance(sort, str):
        return sort
    if not isinstance(sort, dict) or len(sort) != 1:
        raise ValueError("Unsupported sort: a single field, as a string or {field: 1 | -1}, is supported.")

    ((field, direction),) = sort.items()
    return f"-{field}" if direction in (-1, "desc") else field


def translate_projection(projection):
    """
    Translates the Mongo-style options of a list call into the pagination parameters of the endpoint.

    `limit`, `skip` and a single-field `sort` are honored. `fields` is ignored: the endpoints return whole
    documents, which can only be more than was asked for.

    Args:
        projection (dict): options, e.g. {"limit": 1, "sort": {"precision.value": -1}}.

    Returns:
        dict: flat parameters.

    Raises:
        ValueError: for an unsupported option or sort.
    """
    unsupported = [option for option in projection if option not in PROJECTION_OPTIONS]
    if unsupported:
        raise ValueError(
            f'Unsupported projection option "{unsupported[0]}". Supported: {", ".join(PROJECTION_OPTIONS)}.'
        )

    parameters = {option: projection[option] for option in ("limit", "skip") if option in projection}
    if "sort" in projection:
        parameters["sort"] = _translate_sort(projection["sort"])
    return parameters


def set_parameters(query):
    """
    The set parameters of a list that answers a Mongo query.

    The list endpoint defaults to top-level entities. A Mongo query means "anywhere" unless it names the set
    (`setId`) or asks for the sets themselves, which sit at the top level.

    Args:
        query (dict): Mongo query.

    Returns:
        dict
    """
    set_id = query.get("inSet._id")
    if isinstance(set_id, str):
        return {"setId": set_id}
    if query.get("isEntitySet") is True:
        return {}
    return {"globalSearch": "true"}
