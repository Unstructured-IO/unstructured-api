from fastapi import FastAPI, Request, status, HTTPException
from fastapi.datastructures import FormData
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
import logging
import os

from .general import router as general_router
from .openapi import set_custom_openapi

logger = logging.getLogger("unstructured_api")

app = FastAPI(
    title="Unstructured Pipeline API",
    summary="Partition documents with the Unstructured library",
    version="0.0.72",
    docs_url="/general/docs",
    openapi_url="/general/openapi.json",
    servers=[
        {
            "url": "https://api.unstructured.io",
            "description": "Hosted API",
            "x-speakeasy-server-id": "prod",
        },
        {
            "url": "http://localhost:8000",
            "description": "Development server",
            "x-speakeasy-server-id": "local",
        },
    ],
    openapi_tags=[{"name": "general"}],
)

# Note(austin) - This logger just dumps exceptions
# We'd rather handle those below, so disable this in deployments
uvicorn_logger = logging.getLogger("uvicorn.error")
if os.environ.get("ENV") in ["dev", "prod"]:
    uvicorn_logger.disabled = True


# Catch all HTTPException for uniform logging and response
@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, e: HTTPException):
    logger.error(e.detail)
    return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


# Catch any other errors and return as 500
@app.exception_handler(Exception)
async def error_handler(request: Request, e: Exception):
    return JSONResponse(status_code=500, content={"detail": str(e)})


allowed_origins = os.environ.get("ALLOWED_ORIGINS", None)
if allowed_origins:
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins.split(","),
        allow_methods=["OPTIONS", "POST"],
        allow_headers=["Content-Type"],
    )

app.include_router(general_router)

set_custom_openapi(app)


# Note(austin) - When FastAPI parses our FormData params,
# it builds lists out of duplicate keys, like so:
# FormData([('key', 'value1'), ('key', 'value2')])
#
# The Speakeasy clients send a more explicit form:
# FormData([('key[]', 'value1'), ('key[]', 'value2')])
#
# FastAPI doesn't understand these, so we need to transform them.
# Can't do this in middleware before the data stream is read, nor in the endpoint
# after the fields are parsed. Thus, we have to patch it into Request.form() on startup.
get_form = Request._get_form


async def patched_get_form(
    self,
    *,
    max_files: int | float = 1000,
    max_fields: int | float = 1000,
) -> FormData:
    """
    Call the original get_form, and iterate the results
    If a key has brackets at the end, remove them before returning the final FormData
    Note the extra params here are unused, but needed to match the signature
    """
    form_params = await get_form(self)

    fixed_params = []
    for key, value in form_params.multi_items():
        # Transform key[] into key
        if key and key.endswith("[]"):
            key = key[:-2]

        fixed_params.append((key, value))

    return FormData(fixed_params)


# Replace the private method with our wrapper
Request._get_form = patched_get_form  # type: ignore[assignment]


# Filter out /healthcheck noise
class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("/healthcheck") == -1


# Filter out /metrics noise
class MetricsCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("/metrics") == -1


logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())
logging.getLogger("uvicorn.access").addFilter(MetricsCheckFilter())


@app.get("/healthcheck", status_code=status.HTTP_200_OK, include_in_schema=False)
def healthcheck(request: Request):
    return {"healthcheck": "HEALTHCHECK STATUS: EVERYTHING OK!"}


logger.info("Started Unstructured API")
