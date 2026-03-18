from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase


class TagRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.tags

    async def find_by_key(self, tag_key: str) -> dict | None:
        return await self.collection.find_one({"tag_key": tag_key})

    async def make_available(self, tag_key: str) -> dict | None:
        now = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"tag_key": tag_key},
            {"$set": {"status": "available", "last_updated_at": now}},
            upsert=False,
        )
        return await self.find_by_key(tag_key)

    async def mark_used_many(self, tags: list[str]) -> list[dict]:
        updated: list[dict] = []
        now = datetime.now(timezone.utc)

        for tag_key in tags:
            await self.collection.update_one(
                {"tag_key": tag_key},
                {"$set": {"status": "used", "last_updated_at": now}},
                upsert=False,
            )
            doc = await self.find_by_key(tag_key)
            if doc:
                updated.append(doc)

        return updated

    async def deactivate(self, tag_key: str) -> dict | None:
        now = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"tag_key": tag_key},
            {"$set": {"status": "invalid", "last_updated_at": now}},
        )
        return await self.find_by_key(tag_key)

    async def find_by_status(self, limit: int) -> list[dict]:
        cursor = self.collection.find({"status": {"$in": ["invalid", "available"]}}).limit(limit)
        return await cursor.to_list(length=limit)
