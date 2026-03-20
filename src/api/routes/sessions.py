from fastapi import APIRouter, Depends

from api.dependencies import get_session_service, require_auth
from schemas.auth import AuthContext
from schemas.sessions import (
    SessionCreateRequest,
    SessionPhoneUpdateRequest,
    SessionPhoneUpdateResponse,
    SessionResponse,
)
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
