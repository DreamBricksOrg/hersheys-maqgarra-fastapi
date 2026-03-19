from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection


class QueueRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection: AsyncIOMotorCollection = db.queue
        self.state_collection: AsyncIOMotorCollection = db.queue_state

    async def create_indexes(self) -> None:
        await self.collection.create_index("session_id")
        await self.collection.create_index("queue_number", unique=True)
        await self.collection.create_index("status")
        await self.collection.create_index([("status", 1), ("queue_number", 1)])
        await self.state_collection.create_index("key", unique=True)

    async def find_last_queue_entry(self) -> dict | None:
        return await self.collection.find_one({}, sort=[("queue_number", -1)])

    async def get_next_queue_number(self) -> int:
        last = await self.find_last_queue_entry()
        return (last["queue_number"] + 1) if last else 1

    async def create_entry(
        self,
        session_id: str,
        queue_number: int,
        total_plays: int,
    ) -> dict:
        now = datetime.now(timezone.utc)
        payload = {
            "session_id": ObjectId(session_id),
            "queue_number": queue_number,
            "status": "waiting",
            "total_plays": total_plays,
            "remaining_plays": total_plays,
            "created_at": now,
            "called_at": None,
            "played_at": None,
            "completed_at": None,
            "requeued_from": None,
        }
        result = await self.collection.insert_one(payload)
        return await self.collection.find_one({"_id": result.inserted_id})

    async def find_by_id(self, player_id: str) -> dict | None:
        return await self.collection.find_one({"_id": ObjectId(player_id)})

    async def count_people_ahead(self, queue_number: int) -> int:
        current = await self.get_current_queue_number()
        effective_current = current or 0
        return await self.collection.count_documents(
            {
                "queue_number": {"$gte": effective_current + 1, "$lt": queue_number},
                "status": {"$in": ["waiting", "requeued", "called"]},
            }
        )

    async def get_next_waiting_entry(self) -> dict | None:
        return await self.collection.find_one(
            {"status": {"$in": ["waiting", "requeued"]}},
            sort=[("queue_number", 1)],
        )

    async def mark_called(self, player_id: str) -> dict | None:
        now = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"_id": ObjectId(player_id)},
            {"$set": {"status": "called", "called_at": now}},
        )
        return await self.find_by_id(player_id)

    async def mark_playing(self, player_id: str) -> dict | None:
        now = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"_id": ObjectId(player_id)},
            {"$set": {"status": "playing", "played_at": now}},
        )
        return await self.find_by_id(player_id)

    async def mark_done(self, player_id: str, remaining_plays: int) -> dict | None:
        now = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"_id": ObjectId(player_id)},
            {
                "$set": {
                    "status": "done",
                    "completed_at": now,
                    "remaining_plays": remaining_plays,
                }
            },
        )
        return await self.find_by_id(player_id)

    async def mark_skipped(self, player_id: str) -> dict | None:
        await self.collection.update_one(
            {"_id": ObjectId(player_id)},
            {"$set": {"status": "skipped"}},
        )
        return await self.find_by_id(player_id)

    async def requeue(self, player_id: str, new_queue_number: int, old_queue_number: int) -> dict | None:
        await self.collection.update_one(
            {"_id": ObjectId(player_id)},
            {
                "$set": {
                    "queue_number": new_queue_number,
                    "status": "requeued",
                    "requeued_from": old_queue_number,
                    "called_at": None,
                    "played_at": None,
                }
            },
        )
        return await self.find_by_id(player_id)

    async def list_active_queue(self) -> list[dict]:
        cursor = self.collection.find(
            {"status": {"$in": ["waiting", "requeued", "called", "playing"]}}
        ).sort("queue_number", 1)
        return await cursor.to_list(length=None)

    async def list_waiting_queue(self) -> list[dict]:
        cursor = self.collection.find(
            {"status": {"$in": ["waiting", "requeued", "called"]}}
        ).sort("queue_number", 1)
        return await cursor.to_list(length=None)

    async def set_current_queue_number(self, queue_number: int, player_id: str, status: str) -> None:
        await self.state_collection.update_one(
            {"key": "current"},
            {
                "$set": {
                    "key": "current",
                    "queue_number": queue_number,
                    "player_id": ObjectId(player_id),
                    "status": status,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )

    async def clear_current_queue_number(self) -> None:
        await self.state_collection.update_one(
            {"key": "current"},
            {
                "$set": {
                    "key": "current",
                    "queue_number": None,
                    "player_id": None,
                    "status": None,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )

    async def get_current_state(self) -> dict | None:
        return await self.state_collection.find_one({"key": "current"})

    async def get_current_queue_number(self) -> int | None:
        state = await self.get_current_state()
        if not state:
            return None
        return state.get("queue_number")

    async def decrement_remaining_play(self, player_id: str) -> int:
        doc = await self.find_by_id(player_id)
        remaining = max((doc or {}).get("remaining_plays", 1) - 1, 0)
        await self.collection.update_one(
            {"_id": ObjectId(player_id)},
            {"$set": {"remaining_plays": remaining}},
        )
        return remaining

    async def touch_status(self, player_id: str, status: str) -> dict | None:
        await self.collection.update_one(
            {"_id": ObjectId(player_id)},
            {"$set": {"status": status}},
        )
        return await self.find_by_id(player_id)