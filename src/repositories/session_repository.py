from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


class SessionRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.sessions

    async def create(self, receipt_ids: list[str], tag_ids: list[str] | None = None) -> dict:
        payload = {
            "receipt_ids": receipt_ids,
            "tag_ids": tag_ids or [],
            "created_at": datetime.now(timezone.utc),
            "finished_at": None,
        }
        result = await self.collection.insert_one(payload)
        payload["_id"] = result.inserted_id
        return payload

    async def find_by_id(self, session_id: str) -> dict | None:
        return await self.collection.find_one({"_id": ObjectId(session_id)})

    async def attach_tags(self, session_id: str, tag_ids: list[str]) -> dict | None:
        await self.collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"tag_ids": tag_ids, "finished_at": datetime.now(timezone.utc)}},
        )
        return await self.find_by_id(session_id)
