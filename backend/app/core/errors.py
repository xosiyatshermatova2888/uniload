"""RFC 7807 (application/problem+json) xatolari."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm.exc import StaleDataError

log = logging.getLogger("uniload.errors")


class AppError(Exception):
    status: int = 400
    code: str = "BAD_REQUEST"
    title: str = "Noto‘g‘ri so‘rov"

    def __init__(
        self,
        detail: str | None = None,
        *,
        code: str | None = None,
        status: int | None = None,
        title: str | None = None,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(detail or self.title)
        self.detail = detail
        if code:
            self.code = code
        if status:
            self.status = status
        if title:
            self.title = title
        self.errors = errors or []


class NotFound(AppError):
    status, code, title = 404, "NOT_FOUND", "Topilmadi"


class Unauthorized(AppError):
    status, code, title = 401, "UNAUTHORIZED", "Avtorizatsiya talab qilinadi"


class Forbidden(AppError):
    status, code, title = 403, "FORBIDDEN", "Bu amal uchun ruxsat yo‘q"


class Conflict(AppError):
    status, code, title = 409, "CONFLICT", "Ziddiyat"


class ValidationFailed(AppError):
    status, code, title = 422, "VALIDATION_ERROR", "Ma’lumotlar noto‘g‘ri"


def problem(request: Request, status: int, code: str, title: str, detail: str | None = None,
            errors: list | None = None) -> JSONResponse:
    body = {
        "type": f"https://uniload.uz/errors/{code.lower()}",
        "title": title,
        "status": status,
        "code": code,
        "detail": detail,
        "errors": errors or [],
        "request_id": getattr(request.state, "request_id", None),
    }
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


def _db_error(request: Request, exc: DBAPIError) -> JSONResponse:
    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None)
    diag = getattr(orig, "diag", None)
    constraint = getattr(diag, "constraint_name", None)
    if sqlstate == "UL001":
        msg = getattr(diag, "message_primary", None) or "O‘quv yili qulflangan"
        return problem(request, 409, "YEAR_LOCKED", "O‘quv yili qulflangan", msg)
    if sqlstate == "UL002":
        msg = getattr(diag, "message_primary", None) or "O‘quv reja qulflangan"
        return problem(request, 409, "CURRICULUM_LOCKED", "O‘quv reja qulflangan", msg)
    if sqlstate == "23505":
        return problem(request, 409, "DUPLICATE", "Bunday yozuv allaqachon mavjud",
                       constraint, [{"constraint": constraint}])
    if sqlstate == "23503":
        return problem(request, 409, "REFERENCE_ERROR", "Bog‘liq yozuv mavjud emas yoki ishlatilmoqda",
                       "Bu yozuv boshqa ma’lumotlarda ishlatilmoqda yoki bog‘langan yozuv topilmadi. "
                       "O‘chirish o‘rniga nofaol qilib qo‘yishingiz mumkin.", [{"constraint": constraint}])
    if sqlstate == "23502":
        column = getattr(diag, "column_name", None)
        return problem(request, 422, "REQUIRED_FIELD", "Majburiy maydon bo‘sh qoldirildi", column,
                       [{"field": column}])
    if sqlstate == "23514":
        return problem(request, 422, "CHECK_FAILED", "Ma’lumot cheklovga mos emas",
                       constraint, [{"constraint": constraint}])
    if sqlstate == "42501":
        # RLS WITH CHECK buzilishi — boshqa tenantga yozishga urinish.
        return problem(request, 403, "FORBIDDEN", "Bu amal uchun ruxsat yo‘q")
    log.exception("Kutilmagan DB xatosi", exc_info=exc)
    return problem(request, 500, "INTERNAL_ERROR", "Ichki xatolik")


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        return problem(request, exc.status, exc.code, exc.title, exc.detail, exc.errors)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        errors = [{"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")}
                  for e in exc.errors()]
        return problem(request, 422, "VALIDATION_ERROR", "Ma’lumotlar noto‘g‘ri", None, errors)

    @app.exception_handler(StaleDataError)
    async def _stale(request: Request, exc: StaleDataError):
        return problem(request, 409, "CONCURRENT_UPDATE",
                       "Yozuv boshqa foydalanuvchi tomonidan o‘zgartirildi",
                       "Sahifani yangilab, qayta urinib ko‘ring.")

    @app.exception_handler(DBAPIError)
    async def _db(request: Request, exc: DBAPIError):
        return _db_error(request, exc)
