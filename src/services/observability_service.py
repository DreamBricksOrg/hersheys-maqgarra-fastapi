import logging
from typing import Any

from repositories.audit_repository import AuditRepository

logger = logging.getLogger(__name__)


class ObservabilityService:
    def __init__(self, audit_repository: AuditRepository):
        self.audit_repository = audit_repository

    async def emit(self, event: str, payload: dict[str, Any]) -> None:
        logger.info("event=%s payload=%s", event, payload)
        await self.audit_repository.create(event, payload)
