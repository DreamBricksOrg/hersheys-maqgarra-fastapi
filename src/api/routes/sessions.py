from fastapi import APIRouter, Depends, status

from api.dependencies import get_session_service, get_session_tags_service, require_auth
from schemas.auth import AuthContext
from schemas.sessions import SessionCreateRequest, SessionResponse
from schemas.tags import SessionTagsResponse
from services.session_service import SessionService
from services.session_tags_service import SessionTagsService

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
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


@router.get("/{session_id}/tags", response_model=SessionTagsResponse)
async def get_session_tags(
    session_id: str,
    auth: AuthContext = Depends(require_auth),
    service: SessionTagsService = Depends(get_session_tags_service),
) -> SessionTagsResponse:
    return await service.get_tags(session_id)
