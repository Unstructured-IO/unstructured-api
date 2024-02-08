from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def set_custom_openapi(app: FastAPI) -> None:
    """Generate a custom OpenAPI schema for the app"""

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            summary=app.summary,
            description=app.description,
            servers=app.servers,
            routes=app.routes,
            tags=app.openapi_tags,
        )
        _apply_customizations(openapi_schema)

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore


def _apply_customizations(openapi_schema: dict[str, Any]) -> None:
    """Add customizations to the OpenAPI schema"""

    # Add security
    openapi_schema["security"] = [{"ApiKeyAuth": []}]

    # Add retries
    openapi_schema["x-speakeasy-retries"] = {
        "strategy": "backoff",
        "backoff": {
            "initialInterval": 500,
            "maxInterval": 60000,
            "maxElapsedTime": 900000,
            "exponent": 1.5,
        },
        "statusCodes": [
            "5xx",
        ],
        "retryConnectionErrors": True,
    }

    # Response changes
    openapi_schema["paths"]["/general/v0/general"]["post"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"] = {
        "items": {"$ref": "#/components/schemas/Element"},
        "title": "Response Partition Parameters",
        "type": "array",
    }

    # Schema changes

    # Add securitySchemes
    # TODO: Implement security per the FastAPI documentation:
    # https://fastapi.tiangolo.com/reference/security/?h=apikey
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "name": "unstructured-api-key",
            "in": "header",
            "x-speakeasy-example": "YOUR_API_KEY",
        }
    }

    # TODO: Instead of a list of paramaters, crete a PartitionParameters model
    # and declare schema keys (type, format, description) as attributes
    # https://fastapi.tiangolo.com/reference/openapi/models/?h=model
    # Update the schema key from `Body_partition` to `partition_paramaters`

    # TODO: Similarly, create an Element model
    # https://fastapi.tiangolo.com/reference/openapi/models/?h=model
    # Add Elements schema
    openapi_schema["components"]["schemas"]["Element"] = {
        "properties": {
            "type": {"type": "string", "title": "Type"},
            "element_id": {"type": "string", "title": "Element Id"},
            "metadata": {"type": "object", "title": "Metadata"},
            "text": {"type": "string", "title": "Text"},
        },
        "type": "object",
        "required": ["type", "element_id", "metadata", "text"],
        "title": "Element",
    }

    # Must manually correct the schema for the files parameter as due to a bug
    # described here: https://github.com/tiangolo/fastapi/discussions/10280
    # files parameter cannot be described with an annotation.
    # TODO: Check if the bug is fixed and remove this workaround
    for key in openapi_schema["components"]["schemas"]:
        if "partition_parameters" in key:
            general_pipeline_schema = openapi_schema["components"]["schemas"][key]
            break
    else:
        # Could not find the schema to update, returning
        return

    general_pipeline_schema["properties"]["files"] = {
        "type": "string",
        "format": "binary",
        "description": "The file to extract",
        "required": "true",
        "examples": [
            {
                "summary": "File to be partitioned",
                "externalValue": "https://github.com/Unstructured-IO/unstructured/blob/98d3541909f64290b5efb65a226fc3ee8a7cc5ee/example-docs/layout-parser-paper.pdf",
            }
        ],
    }
