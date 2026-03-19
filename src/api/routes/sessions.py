from fastapi import APIRouter, Depends

from api.dependencies import get_session_tags_service, require_auth
from schemas.auth import AuthContext
from schemas.tags import SessionTagsResponse
from services.session_tags_service import SessionTagsService

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("/{session_id}/tags", response_model=SessionTagsResponse)
async def get_session_tags(
    session_id: str,
    auth: AuthContext = Depends(require_auth),
    service: SessionTagsService = Depends(get_session_tags_service),
) -> SessionTagsResponse:
    return await service.get_tags(session_id)