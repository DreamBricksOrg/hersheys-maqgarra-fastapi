from fastapi import APIRouter, Depends

from api.dependencies import get_queue_intake_service, get_queue_service, require_auth
from core.config import settings
from schemas.auth import AuthContext
from schemas.queue import (
    QueueCompleteRequest,
    QueueCompleteResponse,
    QueueCurrentResponse,
    QueueIntakeRequest,
    QueueIntakeResponse,
    QueueJoinRequest,
    QueueJoinResponse,
    QueueListResponse,
    QueueMobileViewResponse,
    QueueNextResponse,
    QueueSkipRequest,
    QueueSkipResponse,
    QueueStateResponse,
    QueueValidateRequest,
    QueueValidateResponse,
)
from services.queue_intake_service import QueueIntakeService
from services.queue_service import QueueService

router = APIRouter(prefix="/api/queue", tags=["queue"])


@router.post("/intake", response_model=QueueIntakeResponse)
async def intake_queue_from_receipt(
    payload: QueueIntakeRequest,
    auth: AuthContext = Depends(require_auth),
    service: QueueIntakeService = Depends(get_queue_intake_service),
) -> QueueIntakeResponse:
    return await service.execute(
        receipt_id=payload.receipt_id,
        total_plays=payload.total_plays,
        phone=payload.phone,
    )


@router.post("/join", response_model=QueueJoinResponse)
async def join_queue(
    payload: QueueJoinRequest,
    auth: AuthContext = Depends(require_auth),
    service: QueueService = Depends(get_queue_service),
) -> QueueJoinResponse:
    return await service.join(payload.session_id, payload.total_plays)


@router.get("/current", response_model=QueueCurrentResponse)
async def get_current_queue(
    auth: AuthContext = Depends(require_auth),
    service: QueueService = Depends(get_queue_service),
) -> QueueCurrentResponse:
    return await service.get_current()


@router.get("/active", response_model=QueueListResponse)
async def list_active_queue(
    auth: AuthContext = Depends(require_auth),
    service: QueueService = Depends(get_queue_service),
) -> QueueListResponse:
    return await service.list_active()


@router.get("/mobile/{player_id}", response_model=QueueMobileViewResponse)
async def get_mobile_queue_view(
    player_id: str,
    auth: AuthContext = Depends(require_auth),
    service: QueueService = Depends(get_queue_service),
) -> QueueMobileViewResponse:
    data = await service.get_mobile_view(player_id, settings.BASE_URL)
    return QueueMobileViewResponse(**data)


@router.get("/{player_id}", response_model=QueueStateResponse)
async def get_queue_state(
    player_id: str,
    auth: AuthContext = Depends(require_auth),
    service: QueueService = Depends(get_queue_service),
) -> QueueStateResponse:
    return await service.get_state(player_id)


@router.post("/next", response_model=QueueNextResponse)
async def call_next_in_queue(
    auth: AuthContext = Depends(require_auth),
    service: QueueService = Depends(get_queue_service),
) -> QueueNextResponse:
    return await service.next()


@router.post("/validate", response_model=QueueValidateResponse)
async def validate_queue_player(
    payload: QueueValidateRequest,
    auth: AuthContext = Depends(require_auth),
    service: QueueService = Depends(get_queue_service),
) -> QueueValidateResponse:
    return await service.validate_for_play(payload.player_id)


@router.post("/complete", response_model=QueueCompleteResponse)
async def complete_queue_player(
    payload: QueueCompleteRequest,
    auth: AuthContext = Depends(require_auth),
    service: QueueService = Depends(get_queue_service),
) -> QueueCompleteResponse:
    return await service.complete(payload.player_id)


@router.post("/skip", response_model=QueueSkipResponse)
async def skip_current_queue_player(
    payload: QueueSkipRequest,
    auth: AuthContext = Depends(require_auth),
    service: QueueService = Depends(get_queue_service),
) -> QueueSkipResponse:
    return await service.skip_current(payload.reason)
