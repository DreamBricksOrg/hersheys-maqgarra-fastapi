from fastapi import APIRouter, Body, Depends, Query

from api.dependencies import get_queue_intake_service, get_queue_service, require_auth
from schemas.auth import AuthContext
from schemas.queue import (
    QueueCompleteResponse,
    QueueCurrentResponse,
    QueueIntakeResponse,
    QueueJoinRequest,
    QueueJoinResponse,
    QueueListResponse,
    QueueMobileViewResponse,
    QueueNextResponse,
    QueueSkipResponse,
    QueueStateResponse,
    QueueValidateResponse,
    QueueRequeueResponse,
    QueuePreferentialResponse,
)
from services.queue_intake_service import QueueIntakeService
from services.queue_service import QueueService

router = APIRouter(prefix="/api/queue", tags=["queue"])


@router.post("/intake", response_model=QueueIntakeResponse)
async def queue_intake(
    receipt_id: str,
    total_plays: int = Query(default=1, ge=1, le=20),
    phone: str | None = None,
    auth: AuthContext = Depends(require_auth),
    service: QueueIntakeService = Depends(get_queue_intake_service),
) -> QueueIntakeResponse:
    return await service.execute(
        receipt_id=receipt_id,
        total_plays=total_plays,
        phone=phone,
    )


@router.post("/join", response_model=QueueJoinResponse)
async def join_queue(
    payload: QueueJoinRequest,
    auth: AuthContext = Depends(require_auth),
    service: QueueService = Depends(get_queue_service),
) -> QueueJoinResponse:
    return await service.join(
        session_id=payload.session_id,
        total_plays=payload.total_plays,
    )


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
async def get_mobile_view(
    player_id: str,
    auth: AuthContext = Depends(require_auth),
    service: QueueService = Depends(get_queue_service),
) -> QueueMobileViewResponse:
    return await service.get_mobile_view(player_id=player_id)


@router.get("/{player_id}", response_model=QueueStateResponse)
async def get_queue_state(
    player_id: str,
    auth: AuthContext = Depends(require_auth),
    service: QueueService = Depends(get_queue_service),
) -> QueueStateResponse:
    return await service.get_state(player_id)


@router.post("/next", response_model=QueueNextResponse)
async def next_queue_player(
    auth: AuthContext = Depends(require_auth),
    service: QueueService = Depends(get_queue_service),
) -> QueueNextResponse:
    return await service.next()


@router.post("/validate", response_model=QueueValidateResponse)
async def validate_queue_player(
    player_id: str,
    auth: AuthContext = Depends(require_auth),
    service: QueueService = Depends(get_queue_service),
) -> QueueValidateResponse:
    return await service.validate_for_play(player_id)


@router.post("/{player_id}/preferential", response_model=QueuePreferentialResponse)
async def mark_preferential(
    player_id: str,
    auth: AuthContext = Depends(require_auth),
    service: QueueService = Depends(get_queue_service),
) -> QueuePreferentialResponse:
    return await service.mark_preferential(player_id)


@router.post("/play")
async def play_queue_turn(
    player_id: str = Body(..., embed=True),
    tag_key: str = Body(..., embed=True),
    auth: AuthContext = Depends(require_auth),
    service: QueueService = Depends(get_queue_service),
) -> dict:
    return await service.play(
        player_id=player_id,
        tag_key=tag_key,
    )


@router.post("/complete", response_model=QueueCompleteResponse)
async def complete_queue_player(
    player_id: str,
    auth: AuthContext = Depends(require_auth),
    service: QueueService = Depends(get_queue_service),
) -> QueueCompleteResponse:
    return await service.complete(player_id)


@router.post("/skip", response_model=QueueSkipResponse)
async def skip_current_player(
    reason: str | None = None,
    auth: AuthContext = Depends(require_auth),
    service: QueueService = Depends(get_queue_service),
) -> QueueSkipResponse:
    return await service.skip_current(reason=reason)

@router.post("/requeue", response_model=QueueRequeueResponse)
async def requeue_player(
    player_id: str,
    auth: AuthContext = Depends(require_auth),
    service: QueueService = Depends(get_queue_service),
) -> QueueRequeueResponse:
    return await service.requeue(player_id)
