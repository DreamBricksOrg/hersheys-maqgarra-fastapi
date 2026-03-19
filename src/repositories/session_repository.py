from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


class SessionRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.sessions

    async def create(
        self,
        receipt_ids: list[str],
        player_id: str,
        tag_ids: list[str] | None = None,
        phone: str | None = None,
    ) -> dict:
        now = datetime.now(timezone.utc)

        payload = {
            "receipt_ids": [ObjectId(item) for item in receipt_ids],
            "tag_ids": [ObjectId(item) for item in (tag_ids or [])],
            "player_id": ObjectId(player_id),
            "queue_entry_id": None,
            "phone": phone,
            "status": "created",
            "created_at": now,
            "finished_at": None,
            "last_updated_at": now,
        }

        result = await self.collection.insert_one(payload)
        return await self.collection.find_one({"_id": result.inserted_id})

    async def find_by_id(self, session_id: str) -> dict | None:
        return await self.collection.find_one({"_id": ObjectId(session_id)})

    async def find_by_receipt_id(self, receipt_id: str) -> dict | None:
        return await self.collection.find_one({"receipt_ids": ObjectId(receipt_id)})

    async def find_by_player_id(self, player_id: str) -> dict | None:
        return await self.collection.find_one({"player_id": ObjectId(player_id)})

    async def attach_tags(self, session_id: str, tag_ids: list[str]) -> dict | None:
        await self.collection.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$addToSet": {
                    "tag_ids": {"$each": [ObjectId(item) for item in tag_ids]}
                },
                "$set": {
                    "last_updated_at": datetime.now(timezone.utc),
                },
            },
        )
        return await self.find_by_id(session_id)

    async def set_player_id(self, session_id: str, player_id: str) -> dict | None:
        await self.collection.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    "player_id": ObjectId(player_id),
                    "last_updated_at": datetime.now(timezone.utc),
                },
            },
        )
        return await self.find_by_id(session_id)

    async def attach_player_id(self, session_id: str, player_id: str) -> dict | None:
        return await self.set_player_id(session_id, player_id)

    async def attach_receipt_id(self, session_id: str, receipt_id: str) -> dict | None:
        await self.collection.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$addToSet": {"receipt_ids": ObjectId(receipt_id)},
                "$set": {"last_updated_at": datetime.now(timezone.utc)},
            },
        )
        return await self.find_by_id(session_id)

    async def set_queue_entry_id(self, session_id: str, queue_entry_id: str) -> dict | None:
        await self.collection.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    "queue_entry_id": ObjectId(queue_entry_id),
                    "last_updated_at": datetime.now(timezone.utc),
                },
            },
        )
        return await self.find_by_id(session_id)

    async def update_status(self, session_id: str, status: str) -> dict | None:
        now = datetime.now(timezone.utc)
        update_data = {
            "status": status,
            "last_updated_at": now,
        }

        if status == "finished":
            update_data["finished_at"] = now

        await self.collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": update_data},
        )
        return await self.find_by_id(session_id)
