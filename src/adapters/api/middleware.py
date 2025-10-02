from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
import uuid


class CorrelationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, header_name: str = "X-Correlation-ID"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):  # pragma: no cover simple propagation
        cid = request.headers.get(self.header_name) or str(uuid.uuid4())
        request.state.correlation_id = cid
        response = await call_next(request)
        response.headers[self.header_name] = cid
        return response

__all__ = ["CorrelationMiddleware"]
