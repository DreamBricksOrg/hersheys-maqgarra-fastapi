from motor.motor_asyncio import AsyncIOMotorDatabase


class BarsNameRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.bars_names

    async def find_all_names(self) -> list[str]:
        return [doc["name"].lower() async for doc in self.collection.find({}, {"name": 1})]

    async def exists(self, name: str) -> bool:
        doc = await self.collection.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
        return doc is not None

    async def add_name(self, name: str) -> tuple[dict, bool]:
        """Returns (document, created). created=False if already existed."""
        if await self.exists(name):
            doc = await self.collection.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
            return doc, False
        result = await self.collection.insert_one({"name": name})
        doc = await self.collection.find_one({"_id": result.inserted_id})
        return doc, True
