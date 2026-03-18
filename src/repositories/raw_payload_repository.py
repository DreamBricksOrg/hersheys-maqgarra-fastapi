from copy import deepcopy
from motor.motor_asyncio import AsyncIOMotorDatabase


class RawPayloadRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.raw_payload

    async def create(self, payload: dict) -> str:
        payload_to_insert = deepcopy(payload)
        result = await self.collection.insert_one(payload_to_insert)
        return str(result.inserted_id)
