from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse

from fastapi.openapi.utils import get_openapi

import logging
import os

from .general import router as general_router

logger = logging.getLogger("unstructured_api")


app = FastAPI(
    title="Unstructured Pipeline API",
    description="API for the Unstructured Pipeline",
    version="0.0.57",
    docs_url="/general/docs",
    openapi_url="/general/openapi.json",
    servers=[
        {
            "url": "https://api.unstructured.io",
            "description": "Hosted API",
            "x-speakeasy-server-id": "prod"
        },
        {
            "url": "http://localhost:8000",
            "description": "Development server",
            "x-speakeasy-server-id": "local"
        }
    ],
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

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        summary=app.summary,
        description=app.description,
        routes=app.routes,
    )

    # Add retries
    openapi_schema["x-speakeasy-retries"] = {
        "strategy": "backoff",
        "backoff": {
            "initialInterval": 500,
            "maxInterval": 60000,
            "maxElapsedTime": 3600000,
            "exponent": 1.5,
        },
        "statusCodes": [
            "5XX",
        ],
        "retryConnectionErrors": True,
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

logger.info("Started Unstructured API")
