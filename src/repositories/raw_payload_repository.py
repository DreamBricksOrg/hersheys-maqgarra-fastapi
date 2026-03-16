from motor.motor_asyncio import AsyncIOMotorDatabase


class RawPayloadRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.raw_payload

    async def create(self, payload: dict) -> str:
        result = await self.collection.insert_one(payload)
        return str(result.inserted_id)
