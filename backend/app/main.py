import logging
import uuid

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.db.session import engine
from app.modules.academic_years.api import router as years_router
from app.modules.audit.api import router as audit_router
from app.modules.auth.api import router as auth_router
from app.modules.curricula.api import router as curricula_router
from app.modules.dashboard.api import router as dashboard_router
from app.modules.groups.api import router as groups_router
from app.modules.org.api import router as org_router
from app.modules.teachers.api import router as teachers_router
from app.modules.tenants.api import platform_router
from app.modules.tenants.api import router as university_router
from app.modules.users.api import router as users_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="UniLoad API",
        version="0.1.0",
        description="Universitet o‘quv yuklamalarini avtomatlashtirish platformasi — REST API.",
        docs_url="/docs",
        openapi_url=f"{API_PREFIX}/openapi.json",
    )
    install_error_handlers(app)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = rid[:64]
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    api = APIRouter(prefix=API_PREFIX)
    for r in (auth_router, university_router, platform_router, users_router, years_router,
              dashboard_router, audit_router, org_router, curricula_router, groups_router, teachers_router):
        api.include_router(r)

    @api.get("/health", tags=["Tizim"], summary="Liveness / readiness")
    def health():
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}

    app.include_router(api)
    return app


app = create_app()
