from fastapi import APIRouter, Depends, Query, Response, status

from api.dependencies import (
    get_session_tags_service,
    get_tag_association_service,
    get_tag_crud_service,
    get_tag_state_service,
    get_tag_usage_service,
    require_auth,
)
from schemas.auth import AuthContext
from schemas.tags import (
    SessionTagsResponse,
    TagActivateRequest,
    TagAssociateRequest,
    TagAssociateResponse,
    TagCreateRequest,
    TagDeactivateRequest,
    TagListResponse,
    TagResponse,
    TagStatusResponse,
    TagUpdateRequest,
    TagUseRequest,
    TagListResponse,
)
from services.session_tags_service import SessionTagsService
from services.tag_association_service import TagAssociationService
from services.tag_crud_service import TagCrudService
from services.tag_state_service import TagStateService
from services.tag_usage_service import TagUsageService

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.post("/associate", response_model=TagAssociateResponse)
async def associate_tags(
    payload: TagAssociateRequest,
    auth: AuthContext = Depends(require_auth),
    service: TagAssociationService = Depends(get_tag_association_service),
) -> TagAssociateResponse:
    return await service.execute(payload.session_id, payload.tags)


@router.post("/use", response_model=TagResponse)
async def use_tag(
    payload: TagUseRequest,
    auth: AuthContext = Depends(require_auth),
    service: TagUsageService = Depends(get_tag_usage_service),
) -> TagResponse:
    return await service.use(payload.tag_key)


@router.get("/key/{tag_key}", response_model=TagStatusResponse)
async def get_tag_state(
    tag_key: str,
    auth: AuthContext = Depends(require_auth),
    service: TagStateService = Depends(get_tag_state_service),
) -> TagStatusResponse:
    return await service.get_state(tag_key)


@router.get("", response_model=TagListResponse)
async def list_tags(
    amount: int,
    auth: AuthContext = Depends(require_auth),
    service: TagStateService = Depends(get_tag_state_service),
) -> TagListResponse:
    tags = await service.list_tags(amount)
    return TagListResponse(tags=tags)


@router.post("/{tag_key}/activate", response_model=TagStatusResponse)
async def activate_tag(
    tag_key: str,
    payload: TagActivateRequest,
    auth: AuthContext = Depends(require_auth),
    service: TagStateService = Depends(get_tag_state_service),
) -> TagStatusResponse:
    return await service.activate(tag_key, payload.reason)


@router.post("/key/{tag_key}/deactivate", response_model=TagStatusResponse)
async def deactivate_tag(
    tag_key: str,
    payload: TagDeactivateRequest,
    auth: AuthContext = Depends(require_auth),
    service: TagStateService = Depends(get_tag_state_service),
) -> TagStatusResponse:
    return await service.deactivate(tag_key, payload.reason)


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    payload: TagCreateRequest,
    auth: AuthContext = Depends(require_auth),
    service: TagCrudService = Depends(get_tag_crud_service),
) -> TagResponse:
    return await service.create(
        tag_key=payload.tag_key,
        delivery_mode=payload.delivery_mode,
        status=payload.status,
        session_id=payload.session_id,
    )


@router.get("", response_model=TagListResponse)
async def list_tags(
    status_value: str | None = Query(default=None, alias="status"),
    session_id: str | None = Query(default=None),
    tag_key: str | None = Query(default=None),
    delivery_mode: str | None = Query(default=None),
    auth: AuthContext = Depends(require_auth),
    service: TagCrudService = Depends(get_tag_crud_service),
) -> TagListResponse:
    return await service.list(
        status=status_value,
        session_id=session_id,
        tag_key=tag_key,
        delivery_mode=delivery_mode,
    )


@router.get("/id/{tag_id}", response_model=TagResponse)
async def get_tag(
    tag_id: str,
    auth: AuthContext = Depends(require_auth),
    service: TagCrudService = Depends(get_tag_crud_service),
) -> TagResponse:
    return await service.get_by_id(tag_id)


@router.patch("/id/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: str,
    payload: TagUpdateRequest,
    auth: AuthContext = Depends(require_auth),
    service: TagCrudService = Depends(get_tag_crud_service),
) -> TagResponse:
    return await service.update(
        tag_id=tag_id,
        status=payload.status,
        session_id=payload.session_id,
        invalid_reason=payload.invalid_reason,
        delivery_mode=payload.delivery_mode,
    )


@router.delete("/id/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: str,
    auth: AuthContext = Depends(require_auth),
    service: TagCrudService = Depends(get_tag_crud_service),
) -> Response:
    await service.delete(tag_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/session/{session_id}", response_model=SessionTagsResponse)
async def get_tags_by_session(
    session_id: str,
    auth: AuthContext = Depends(require_auth),
    service: SessionTagsService = Depends(get_session_tags_service),
) -> SessionTagsResponse:
    return await service.get_tags(session_id)
