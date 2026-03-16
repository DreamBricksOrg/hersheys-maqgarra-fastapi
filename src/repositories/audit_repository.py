from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase


class AuditRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.audit_events

    async def create(self, event: str, payload: dict) -> None:
        await self.collection.insert_one(
            {"event": event, "payload": payload, "created_at": datetime.now(timezone.utc)}
        )
