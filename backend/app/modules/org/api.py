import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import Ctx, require
from app.modules.org import service
from app.modules.org.schemas import (
    DepartmentIn,
    DepartmentOut,
    DepartmentUpdateIn,
    FacultyIn,
    FacultyOut,
    FacultyUpdateIn,
    ProgramIn,
    ProgramOut,
    ProgramUpdateIn,
)

router = APIRouter(tags=["Tashkiliy tuzilma"])
_org_view = require("org.view")
_org_manage = require("org.manage", university_wide=True)
_prog_view = require("programs.view")
_prog_manage = require("programs.manage", university_wide=True)
Q = Query(None, max_length=100)


@router.get("/faculties", response_model=list[FacultyOut], summary="Fakultetlar")
def list_faculties(q: str | None = Q, is_active: bool | None = None, ctx: Ctx = Depends(_org_view)):
    return service.list_faculties(ctx, q, is_active)


@router.post("/faculties", response_model=FacultyOut, status_code=status.HTTP_201_CREATED)
def create_faculty(body: FacultyIn, ctx: Ctx = Depends(_org_manage)):
    return service.create_faculty(ctx, body)


@router.patch("/faculties/{faculty_id}", response_model=FacultyOut)
def update_faculty(faculty_id: uuid.UUID, body: FacultyUpdateIn, ctx: Ctx = Depends(_org_manage)):
    return service.update_faculty(ctx, faculty_id, body)


@router.delete("/faculties/{faculty_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_faculty(faculty_id: uuid.UUID, ctx: Ctx = Depends(_org_manage)):
    service.delete_faculty(ctx, faculty_id)


@router.get("/departments", response_model=list[DepartmentOut], summary="Kafedralar")
def list_departments(q: str | None = Q, faculty_id: uuid.UUID | None = None, is_active: bool | None = None,
                     ctx: Ctx = Depends(_org_view)):
    return service.list_departments(ctx, q, faculty_id, is_active)


@router.post("/departments", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
def create_department(body: DepartmentIn, ctx: Ctx = Depends(_org_manage)):
    return service.create_department(ctx, body)


@router.patch("/departments/{department_id}", response_model=DepartmentOut,
              summary="Tahrirlash, nofaol qilish yoki boshqa kafedraga birlashtirish")
def update_department(department_id: uuid.UUID, body: DepartmentUpdateIn, ctx: Ctx = Depends(_org_manage)):
    return service.update_department(ctx, department_id, body)


@router.delete("/departments/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(department_id: uuid.UUID, ctx: Ctx = Depends(_org_manage)):
    service.delete_department(ctx, department_id)


@router.get("/programs", response_model=list[ProgramOut], tags=["Ta’lim yo‘nalishlari"])
def list_programs(q: str | None = Q, department_id: uuid.UUID | None = None,
                  degree: Literal["bachelor", "master"] | None = None, is_active: bool | None = None,
                  ctx: Ctx = Depends(_prog_view)):
    return service.list_programs(ctx, q, department_id, degree, is_active)


@router.post("/programs", response_model=ProgramOut, status_code=status.HTTP_201_CREATED,
             tags=["Ta’lim yo‘nalishlari"])
def create_program(body: ProgramIn, ctx: Ctx = Depends(_prog_manage)):
    return service.create_program(ctx, body)


@router.patch("/programs/{program_id}", response_model=ProgramOut, tags=["Ta’lim yo‘nalishlari"])
def update_program(program_id: uuid.UUID, body: ProgramUpdateIn, ctx: Ctx = Depends(_prog_manage)):
    return service.update_program(ctx, program_id, body)


@router.delete("/programs/{program_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Ta’lim yo‘nalishlari"])
def delete_program(program_id: uuid.UUID, ctx: Ctx = Depends(_prog_manage)):
    service.delete_program(ctx, program_id)
