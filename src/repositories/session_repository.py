from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


class SessionRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.sessions

    async def create(self, receipt_ids: list[str], tag_ids: list[str] | None = None) -> dict:
        payload = {
            "receipt_ids": [ObjectId(item) for item in receipt_ids],
            "tag_ids": [ObjectId(item) for item in (tag_ids or [])],
            "player_ids": [],
            "phone": None,
            "created_at": datetime.now(timezone.utc),
            "finished_at": None,
            "last_updated_at": None,
        }
        result = await self.collection.insert_one(payload)
        return await self.collection.find_one({"_id": result.inserted_id})

    async def find_by_id(self, session_id: str) -> dict | None:
        return await self.collection.find_one({"_id": ObjectId(session_id)})

    async def find_by_receipt_id(self, receipt_id: str) -> dict | None:
        return await self.collection.find_one({"receipt_ids": ObjectId(receipt_id)})

    async def attach_tags(self, session_id: str, tag_ids: list[str]) -> dict | None:
        await self.collection.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$addToSet": {
                    "tag_ids": {
                        "$each": [ObjectId(item) for item in tag_ids]
                    }
                },
                "$set": {
                    "finished_at": datetime.now(timezone.utc),
                    "last_updated_at": datetime.now(timezone.utc),
                },
            },
        )
        return await self.find_by_id(session_id)

    async def attach_player_id(self, session_id: str, player_id: str) -> dict | None:
        await self.collection.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$addToSet": {"player_ids": ObjectId(player_id)},
                "$set": {"last_updated_at": datetime.now(timezone.utc)},
            },
        )
        return await self.find_by_id(session_id)

    async def attach_receipt_id(self, session_id: str, receipt_id: str) -> dict | None:
        await self.collection.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$addToSet": {"receipt_ids": ObjectId(receipt_id)},
                "$set": {"last_updated_at": datetime.now(timezone.utc)},
            },
        )
        return await self.find_by_id(session_id)
