import logging
import time
import uuid

logger = logging.getLogger("cine.request")


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        started = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response["X-Request-ID"] = request.request_id
        if request.path.startswith("/api/"):
            logger.info(
                "%s %s %s %sms rid=%s",
                request.method,
                request.get_full_path(),
                response.status_code,
                round(elapsed_ms, 1),
                request.request_id,
            )
        return response
