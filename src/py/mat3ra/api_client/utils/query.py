"""
Translation of Mongo-style list queries into the flat filters of the platform's list endpoints.

The list endpoints validate their parameters against a declared set of flat keys (e.g. `ownerId`,
`hashes`) and silently drop anything else - including the `query=<json>` blob `list()` sends. An
endpoint opts in by declaring:
    list_parameters: the flat parameters of its list use case, which `list()` accepts directly;
    query_fields: the Mongo field paths it can still translate, each mapped to a flat parameter.
"""

OWNED_ENTITY_QUERY_FIELDS = {
    "_id": "id",
    "owner._id": "ownerId",
    "owner.slug": "ownerSlug",
    "name": "name",
    "isDefault": "isDefault",
}

PAGINATION_PARAMETERS = ("limit", "skip", "sort")
BOOLEAN_PARAMETERS = ("isDefault", "isEntitySet", "isCurated")
PROJECTION_OPTIONS = ("limit", "skip", "sort", "fields")


def _unsupported_condition(field):
    return ValueError(
        f'Unsupported condition on query field "{field}". Supported: a value, $eq, $in and, for boolean fields, $ne.'
    )


def _translate_condition(field, parameter, condition):
    if not isinstance(condition, dict):
        return condition
    if len(condition) != 1:
        raise _unsupported_condition(field)

    ((operator, operand),) = condition.items()
    if operator == "$eq":
        return operand
    if operator == "$in" and isinstance(operand, (list, tuple)):
        return list(operand)
    if operator == "$ne" and isinstance(operand, bool) and parameter in BOOLEAN_PARAMETERS:
        return not operand
    raise _unsupported_condition(field)


def _to_parameter_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return [_to_parameter_value(item) for item in value]
    return value


def _translate_direct_value(parameter, value):
    if isinstance(value, dict):
        if parameter == "sort":
            return _translate_sort(value)
        raise ValueError(f'"{parameter}" is a list parameter: pass a value or a list, not a condition.')
    return _to_parameter_value(value)


def uses_list_parameters(query, query_fields, list_parameters):
    """
    Whether a query uses the list parameters of the endpoint (e.g. `ownerId`) rather than Mongo field paths
    (e.g. `owner._id`). Such a query means exactly what the list endpoint says.
    """
    return any(field in list_parameters and field not in query_fields for field in query)


def translate_query(query, query_fields, list_parameters=()):
    """
    Translates a query into flat list parameters.

    Args:
        query (dict): list parameters (passed on as they are), and/or Mongo field paths whose value may be a
            value, `$eq`, `$in` or (booleans) `$ne`.
        query_fields (dict): Mongo field path -> flat parameter name the endpoint accepts.
        list_parameters (tuple): flat parameters the endpoint accepts as they are.

    Returns:
        dict: flat parameters.

    Raises:
        ValueError: for a field or condition the endpoint cannot filter on.
    """
    parameters = {}
    for field, condition in query.items():
        if field in query_fields:
            parameter = query_fields[field]
            parameters[parameter] = _to_parameter_value(_translate_condition(field, parameter, condition))
        elif field in list_parameters:
            parameters[field] = _translate_direct_value(field, condition)
        else:
            supported = ", ".join((*list_parameters, *query_fields))
            raise ValueError(f'Unsupported query field "{field}". Supported: {supported}.')
    return parameters


def _translate_sort(sort):
    if isinstance(sort, str):
        return sort
    if not isinstance(sort, dict) or len(sort) != 1:
        raise ValueError("Unsupported sort: a single field, as a string or {field: 1 | -1}, is supported.")

    ((field, direction),) = sort.items()
    return f"-{field}" if direction in (-1, "desc") else field


def translate_projection(projection):
    """
    Translates the Mongo-style options of a list call into flat list parameters.

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
