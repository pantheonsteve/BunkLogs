"""OpenAPI schema includes local-dev organization routing fields."""

from config.utils import add_organization_context_to_schema


def test_add_organization_context_to_schema_documents_v1_operations():
    schema = {
        "paths": {
            "/api/v1/dashboards/group/{group_id}/": {
                "get": {
                    "parameters": [{"name": "group_id", "in": "path", "required": True}],
                    "security": [{"jwtAuth": []}],
                },
            },
            "/api/auth/token/": {
                "post": {"security": []},
            },
        },
    }

    result = add_organization_context_to_schema(schema, generator=None, request=None, public=True)

    op = result["paths"]["/api/v1/dashboards/group/{group_id}/"]["get"]
    param_names = {(p["in"], p["name"]) for p in op["parameters"]}
    assert ("header", "X-Organization-Slug") in param_names
    assert ("query", "org") in param_names
    assert op["security"] == [{"jwtAuth": [], "organizationSlug": []}]

    token_op = result["paths"]["/api/auth/token/"]["post"]
    assert "organizationSlug" not in str(token_op)
