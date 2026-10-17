from datetime import UTC, datetime

from fastapi import APIRouter, Cookie, Depends, Request, Response, status

from app.core.config import get_settings
from app.core.deps import Ctx, get_ctx
from app.db.session import platform_session
from app.modules.auth import service
from app.modules.auth.schemas import (
    LoginIn,
    MeOut,
    PasswordChangeIn,
    PasswordForgotIn,
    PasswordResetIn,
    TokenOut,
)
from app.modules.users.models import User

router = APIRouter(prefix="/auth", tags=["Auth"])

REFRESH_COOKIE = "uniload_refresh"
COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, raw: str, expires: datetime) -> None:
    response.set_cookie(
        REFRESH_COOKIE, raw, httponly=True, secure=get_settings().cookie_secure, samesite="strict",
        path=COOKIE_PATH, max_age=int((expires - datetime.now(UTC)).total_seconds()),
    )


def _meta(request: Request) -> tuple[str | None, str | None]:
    return (request.client.host if request.client else None), request.headers.get("user-agent")


@router.post("/login", response_model=TokenOut, summary="Tizimga kirish")
def login(body: LoginIn, request: Request, response: Response) -> TokenOut:
    ip, ua = _meta(request)
    with platform_session() as db:
        issued = service.login(db, username=body.username, password=body.password, ip=ip, user_agent=ua)
    _set_refresh_cookie(response, issued.refresh_raw, issued.refresh_expires)
    return issued.token


@router.post("/refresh", response_model=TokenOut, summary="Access tokenni yangilash")
def refresh(request: Request, response: Response,
            uniload_refresh: str | None = Cookie(default=None)) -> TokenOut:
    ip, ua = _meta(request)
    with platform_session() as db:
        issued = service.refresh(db, raw_token=uniload_refresh, ip=ip, user_agent=ua)
    _set_refresh_cookie(response, issued.refresh_raw, issued.refresh_expires)
    return issued.token


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Chiqish")
def logout(request: Request, response: Response, uniload_refresh: str | None = Cookie(default=None)) -> None:
    ip, _ = _meta(request)
    with platform_session() as db:
        service.logout(db, raw_token=uniload_refresh, ip=ip)
    response.delete_cookie(REFRESH_COOKIE, path=COOKIE_PATH)


@router.get("/me", response_model=MeOut, summary="Joriy foydalanuvchi")
def me(ctx: Ctx = Depends(get_ctx)) -> MeOut:
    return service.build_me(ctx.db, ctx.db.get(User, ctx.principal.user_id))


@router.post("/password/change", status_code=status.HTTP_204_NO_CONTENT, summary="Parolni almashtirish")
def change_password(body: PasswordChangeIn, ctx: Ctx = Depends(get_ctx)) -> None:
    user = ctx.db.get(User, ctx.principal.user_id)
    service.change_password(ctx.db, user=user, current=body.current_password, new=body.new_password, ip=ctx.ip)


@router.post("/password/forgot", status_code=status.HTTP_204_NO_CONTENT, summary="Parolni tiklash so‘rovi")
def forgot_password(body: PasswordForgotIn, request: Request) -> None:
    ip, _ = _meta(request)
    with platform_session() as db:
        service.forgot_password(db, username=body.username, ip=ip)


@router.post("/password/reset", status_code=status.HTTP_204_NO_CONTENT, summary="Yangi parol o‘rnatish")
def reset_password(body: PasswordResetIn, request: Request) -> None:
    ip, _ = _meta(request)
    with platform_session() as db:
        service.reset_password(db, raw_token=body.token, new_password=body.new_password, ip=ip)
