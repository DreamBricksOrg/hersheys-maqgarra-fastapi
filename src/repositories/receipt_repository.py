from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


class ReceiptRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.receipts

    async def create(self, payload: dict) -> dict:
        result = await self.collection.insert_one(payload)
        payload["_id"] = result.inserted_id
        return payload

    async def find_by_id(self, receipt_id: str) -> dict | None:
        return await self.collection.find_one({"_id": ObjectId(receipt_id)})

    async def find_by_key(self, receipt_key: str) -> dict | None:
        return await self.collection.find_one({"receipt_key": receipt_key})

    async def update_by_id(self, receipt_id: str, update: dict) -> dict | None:
        await self.collection.update_one({"_id": ObjectId(receipt_id)}, {"$set": update})
        return await self.find_by_id(receipt_id)

    async def mark_used_many(self, receipt_ids: list[str]) -> None:
        object_ids = [ObjectId(item) for item in receipt_ids]
        await self.collection.update_many({"_id": {"$in": object_ids}}, {"$set": {"status": "used"}})
