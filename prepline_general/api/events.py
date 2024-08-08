import os
import threading

import psutil
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

is_shutting_down = False
is_memory_low = False
active_requests = 0
request_lock = threading.Lock()
shutdown_event = threading.Event()


def graceful_shutdown():
    global is_shutting_down
    is_shutting_down = True

    if active_requests > 0:
        shutdown_event.wait()



def get_memory_usage():
    try:
        with open('/sys/fs/cgroup/memory/memory.usage_in_bytes', 'r') as f:
            return int(f.read().strip())
    except FileNotFoundError:
        try:
            with open('/sys/fs/cgroup/memory.current', 'r') as f:
                return int(f.read().strip())
        except FileNotFoundError:
            mem = psutil.virtual_memory()
            return mem


def get_memory_limit():
    try:
        with open('/sys/fs/cgroup/memory/memory.limit_in_bytes', 'r') as f:
            return int(f.read().strip())
    except FileNotFoundError:
        try:
            with open('/sys/fs/cgroup/memory.max', 'r') as f:
                value = f.read().strip()
                return int(value) if value != 'max' else None
        except FileNotFoundError:
            mem = psutil.virtual_memory()
            return mem


def _check_free_memory():
    global is_memory_low  # 전역 변수로 is_memory_low를 사용

    usage = get_memory_usage()
    limit = get_memory_limit()

    print(f"Memory usage: {usage / 1024 / 1024:.2f} MB, Memory limit: {limit / 1024 / 1024:.2f} MB")

    if usage is None or limit is None:
        print("Unable to determine memory usage or limit. Assuming sufficient memory.")
        is_memory_low = False  # 충분한 메모리가 있다고 가정
        return True

    usage_threshold = limit * 0.8

    if usage >= usage_threshold:
        print(f"Memory usage ({usage / 1024 / 1024:.2f} MB) is above 80% of the limit ({usage_threshold / 1024 / 1024:.2f} MB)")
        is_memory_low = True
        return False
    else:
        print(f"Memory usage: {usage / 1024 / 1024:.2f} MB, below 80% of the limit ({usage_threshold / 1024 / 1024:.2f} MB)")
        is_memory_low = False
        return True


def healthcheck(_: Request):
    global is_shutting_down, is_memory_low, active_requests

    _check_free_memory()

    if is_shutting_down or is_memory_low:
        return JSONResponse(
            status_code=503,
            content={
                "status": "SHUTTING_DOWN",
                "reason": "Low memory" if is_memory_low else "Service is shutting down",
                "active_requests": active_requests
            }
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "HEALTHY",
            "active_requests": active_requests
        }
    )



class MemoryCheckMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        global is_memory_low, active_requests

        if request.url.path == "/general/v0/general":
            if is_memory_low:
                print(f"Service is currently unavailable due to low memory, {active_requests} active requests")
                raise HTTPException(status_code=503, detail="Service is currently unavailable due to low memory")

            with request_lock:
                active_requests += 1

            try:
                response = await call_next(request)
                return response
            finally:
                with request_lock:
                    active_requests -= 1
        else:
            return await call_next(request)