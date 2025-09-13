# observability/middleware.py
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from observability.metrics_chatgpt import LAT, REQS


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = rid
        start = time.perf_counter()
        response: Response = await call_next(request)
        duration = time.perf_counter() - start
        endpoint = request.url.path
        method = request.method
        code = str(response.status_code)
        REQS.labels(endpoint, method, code).inc()
        LAT.labels(endpoint, method, code).observe(duration)
        response.headers["X-Request-ID"] = rid
        return response
