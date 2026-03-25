from repositories.receipt_repository import ReceiptRepository
from schemas.receipts import ReceiptUnusedResponse
from services.observability_service import ObservabilityService
from core.exceptions import AppError
from datetime import datetime

class ReceiptUnusedService:
    def __init__(self, receipt_repository: ReceiptRepository, observability_service: ObservabilityService):
        self.receipt_repository = receipt_repository
        self.observability_service = observability_service

    async def execute(self, receipt_ids: list[str]) -> ReceiptUnusedResponse:
        for receipt_id in receipt_ids:
            receipt = await self.receipt_repository.find_by_id(receipt_id)
            if not receipt:
                raise AppError("Nota não encontrada", "receipt_not_found", 404)
            now = datetime.now()
            formatted_ts = now.strftime("%Y-%m-%d %H:%M:%S")
            receipt_key_formatted = receipt["receipt_key"] + "D_" + formatted_ts
            
            await self.receipt_repository.update_by_id(
                receipt_id,
                {"receipt_key": receipt_key_formatted},
            )
            await self.observability_service.emit("receipt-override", {"receipt_key": receipt_key_formatted})
        return ReceiptUnusedResponse.model_validate({"success": True})
        
