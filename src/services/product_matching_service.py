from motor.motor_asyncio import AsyncIOMotorDatabase
from services.redis_service import RedisService

class ProductMatchingService:
    def __init__(self, db: AsyncIOMotorDatabase, redisService: RedisService):
        self.collection = db.bars_names
        self.redisService = redisService

    async def match_products(self, produtos: list[dict]) -> tuple[list[dict], int]:
        known_names = self.redisService.get_list("bars_names")
        if known_names is None:
            known_names = [doc["name"].lower() async for doc in self.collection.find({}, {"name": 1})]
            self.redisService.add_to_redis_set("bars_names", known_names)
        matched_items: list[dict] = []
        total_bars = 0

        for produto in produtos:
            name = str(produto.get("nome", "")).strip()
            quantity_raw = produto.get("quantidade", 0)
            try:
                quantity = int(float(quantity_raw))
            except (ValueError, TypeError):
                quantity = 0

            lowered = name.lower()
            matched = lowered in known_names or "hers" in lowered or "hershey" in lowered
            if matched:
                total_bars += quantity

            matched_items.append({
                "name": name,
                "quantity": quantity,
                "matched": matched,
            })

        return matched_items, total_bars
