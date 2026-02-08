from datetime import datetime

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

'''
Вспомогательная функция _error_response()

Принимает параметры status_code, detail, code, request. Возвращает стандартный FastAPI-ответ с JSON-телом.

Собираем единый формат ошибки.
'''
def _error_response(
    *,
    status_code: int,
    detail: str,
    code: str,
    request: Request,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": detail,
            "code": code,
            "path": request.url.path,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )

# Базовый класс AppError
class AppError(Exception):
    status_code = 400
    code = "app_error"
    detail = "Application error"

    def __init__(self, detail: str | None = None, code: str | None = None):
        if detail is not None:
            self.detail = detail
        if code is not None:
            self.code = code


# ================
# Кастомные ошибки
# ================

class NotFound(AppError):
    status_code = 404
    code = "not_found"
    detail = "Resource not found"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "permission_denied"
    detail = "You are not allowed to perform this action"


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return _error_response(
        status_code=exc.status_code,
        detail=exc.detail,
        code=exc.code,
        request=request,
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return _error_response(
        status_code=exc.status_code,
        detail=detail,
        code="http_error",
        request=request,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return _error_response(
        status_code=422,
        detail="Validation error",
        code="validation_error",
        request=request,
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return _error_response(
        status_code=500,
        detail="Internal server error",
        code="internal_server_error",
        request=request,
    )
