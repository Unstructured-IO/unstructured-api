from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
import logging
import os

from prepline_general.api.endpoints import router as general_router
from prepline_general.api.openapi import set_custom_openapi

logger = logging.getLogger("unstructured_api")

app = FastAPI(
    title="Unstructured Pipeline API",
    summary="Partition documents with the Unstructured library",
    version="0.0.67",
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

app.include_router(general_router)

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


set_custom_openapi(app)

logger.info("Started Unstructured API")
