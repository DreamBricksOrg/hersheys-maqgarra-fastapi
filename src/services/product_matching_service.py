from repositories.bars_name_repository import BarsNameRepository


class ProductMatchingService:
    def __init__(self, bars_name_repository: BarsNameRepository):
        self.bars_name_repository = bars_name_repository

    async def match_products(self, produtos: list[dict]) -> tuple[list[dict], int]:
        known_names = await self.bars_name_repository.find_all_names()
        matched_items: list[dict] = []
        total_bars = 0

        for produto in produtos:
            name = str(produto.get("nome", "")).strip()
            quantity_raw = produto.get("quantidade", 0)
            try:
                quantity = int(float(str(quantity_raw)))
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

    async def learn(self, name: str) -> tuple[dict, bool]:
        """Adiciona nome ao banco se não existir. Retorna (doc, created)."""
        return await self.bars_name_repository.add_name(name)
