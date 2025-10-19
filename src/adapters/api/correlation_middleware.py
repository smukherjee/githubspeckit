from typing import Any
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
import uuid


class CorrelationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, header_name: str = "X-Correlation-ID") -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Any) -> Response:  # pragma: no cover simple propagation
        cid = request.headers.get(self.header_name) or str(uuid.uuid4())
        request.state.correlation_id = cid
        response = await call_next(request)
        response.headers[self.header_name] = cid
        return response

__all__ = ["CorrelationMiddleware"]
