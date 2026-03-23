from fastapi import APIRouter, Depends

from api.dependencies import get_observability_service
from services.observability_service import ObservabilityService


router = APIRouter()


@router.get("/alive")
async def alive(
    observability_service: ObservabilityService = Depends(get_observability_service),
):
    await observability_service.emit(
        "alive-called",
        {
            "route": "/alive",
            "status": "ok"
        },
        tags=["health", "alive", "status"],
    )
    return {"status": "ok"}
