import uuid

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import Ctx, get_tenant_ctx, require
from app.core.schemas import Page, PageParams
from app.modules.users import service
from app.modules.users.schemas import (
    PermissionOut,
    RoleCreateIn,
    RoleDetailOut,
    RoleOut,
    RolesReplaceIn,
    RoleUpdateIn,
    UserCreateIn,
    UserDetailOut,
    UserOut,
    UserUpdateIn,
)

router = APIRouter(tags=["Foydalanuvchilar va rollar"])
_manage = require("users.manage", university_wide=True)


@router.get("/users", response_model=Page[UserOut], summary="Foydalanuvchilar ro‘yxati")
def list_users(params: PageParams = Depends(), q: str | None = Query(None, max_length=100),
               is_active: bool | None = None, ctx: Ctx = Depends(_manage)):
    return service.list_users(ctx, params, q, is_active)


@router.post("/users", response_model=UserDetailOut, status_code=status.HTTP_201_CREATED,
             summary="Foydalanuvchi yaratish")
def create_user(body: UserCreateIn, ctx: Ctx = Depends(_manage)):
    return service.create_user(ctx, body)


@router.get("/users/{user_id}", response_model=UserDetailOut)
def get_user(user_id: uuid.UUID, ctx: Ctx = Depends(_manage)):
    return service.get_user(ctx, user_id)


@router.patch("/users/{user_id}", response_model=UserDetailOut, summary="Tahrirlash yoki bloklash")
def update_user(user_id: uuid.UUID, body: UserUpdateIn, ctx: Ctx = Depends(_manage)):
    return service.update_user(ctx, user_id, body)


@router.put("/users/{user_id}/roles", response_model=UserDetailOut, summary="Rollar va ko‘lamlarni belgilash")
def replace_roles(user_id: uuid.UUID, body: RolesReplaceIn, ctx: Ctx = Depends(_manage)):
    return service.replace_user_roles(ctx, user_id, body.roles)


@router.get("/roles", response_model=list[RoleOut])
def list_roles(ctx: Ctx = Depends(_manage)):
    return service.list_roles(ctx)


@router.post("/roles", response_model=RoleDetailOut, status_code=status.HTTP_201_CREATED)
def create_role(body: RoleCreateIn, ctx: Ctx = Depends(_manage)):
    return service.create_role(ctx, body)


@router.get("/roles/{role_id}", response_model=RoleDetailOut)
def get_role(role_id: uuid.UUID, ctx: Ctx = Depends(_manage)):
    return service.get_role(ctx, role_id)


@router.patch("/roles/{role_id}", response_model=RoleDetailOut)
def update_role(role_id: uuid.UUID, body: RoleUpdateIn, ctx: Ctx = Depends(_manage)):
    return service.update_role(ctx, role_id, body)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(role_id: uuid.UUID, ctx: Ctx = Depends(_manage)):
    service.delete_role(ctx, role_id)


@router.get("/permissions", response_model=list[PermissionOut], summary="Ruxsatlar katalogi")
def list_permissions(ctx: Ctx = Depends(get_tenant_ctx)):
    return service.list_permissions(ctx.db)
