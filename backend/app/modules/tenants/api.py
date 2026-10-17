import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import text

from app.core.deps import Ctx, get_tenant_ctx, require, require_platform
from app.modules.tenants import service
from app.modules.tenants.schemas import (
    PlanCreateIn,
    PlanOut,
    PlatformUniversityOut,
    SubscriptionCreateIn,
    SubscriptionOut,
    SubscriptionUpdateIn,
    UniversityCreateIn,
    UniversityOut,
    UniversityPlatformUpdateIn,
    UniversityUpdateIn,
)

router = APIRouter(tags=["Universitet"])
platform_router = APIRouter(prefix="/platform", tags=["Platforma (Super Admin)"])

_tenants = require_platform("platform.tenants.manage")
_subs = require_platform("platform.subscriptions.manage")


@router.get("/university", response_model=UniversityOut, summary="O‘z universiteti")
def get_own(ctx: Ctx = Depends(get_tenant_ctx)):
    return service.get_own(ctx)


@router.patch("/university", response_model=UniversityOut, summary="Universitet profili va sozlamalari")
def update_own(body: UniversityUpdateIn, ctx: Ctx = Depends(require("settings.manage", university_wide=True))):
    return service.update_own(ctx, body)


@platform_router.get("/universities", response_model=list[PlatformUniversityOut])
def list_universities(ctx: Ctx = Depends(_tenants)):
    return service.list_universities(ctx)


@platform_router.post("/universities", response_model=PlatformUniversityOut, status_code=status.HTTP_201_CREATED,
                      summary="Universitet va birinchi administratorini yaratish")
def create_university(body: UniversityCreateIn, ctx: Ctx = Depends(_tenants)):
    return service.create_university(ctx, body)


@platform_router.get("/universities/{university_id}", response_model=PlatformUniversityOut)
def get_university(university_id: uuid.UUID, ctx: Ctx = Depends(_tenants)):
    return service.get_university(ctx, university_id)


@platform_router.patch("/universities/{university_id}", response_model=PlatformUniversityOut)
def update_university(university_id: uuid.UUID, body: UniversityPlatformUpdateIn, ctx: Ctx = Depends(_tenants)):
    return service.update_university(ctx, university_id, body)


@platform_router.get("/plans", response_model=list[PlanOut])
def list_plans(ctx: Ctx = Depends(_subs)):
    return service.list_plans(ctx)


@platform_router.post("/plans", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
def create_plan(body: PlanCreateIn, ctx: Ctx = Depends(_subs)):
    return service.create_plan(ctx, body)


@platform_router.get("/universities/{university_id}/subscriptions", response_model=list[SubscriptionOut])
def list_subscriptions(university_id: uuid.UUID, ctx: Ctx = Depends(_subs)):
    return service.list_subscriptions(ctx, university_id)


@platform_router.post("/universities/{university_id}/subscriptions", response_model=SubscriptionOut,
                      status_code=status.HTTP_201_CREATED)
def create_subscription(university_id: uuid.UUID, body: SubscriptionCreateIn, ctx: Ctx = Depends(_subs)):
    return service.create_subscription(ctx, university_id, body)


@platform_router.patch("/subscriptions/{subscription_id}", response_model=SubscriptionOut)
def update_subscription(subscription_id: uuid.UUID, body: SubscriptionUpdateIn, ctx: Ctx = Depends(_subs)):
    return service.update_subscription(ctx, subscription_id, body)


@platform_router.get("/health", summary="Tizim holati")
def health(ctx: Ctx = Depends(require_platform("platform.system.manage"))):
    db_ok = ctx.db.execute(text("SELECT 1")).scalar() == 1
    return {"database": "ok" if db_ok else "error"}
