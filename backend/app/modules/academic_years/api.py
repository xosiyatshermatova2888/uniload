import uuid

from fastapi import APIRouter, Depends, status

from app.core.deps import Ctx, require
from app.modules.academic_years import service
from app.modules.academic_years.schemas import (
    AcademicYearCreateIn,
    AcademicYearDetailOut,
    AcademicYearOut,
    AcademicYearUpdateIn,
    CopyPreviewOut,
    SemesterOut,
    SemestersReplaceIn,
    TransitionIn,
)

router = APIRouter(tags=["O‘quv yillari"])
_view = require("academic_year.view")
_manage = require("academic_year.create", university_wide=True)


@router.get("/academic-years", response_model=list[AcademicYearOut], summary="O‘quv yillari ro‘yxati")
def list_years(ctx: Ctx = Depends(_view)):
    return service.list_years(ctx)


@router.post("/academic-years/preview", response_model=CopyPreviewOut,
             summary="Yangi yilni oldindan ko‘rish (hech narsa yozmaydi)")
def preview(body: AcademicYearCreateIn, ctx: Ctx = Depends(_manage)):
    return service.preview(ctx, body)


@router.post("/academic-years", response_model=AcademicYearDetailOut, status_code=status.HTTP_201_CREATED,
             summary="Yangi o‘quv yili yaratish (bo‘sh yoki nusxa)")
def create_year(body: AcademicYearCreateIn, ctx: Ctx = Depends(_manage)):
    return service.create_year(ctx, body)


@router.get("/academic-years/{year_id}", response_model=AcademicYearDetailOut)
def get_year(year_id: uuid.UUID, ctx: Ctx = Depends(_view)):
    return service.detail(ctx, service.get_year(ctx, year_id))


@router.patch("/academic-years/{year_id}", response_model=AcademicYearDetailOut)
def update_year(year_id: uuid.UUID, body: AcademicYearUpdateIn, ctx: Ctx = Depends(_manage)):
    return service.update_year(ctx, year_id, body)


@router.post("/academic-years/{year_id}/transitions", response_model=AcademicYearDetailOut,
             summary="Holatni o‘zgartirish")
def transition(year_id: uuid.UUID, body: TransitionIn, ctx: Ctx = Depends(_view)):
    # Kerakli ruxsat maqsad holatga bog‘liq — servis ichida tekshiriladi.
    return service.transition(ctx, year_id, body)


@router.post("/academic-years/{year_id}/set-current", response_model=AcademicYearDetailOut,
             summary="Joriy o‘quv yili qilish")
def set_current(year_id: uuid.UUID, ctx: Ctx = Depends(_manage)):
    return service.set_current(ctx, year_id)


@router.get("/years/{year_id}/semesters", response_model=list[SemesterOut])
def list_semesters(year_id: uuid.UUID, ctx: Ctx = Depends(_view)):
    return service.detail(ctx, service.get_year(ctx, year_id)).semesters


@router.put("/years/{year_id}/semesters", response_model=list[SemesterOut])
def replace_semesters(year_id: uuid.UUID, body: SemestersReplaceIn, ctx: Ctx = Depends(_manage)):
    return service.replace_semesters(ctx, year_id, body.semesters)
