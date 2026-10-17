import uuid

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import Ctx, require
from app.modules.groups import service
from app.modules.groups.schemas import (
    GroupBulkIn,
    GroupIn,
    GroupOut,
    GroupUpdateIn,
    StreamIn,
    StreamOut,
    StreamUpdateIn,
)

router = APIRouter(prefix="/years/{year_id}", tags=["Akademik guruhlar va oqimlar"])
_view = require("groups.view")
_manage = require("groups.manage", university_wide=True)


@router.get("/groups", response_model=list[GroupOut], summary="O‘quv yili guruhlari")
def list_groups(year_id: uuid.UUID, q: str | None = Query(None, max_length=50), curriculum_id: uuid.UUID | None = None,
                course: int | None = Query(None, ge=1, le=6), needs_review: bool | None = None,
                ctx: Ctx = Depends(_view)):
    return service.list_groups(ctx, year_id, q, curriculum_id, course, needs_review)


@router.post("/groups", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(year_id: uuid.UUID, body: GroupIn, ctx: Ctx = Depends(_manage)):
    return service.create_group(ctx, year_id, body)


@router.patch("/groups", response_model=list[GroupOut], summary="Kontingentni ommaviy yangilash")
def bulk_update(year_id: uuid.UUID, body: GroupBulkIn, ctx: Ctx = Depends(_manage)):
    return service.bulk_update_counts(ctx, year_id, body.items)


@router.patch("/groups/{group_id}", response_model=GroupOut)
def update_group(year_id: uuid.UUID, group_id: uuid.UUID, body: GroupUpdateIn, ctx: Ctx = Depends(_manage)):
    return service.update_group(ctx, year_id, group_id, body)


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(year_id: uuid.UUID, group_id: uuid.UUID, ctx: Ctx = Depends(_manage)):
    service.delete_group(ctx, year_id, group_id)


@router.get("/streams", response_model=list[StreamOut], summary="Oqimlar")
def list_streams(year_id: uuid.UUID, subject_id: uuid.UUID | None = None, ctx: Ctx = Depends(_view)):
    return service.list_streams(ctx, year_id, subject_id)


@router.post("/streams", response_model=StreamOut, status_code=status.HTTP_201_CREATED)
def create_stream(year_id: uuid.UUID, body: StreamIn, ctx: Ctx = Depends(_manage)):
    return service.create_stream(ctx, year_id, body)


@router.patch("/streams/{stream_id}", response_model=StreamOut)
def update_stream(year_id: uuid.UUID, stream_id: uuid.UUID, body: StreamUpdateIn, ctx: Ctx = Depends(_manage)):
    return service.update_stream(ctx, year_id, stream_id, body)


@router.delete("/streams/{stream_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stream(year_id: uuid.UUID, stream_id: uuid.UUID, ctx: Ctx = Depends(_manage)):
    service.delete_stream(ctx, year_id, stream_id)
