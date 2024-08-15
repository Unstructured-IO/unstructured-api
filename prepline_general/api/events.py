import os
import threading
import logging
import psutil
from fastapi import Request, HTTPException, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Configuration
MAX_REQUESTS = int(os.getenv('MAX_REQUESTS', 1))
MEMORY_THRESHOLD = 0.8  # 80% of memory limit

# Global variables
is_memory_low = False
request_lock = threading.Lock()

# Global state variables
processed_requests = 0
is_ready = True
is_live = True
is_processing = False

# Logging setup
logger = logging.getLogger(__name__)


def get_memory_info():
    try:
        with open('/sys/fs/cgroup/memory/memory.usage_in_bytes', 'r') as f:
            usage = int(f.read().strip())
        with open('/sys/fs/cgroup/memory/memory.limit_in_bytes', 'r') as f:
            limit = int(f.read().strip())
    except FileNotFoundError:
        try:
            with open('/sys/fs/cgroup/memory.current', 'r') as f:
                usage = int(f.read().strip())
            with open('/sys/fs/cgroup/memory.max', 'r') as f:
                limit_value = f.read().strip()
                limit = int(limit_value) if limit_value != 'max' else None
        except FileNotFoundError:
            mem = psutil.virtual_memory()
            usage = mem.used
            limit = mem.total

    return usage, limit


def check_memory():
    global is_memory_low
    usage, limit = get_memory_info()

    if usage is None or limit is None:
        logger.warning("Unable to determine memory usage or limit. Assuming sufficient memory.")
        is_memory_low = False
        return None, None, is_memory_low

    logger.info(f"Memory usage: {usage / 1024 / 1024:.2f} MB, Memory limit: {limit / 1024 / 1024:.2f} MB")

    if usage >= limit * MEMORY_THRESHOLD:
        logger.warning(f"Memory usage ({usage / 1024 / 1024:.2f} MB) is above {MEMORY_THRESHOLD * 100}% of the limit")
        is_memory_low = True
    else:
        logger.info(f"Memory usage: {usage / 1024 / 1024:.2f} MB, below {MEMORY_THRESHOLD * 100}% of the limit")
        is_memory_low = False

    return usage, limit, is_memory_low


def update_state():
    global is_ready, is_live
    if processed_requests == 0:
        is_ready = is_live = True
    elif 0 < processed_requests < MAX_REQUESTS:
        is_ready = is_live = True
    else:
        is_ready = is_live = False


class NotReadyMarkingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, target_path="/general/v0/general"):
        super().__init__(app)
        self.target_path = target_path

    async def dispatch(self, request: Request, call_next):
        global processed_requests, is_ready, is_live, is_processing

        if request.url.path == self.target_path:
            if not is_ready or not is_live or is_processing:
                status = "not ready" if not is_ready else "no longer live" if not is_live else "processing"
                logger.info(f"Request rejected: Service is {status}")
                return Response(content=f"Service is {status}", status_code=503)

            is_ready = False
            is_processing = True
            processed_requests += 1
            logger.info(f"Processing request {processed_requests} of {MAX_REQUESTS}")

            try:
                response = await call_next(request)
                return response
            except Exception as e:
                logger.error(f"Error processing request: {str(e)}")
                raise
            finally:
                is_processing = False
                update_state()
                logger.info(
                    f"Request completed. Processed: {processed_requests}/{MAX_REQUESTS}. Ready: {is_ready}, Live: {is_live}")

        else:
            return await call_next(request)


class MemoryCheckMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        global is_memory_low

        if request.url.path == "/general/v0/general":
            if is_memory_low:
                logger.warning(f"Service is currently unavailable due to low memory")
                raise HTTPException(status_code=503, detail="Service is currently unavailable due to low memory")

        return await call_next(request)


def healthcheck(_: Request):
    usage, limit, is_memory_low = check_memory()

    if is_memory_low:
        return JSONResponse(
            status_code=503,
            content={
                "status": "UNHEALTHY",
                "reason": "Low memory",
                "memory_usage": usage,
                "memory_limit": limit
            }
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "HEALTHY",
            "memory_usage": usage,
            "memory_limit": limit
        }
    )


def ready_healthcheck(_: Request):
    if is_ready and not is_processing:
        return JSONResponse(
            status_code=200,
            content={
                "status": "READY",
                "processed_requests": processed_requests,
                "is_processing": is_processing,
                "max_requests_env": MAX_REQUESTS,
                "memory_usage": check_memory()
            }
        )
    else:
        return JSONResponse(
            status_code=503,
            content={
                "status": "NOT_READY",
                "processed_requests": processed_requests,
                "is_processing": is_processing,
                "max_requests_env": MAX_REQUESTS,
                "memory_usage": check_memory()
            }
        )


def live_healthcheck(_: Request):
    if is_live:
        return JSONResponse(
            status_code=200,
            content={
                "status": "LIVE",
                "processed_requests": processed_requests,
                "is_processing": is_processing,
                "max_requests_env": MAX_REQUESTS,
                "memory_usage": check_memory()
            }
        )
    else:
        return JSONResponse(
            status_code=503,
            content={
                "status": "NOT_LIVE",
                "processed_requests": processed_requests,
                "is_processing": is_processing,
                "max_requests_env": MAX_REQUESTS,
                "memory_usage": check_memory()
            }
        )
