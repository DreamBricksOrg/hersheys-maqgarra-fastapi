from fastapi import APIRouter, Depends

from api.dependencies import get_session_service, get_session_tags_service, require_auth
from schemas.auth import AuthContext
from schemas.sessions import (
    SessionCreateRequest,
    SessionPhoneUpdateRequest,
    SessionPhoneUpdateResponse,
    SessionResponse,
)
from schemas.tags import SessionTagsResponse, SessionWithTagResponse
from services.session_service import SessionService
from services.session_tags_service import SessionTagsService
from services.session_service import SessionService

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    payload: SessionCreateRequest,
    auth: AuthContext = Depends(require_auth),
    service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    return await service.create(payload)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    auth: AuthContext = Depends(require_auth),
    service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    return await service.get_by_id(session_id)


@router.post("/{session_id}/phone", response_model=SessionPhoneUpdateResponse)
async def update_session_phone(
    session_id: str,
    payload: SessionPhoneUpdateRequest,
    auth: AuthContext = Depends(require_auth),
    service: SessionService = Depends(get_session_service),
) -> SessionPhoneUpdateResponse:
    return await service.update_phone(session_id, payload)

@router.get("/{session_id}/tags", response_model=SessionTagsResponse)
async def get_session_tags(
    session_id: str,
    auth: AuthContext = Depends(require_auth),
    service: SessionTagsService = Depends(get_session_tags_service),
) -> SessionTagsResponse:
    return await service.get_tags(session_id)

@router.get("/session/{tag_key}", response_model=SessionWithTagResponse)
async def get_session_with_tags(
    tag_key: str,
    auth: AuthContext = Depends(require_auth),
    service: SessionTagsService = Depends(get_session_tags_service),
) -> SessionWithTagResponse:
    return await service.get_session_with_tags(tag_key)
