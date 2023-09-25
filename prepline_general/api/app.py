from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
import json
import logging
import os
import traceback

from .general import router as general_router

logger = logging.getLogger("unstructured_api")


app = FastAPI(
    title="Unstructured Pipeline API",
    description="""""",
    version="1.0.0",
    docs_url="/general/docs",
    openapi_url="/general/openapi.json",
)

# Note(austin) - This logger just dumps exceptions
# We'd rather handle those below
uvicorn_logger = logging.getLogger("uvicorn.error")
uvicorn_logger.disabled = True


# Catch all HTTPException for uniform logging and response
@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, e: HTTPException):
    logger.error(e.detail)

    return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


# Note(austin) - Convert any other errors to HTTPException
# to be handled above, and log the stack trace
@app.exception_handler(Exception)
async def error_handler(request: Request, e: Exception):
    trace = traceback.format_exc()

    # Note(austin) - If ENV is set, dump the stack in json
    # for nicer parsing. Soon we'll just have a json logger do this.
    if os.environ.get("ENV") in ["dev", "prod"]:
        trace = json.dumps(trace)

    logger.error(trace)

    error = HTTPException(status_code=500, detail=str(e))

    return await http_error_handler(request, error)


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
