"""
Utility functions for Django settings and DRF Spectacular customization.
"""

_ORG_CONTEXT_DESCRIPTION = (
    "Multi-tenant organization slug (e.g. clc). Required on localhost and other "
    "hosts without a tenant subdomain when OrganizationMiddleware cannot infer "
    "the org from the host or the user's Person record."
)

_ORG_SLUG_HEADER_PARAM = {
    "name": "X-Organization-Slug",
    "in": "header",
    "required": False,
    "schema": {"type": "string", "example": "clc"},
    "description": _ORG_CONTEXT_DESCRIPTION,
}

_ORG_SLUG_QUERY_PARAM = {
    "name": "org",
    "in": "query",
    "required": False,
    "schema": {"type": "string", "example": "clc"},
    "description": (
        "Alternative to X-Organization-Slug for local dev (DEBUG=True). "
        + _ORG_CONTEXT_DESCRIPTION
    ),
}

_HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "head", "options", "trace"})


def add_organization_context_to_schema(result, generator, request, public):
    """Document tenant routing overrides on every /api/v1/ operation."""
    paths = result.get("paths", {})
    for path, path_item in paths.items():
        if not path.startswith("/api/v1/"):
            continue
        for method, operation in path_item.items():
            if method not in _HTTP_METHODS or not isinstance(operation, dict):
                continue
            params = operation.setdefault("parameters", [])
            existing = {(p.get("in"), p.get("name")) for p in params if isinstance(p, dict)}
            if ("header", "X-Organization-Slug") not in existing:
                params.append(dict(_ORG_SLUG_HEADER_PARAM))
            if ("query", "org") not in existing:
                params.append(dict(_ORG_SLUG_QUERY_PARAM))

            security = operation.get("security")
            if not security:
                operation["security"] = [{"organizationSlug": []}]
            else:
                for requirement in security:
                    if isinstance(requirement, dict):
                        requirement.setdefault("organizationSlug", [])
    return result


def custom_operation_id_generator(path, method):
    """
    Custom operation ID generator to avoid collisions between similar endpoints.
    """
    # Remove leading/trailing slashes and split the path
    path_parts = path.strip("/").split("/")

    # Handle specific collision cases
    if "auth-token" in path_parts:
        # DRF's obtain_auth_token endpoint
        if method.lower() == "post":
            return "obtainAuthToken"
    elif "auth" in path_parts and "token" in path_parts:
        # JWT token endpoints
        if method.lower() == "post":
            return "jwtTokenCreate"
        if method.lower() == "patch":
            return "jwtTokenRefresh"
        if method.lower() == "get":
            return "jwtTokenVerify"

    # Default behavior for other endpoints
    method_name = method.lower()
    if method_name == "get":
        action = "retrieve" if "{id}" in path or "{pk}" in path else "list"
    elif method_name == "post":
        action = "create"
    elif method_name == "put":
        action = "update"
    elif method_name == "patch":
        action = "partialUpdate"
    elif method_name == "delete":
        action = "destroy"
    else:
        action = method_name

    # Create operation ID from path parts
    resource_name = "".join(word.capitalize() for word in path_parts if word not in ["api", "v1"])

    # Remove common suffixes for cleaner names
    resource_name = resource_name.replace("List", "").replace("Create", "").replace("Update", "").replace("Delete", "")

    return f"{resource_name}{action.capitalize()}"
