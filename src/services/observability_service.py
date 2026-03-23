import logging
from datetime import datetime
from typing import Any
from bson import ObjectId

from repositories.audit_repository import AuditRepository

logger = logging.getLogger(__name__)


def to_logcenter_safe(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): to_logcenter_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_logcenter_safe(v) for v in value]
    if isinstance(value, tuple):
        return [to_logcenter_safe(v) for v in value]
    return value


class ObservabilityService:
    def __init__(self, audit_repository: AuditRepository, log_sender: Any | None = None):
        self.audit_repository = audit_repository
        self.log_sender = log_sender

    async def emit(
        self,
        event: str,
        payload: dict[str, Any],
        *,
        status: str = "ok",
        level: str = "INFO",
        tags: list[str] | None = None,
        request_id: str | None = None,
    ) -> None:
        logger.info("event=%s payload=%s", event, payload)

        await self.audit_repository.create(event, payload)

        if not self.log_sender:
            return

        try:
            safe_payload = to_logcenter_safe(payload)

            await self.log_sender.send(
                level=level,
                message=event,
                status=status,
                tags=tags or ["domain-event", event],
                data=safe_payload,
                request_id=request_id or safe_payload.get("request_id"),
                spool_on_fail=True,
            )
        except Exception:
            logger.exception("failed to send event=%s to logcenter", event)