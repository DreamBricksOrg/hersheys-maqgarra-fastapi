from repositories.receipt_repository import ReceiptRepository
from schemas.receipts import ReceiptResponse, ReceiptItemResponse
from services.observability_service import ObservabilityService
from core.exceptions import AppError


class ReceiptOverrideService:
    def __init__(self, receipt_repository: ReceiptRepository, observability_service: ObservabilityService):
        self.receipt_repository = receipt_repository
        self.observability_service = observability_service

    async def execute(self, receipt_id: str, final_bars: int, reason: str | None) -> ReceiptResponse:
        receipt = await self.receipt_repository.find_by_id(receipt_id)
        if not receipt:
            raise AppError("Nota não encontrada", "receipt_not_found", 404)

        updated = await self.receipt_repository.update_by_id(
            receipt_id,
            {"final_bars": final_bars, "override_reason": reason, "status": "valid"},
        )
        await self.observability_service.emit("receipt-override", {"receipt_id": receipt_id, "final_bars": final_bars, "reason": reason})
        return ReceiptResponse(
            receipt_id=str(updated["_id"]),
            receipt_key=updated.get("receipt_key"),
            source=updated["source"],
            timestamp=updated["timestamp"],
            found_bars=updated["found_bars"],
            final_bars=updated["final_bars"],
            review=updated["review"],
            status=updated["status"],
            items=[ReceiptItemResponse(**item) for item in updated.get("items", [])],
            raw_payload=updated.get("raw_payload"),
            session_id=updated.get("session_id"),
        )
