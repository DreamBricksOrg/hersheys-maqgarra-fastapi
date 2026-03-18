from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


class TagRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.tags

    async def find_by_id(self, tag_id: str) -> dict | None:
        return await self.collection.find_one({"_id": ObjectId(tag_id)})

    async def find_by_key(self, tag_key: str) -> dict | None:
        return await self.collection.find_one({"tag_key": tag_key})

    async def find_by_session_id(self, session_id: str) -> list[dict]:
        cursor = self.collection.find({"session_id": ObjectId(session_id)}).sort("tag_key", 1)
        return await cursor.to_list(length=None)

    async def list_tags(
        self,
        status: str | None = None,
        session_id: str | None = None,
        tag_key: str | None = None,
    ) -> list[dict]:
        query: dict = {}

        if status:
            query["status"] = status
        if session_id:
            query["session_id"] = ObjectId(session_id)
        if tag_key:
            query["tag_key"] = tag_key

        cursor = self.collection.find(query).sort("tag_key", 1)
        return await cursor.to_list(length=None)

    async def create(
        self,
        tag_key: str,
        status: str = "available",
        session_id: str | None = None,
        invalid_reason: str | None = None,
    ) -> dict:
        now = datetime.now(timezone.utc)

        payload = {
            "tag_key": tag_key,
            "status": status,
            "session_id": ObjectId(session_id) if session_id else None,
            "last_updated_at": now,
            "used_at": None,
            "invalid_reason": invalid_reason,
        }

        result = await self.collection.insert_one(payload)
        return await self.collection.find_one({"_id": result.inserted_id})

    async def update(
        self,
        tag_id: str,
        status: str | None = None,
        session_id: str | None = None,
        invalid_reason: str | None = None,
        clear_session_id: bool = False,
    ) -> dict | None:
        update_data: dict = {
            "last_updated_at": datetime.now(timezone.utc),
        }

        if status is not None:
            update_data["status"] = status

        if clear_session_id:
            update_data["session_id"] = None
        elif session_id is not None:
            update_data["session_id"] = ObjectId(session_id)

        if invalid_reason is not None:
            update_data["invalid_reason"] = invalid_reason

        await self.collection.update_one(
            {"_id": ObjectId(tag_id)},
            {"$set": update_data},
        )
        return await self.find_by_id(tag_id)

    async def delete(self, tag_id: str) -> bool:
        result = await self.collection.delete_one({"_id": ObjectId(tag_id)})
        return result.deleted_count > 0

    async def associate_many(self, session_id: str, tag_keys: list[str]) -> list[dict]:
        updated: list[dict] = []
        now = datetime.now(timezone.utc)

        for tag_key in tag_keys:
            await self.collection.update_one(
                {"tag_key": tag_key, "status": "available"},
                {
                    "$set": {
                        "status": "valid",
                        "session_id": ObjectId(session_id),
                        "last_updated_at": now,
                        "invalid_reason": None,
                    }
                },
            )
            doc = await self.find_by_key(tag_key)
            if doc:
                updated.append(doc)

        return updated

    async def mark_used(self, tag_key: str) -> dict | None:
        now = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"tag_key": tag_key, "status": "valid"},
            {
                "$set": {
                    "status": "used",
                    "used_at": now,
                    "last_updated_at": now,
                }
            },
        )
        return await self.find_by_key(tag_key)

    async def invalidate(self, tag_key: str, reason: str = "timeout") -> dict | None:
        now = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"tag_key": tag_key},
            {
                "$set": {
                    "status": "invalid",
                    "invalid_reason": reason,
                    "last_updated_at": now,
                }
            },
        )
        return await self.find_by_key(tag_key)
