import uuid

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import Ctx, require
from app.modules.teachers import service
from app.modules.teachers.models import EMPLOYMENT_TYPES, POSITIONS
from app.modules.teachers.schemas import (
    CatalogOut,
    EmploymentIn,
    EmploymentOut,
    EmploymentUpdateIn,
    HistoryItem,
    PositionNormOut,
    PositionNormsIn,
    TeacherIn,
    TeacherOut,
    TeacherUpdateIn,
)

router = APIRouter(tags=["Professor-o‘qituvchilar"])
_view = require("teachers.view")
_manage_any = require("teachers.manage")  # kafedra ko‘lami servisda tekshiriladi
_manage = require("teachers.manage", university_wide=True)


@router.get("/teachers/catalog", response_model=CatalogOut, summary="Lavozimlar va bandlik turlari")
def catalog(ctx: Ctx = Depends(_view)):
    return CatalogOut(positions=POSITIONS, employment_types=EMPLOYMENT_TYPES)


@router.get("/teachers", response_model=list[TeacherOut])
def list_teachers(q: str | None = Query(None, max_length=100), is_active: bool | None = None,
                  ctx: Ctx = Depends(_view)):
    return service.list_teachers(ctx, q, is_active)


@router.post("/teachers", response_model=TeacherOut, status_code=status.HTTP_201_CREATED)
def create_teacher(body: TeacherIn, ctx: Ctx = Depends(_manage)):
    return service.create_teacher(ctx, body)


@router.get("/teachers/{teacher_id}", response_model=TeacherOut)
def get_teacher(teacher_id: uuid.UUID, ctx: Ctx = Depends(_view)):
    return service.get_teacher(ctx, teacher_id)


@router.patch("/teachers/{teacher_id}", response_model=TeacherOut)
def update_teacher(teacher_id: uuid.UUID, body: TeacherUpdateIn, ctx: Ctx = Depends(_manage)):
    return service.update_teacher(ctx, teacher_id, body)


@router.get("/teachers/{teacher_id}/history", response_model=list[HistoryItem],
            summary="Yillar bo‘yicha bandlik tarixi")
def teacher_history(teacher_id: uuid.UUID, ctx: Ctx = Depends(_view)):
    return service.history(ctx, teacher_id)


@router.get("/years/{year_id}/employment", response_model=list[EmploymentOut], summary="Yillik bandlik")
def list_employment(year_id: uuid.UUID, department_id: uuid.UUID | None = None, teacher_id: uuid.UUID | None = None,
                    ctx: Ctx = Depends(_view)):
    return service.list_employment(ctx, year_id, department_id, teacher_id)


@router.post("/years/{year_id}/employment", response_model=EmploymentOut, status_code=status.HTTP_201_CREATED)
def create_employment(year_id: uuid.UUID, body: EmploymentIn, ctx: Ctx = Depends(_manage_any)):
    return service.create_employment(ctx, year_id, body)


@router.patch("/years/{year_id}/employment/{employment_id}", response_model=EmploymentOut)
def update_employment(year_id: uuid.UUID, employment_id: uuid.UUID, body: EmploymentUpdateIn,
                      ctx: Ctx = Depends(_manage_any)):
    return service.update_employment(ctx, year_id, employment_id, body)


@router.delete("/years/{year_id}/employment/{employment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employment(year_id: uuid.UUID, employment_id: uuid.UUID, ctx: Ctx = Depends(_manage_any)):
    service.delete_employment(ctx, year_id, employment_id)


@router.get("/years/{year_id}/position-norms", response_model=list[PositionNormOut], summary="Lavozim me’yorlari")
def list_norms(year_id: uuid.UUID, ctx: Ctx = Depends(_view)):
    return service.list_norms(ctx, year_id)


@router.put("/years/{year_id}/position-norms", response_model=list[PositionNormOut])
def replace_norms(year_id: uuid.UUID, body: PositionNormsIn, ctx: Ctx = Depends(_manage)):
    return service.replace_norms(ctx, year_id, body.norms)
