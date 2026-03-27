from fastapi import APIRouter, Depends
from typing import Dict, Any

from api.dependencies import get_audit_repository, require_auth
from schemas.auth import AuthContext
from services.stats_service import StatsService
from repositories.audit_repository import AuditRepository

router = APIRouter(prefix="/api/stats", tags=["stats"])

def get_stats_service(
    audit_repository: AuditRepository = Depends(get_audit_repository)
) -> StatsService:
    return StatsService(audit_repository)

@router.get("/daily", response_model=Dict[str, Any])
async def get_daily_stats(
    auth: AuthContext = Depends(require_auth),
    service: StatsService = Depends(get_stats_service),
):
    return await service.get_today_stats()
