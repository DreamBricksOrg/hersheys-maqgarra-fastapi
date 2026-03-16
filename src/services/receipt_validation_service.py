from core.exceptions import AppError
from repositories.receipt_repository import ReceiptRepository


class ReceiptValidationService:
    def __init__(self, receipt_repository: ReceiptRepository):
        self.receipt_repository = receipt_repository

    async def ensure_not_duplicate(self, receipt_key: str | None) -> None:
        if not receipt_key:
            return
        existing = await self.receipt_repository.find_by_key(receipt_key)
        if existing:
            raise AppError(
                code="receipt_duplicate",
                message="Esta nota já foi utilizada",
                status_code=409,
                details={"receipt_key": receipt_key, "status": existing.get("status", "used")},
            )

    @staticmethod
    def build_status(found_bars: int, review: bool) -> str:
        if review:
            return "error"
        return "valid" if found_bars >= 0 else "invalid"
