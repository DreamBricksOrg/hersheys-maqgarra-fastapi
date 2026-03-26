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

    async def attach_session_id(self, receipt_id: str, session_id: str) -> dict | None:
        await self.collection.update_one(
            {"_id": ObjectId(receipt_id)},
            {"$set": {"session_id": ObjectId(session_id)}},
        )
        return await self.find_by_id(receipt_id)

    async def find_latest_by_receipt_key(self, receipt_key: str) -> dict | None:
        return await self.collection.find_one(
            {"receipt_key": receipt_key},
            sort=[("created_at", -1)],
        )

    async def find_by_session_id(self, session_id: str) -> list[dict]:
        return (
            await self.collection.find(
                {"session_id": session_id}
            ).to_list(length=None)
        )

    async def mark_receipts_as_replaced_for_session(self, session_id: str) -> int:
        receipts = await self.find_by_session_id(session_id)
        modified = 0

        for receipt in receipts:
            receipt_id = receipt["_id"]
            receipt_key = receipt.get("receipt_key")

            if not receipt_key:
                continue

            replaced_key = receipt_key if receipt_key.endswith("-D") else f"{receipt_key}-D"

            result = await self.collection.update_one(
                {"_id": receipt_id},
                {
                    "$set": {
                        "receipt_key": replaced_key,
                        "replaced_original_receipt_key": receipt_key,
                        "is_replaced": True,
                    }
                },
            )
            modified += result.modified_count

        return modified
