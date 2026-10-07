"""예외 → HTTP 응답 통일. 라우터는 예외만 던지고 상태 코드·메시지 형식은 여기서 정한다."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str = "서버 오류가 발생했습니다."):
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ValidationError(AppError):
    status_code = 400
    code = "validation_error"


class LLMNotConfiguredError(AppError):
    status_code = 503
    code = "llm_not_configured"


class UpstreamError(AppError):
    status_code = 502
    code = "upstream_error"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"error": exc.code, "message": exc.message})

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        # Pydantic 검증 실패를 400 + 사람이 읽을 수 있는 메시지로
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(p) for p in first.get("loc", []) if p not in ("body", "query", "path"))
        msg = first.get("msg", "입력값이 올바르지 않습니다.")
        details = [{"loc": [str(p) for p in e.get("loc", [])], "msg": str(e.get("msg", "")), "type": str(e.get("type", ""))}
                   for e in exc.errors()]   # ctx 안의 예외 객체는 JSON 직렬화가 안 되므로 뺀다
        return JSONResponse(status_code=400, content={"error": "validation_error",
                                                      "message": f"{loc}: {msg}" if loc else msg,
                                                      "details": details})
