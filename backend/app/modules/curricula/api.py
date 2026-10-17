import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import Ctx, require
from app.modules.curricula import service
from app.modules.curricula.schemas import (
    CurriculumApproveIn,
    CurriculumDetailOut,
    CurriculumIn,
    CurriculumOut,
    CurriculumSubjectIn,
    CurriculumSubjectUpdateIn,
    CurriculumUpdateIn,
    LessonTypeIn,
    LessonTypeOut,
    LessonTypeUpdateIn,
    SubjectIn,
    SubjectOut,
    SubjectUpdateIn,
    VersionIn,
)

router = APIRouter(tags=["O‘quv rejalari va fanlar"])
_cur_view = require("curriculum.view")
_cur_manage = require("curriculum.manage", university_wide=True)
_cur_approve = require("curriculum.approve", university_wide=True)
_subj_view = require("subjects.view")
_subj_manage = require("subjects.manage", university_wide=True)


@router.get("/lesson-types", response_model=list[LessonTypeOut], summary="Mashg‘ulot turlari")
def list_lesson_types(ctx: Ctx = Depends(_cur_view)):
    return service.list_lesson_types(ctx)


@router.post("/lesson-types", response_model=LessonTypeOut, status_code=status.HTTP_201_CREATED)
def create_lesson_type(body: LessonTypeIn, ctx: Ctx = Depends(_cur_manage)):
    return service.create_lesson_type(ctx, body)


@router.patch("/lesson-types/{lesson_type_id}", response_model=LessonTypeOut)
def update_lesson_type(lesson_type_id: uuid.UUID, body: LessonTypeUpdateIn, ctx: Ctx = Depends(_cur_manage)):
    return service.update_lesson_type(ctx, lesson_type_id, body)


@router.delete("/lesson-types/{lesson_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson_type(lesson_type_id: uuid.UUID, ctx: Ctx = Depends(_cur_manage)):
    service.delete_lesson_type(ctx, lesson_type_id)


@router.get("/subjects", response_model=list[SubjectOut], summary="Fanlar katalogi")
def list_subjects(q: str | None = Query(None, max_length=100), department_id: uuid.UUID | None = None,
                  is_active: bool | None = None, ctx: Ctx = Depends(_subj_view)):
    return service.list_subjects(ctx, q, department_id, is_active)


@router.post("/subjects", response_model=SubjectOut, status_code=status.HTTP_201_CREATED)
def create_subject(body: SubjectIn, ctx: Ctx = Depends(_subj_manage)):
    return service.create_subject(ctx, body)


@router.patch("/subjects/{subject_id}", response_model=SubjectOut)
def update_subject(subject_id: uuid.UUID, body: SubjectUpdateIn, ctx: Ctx = Depends(_subj_manage)):
    return service.update_subject(ctx, subject_id, body)


@router.delete("/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(subject_id: uuid.UUID, ctx: Ctx = Depends(_subj_manage)):
    service.delete_subject(ctx, subject_id)


@router.get("/curricula", response_model=list[CurriculumOut], summary="O‘quv rejalari")
def list_curricula(program_id: uuid.UUID | None = None,
                   status: Literal["draft", "approved", "archived"] | None = None,
                   admission_year: int | None = None,
                   education_form: Literal["full_time", "part_time", "evening", "distance"] | None = None,
                   ctx: Ctx = Depends(_cur_view)):
    return service.list_curricula(ctx, program_id, status, admission_year, education_form)


@router.post("/curricula", response_model=CurriculumDetailOut, status_code=status.HTTP_201_CREATED,
             summary="Yangi o‘quv reja (qoralama)")
def create_curriculum(body: CurriculumIn, ctx: Ctx = Depends(_cur_manage)):
    return service.create_curriculum(ctx, body)


@router.get("/curricula/{curriculum_id}", response_model=CurriculumDetailOut,
            summary="O‘quv reja: semestrlar × fanlar × mashg‘ulot turlari")
def get_curriculum(curriculum_id: uuid.UUID, ctx: Ctx = Depends(_cur_view)):
    return service.detail(ctx, curriculum_id)


@router.patch("/curricula/{curriculum_id}", response_model=CurriculumDetailOut)
def update_curriculum(curriculum_id: uuid.UUID, body: CurriculumUpdateIn, ctx: Ctx = Depends(_cur_manage)):
    return service.update_curriculum(ctx, curriculum_id, body)


@router.delete("/curricula/{curriculum_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_curriculum(curriculum_id: uuid.UUID, ctx: Ctx = Depends(_cur_manage)):
    service.delete_curriculum(ctx, curriculum_id)


@router.post("/curricula/{curriculum_id}/approve", response_model=CurriculumDetailOut,
             summary="Versiyani tasdiqlash (shundan keyin o‘zgarmaydi)")
def approve_curriculum(curriculum_id: uuid.UUID, body: CurriculumApproveIn, ctx: Ctx = Depends(_cur_approve)):
    return service.approve(ctx, curriculum_id, body)


@router.post("/curricula/{curriculum_id}/archive", response_model=CurriculumDetailOut)
def archive_curriculum(curriculum_id: uuid.UUID, body: VersionIn, ctx: Ctx = Depends(_cur_approve)):
    return service.archive(ctx, curriculum_id, body.row_version)


@router.post("/curricula/{curriculum_id}/new-version", response_model=CurriculumDetailOut,
             status_code=status.HTTP_201_CREATED, summary="Tasdiqlangan rejadan yangi qoralama versiya")
def new_version(curriculum_id: uuid.UUID, ctx: Ctx = Depends(_cur_manage)):
    return service.new_version(ctx, curriculum_id)


@router.post("/curricula/{curriculum_id}/subjects", response_model=CurriculumDetailOut,
             status_code=status.HTTP_201_CREATED)
def add_subject(curriculum_id: uuid.UUID, body: CurriculumSubjectIn, ctx: Ctx = Depends(_cur_manage)):
    return service.add_subject(ctx, curriculum_id, body)


@router.patch("/curricula/{curriculum_id}/subjects/{entry_id}", response_model=CurriculumDetailOut)
def update_subject_entry(curriculum_id: uuid.UUID, entry_id: uuid.UUID, body: CurriculumSubjectUpdateIn,
                         ctx: Ctx = Depends(_cur_manage)):
    return service.update_subject_entry(ctx, curriculum_id, entry_id, body)


@router.delete("/curricula/{curriculum_id}/subjects/{entry_id}", response_model=CurriculumDetailOut)
def remove_subject(curriculum_id: uuid.UUID, entry_id: uuid.UUID, ctx: Ctx = Depends(_cur_manage)):
    return service.remove_subject(ctx, curriculum_id, entry_id)
