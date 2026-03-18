from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase


class ApiKeyRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.api_keys

    async def find_active(self, api_key: str) -> dict | None:
        return await self.collection.find_one({"api_key": api_key, "is_active": True})

    async def touch(self, api_key: str) -> None:
        await self.collection.update_one(
            {"api_key": api_key},
            {"$set": {"last_used_at": datetime.now(timezone.utc)}},
        )
