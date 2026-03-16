from fastapi import APIRouter, Depends

from api.dependencies import get_tag_association_service, get_tag_state_service, require_auth
from schemas.auth import AuthContext
from schemas.tags import TagAssociateRequest, TagAssociateResponse, TagDeactivateRequest, TagStatusResponse
from services.tag_association_service import TagAssociationService
from services.tag_state_service import TagStateService

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.post("/associate", response_model=TagAssociateResponse)
async def associate_tags(
    payload: TagAssociateRequest,
    auth: AuthContext = Depends(require_auth),
    service: TagAssociationService = Depends(get_tag_association_service),
) -> TagAssociateResponse:
    return await service.execute(payload.session_id, payload.receipt_ids, payload.tags)


@router.get("/{tag_key}", response_model=TagStatusResponse)
async def get_tag_state(
    tag_key: str,
    auth: AuthContext = Depends(require_auth),
    service: TagStateService = Depends(get_tag_state_service),
) -> TagStatusResponse:
    return await service.get_state(tag_key)


@router.post("/{tag_key}/deactivate", response_model=TagStatusResponse)
async def deactivate_tag(
    tag_key: str,
    payload: TagDeactivateRequest,
    auth: AuthContext = Depends(require_auth),
    service: TagStateService = Depends(get_tag_state_service),
) -> TagStatusResponse:
    return await service.deactivate(tag_key)
