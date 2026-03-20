from core.exceptions import AppError
from repositories.receipt_repository import ReceiptRepository
from services.redis_service import RedisService

class ReceiptValidationService:
    def __init__(self, receipt_repository: ReceiptRepository, redisService: RedisService):
        self.receipt_repository = receipt_repository
        self.redisService = redisService

    async def ensure_not_duplicate(self, receipt_key: str | None) -> None:
        if not receipt_key:
            return
        if self.redisService.is_value_present("receipt_key", receipt_key):
           existing = True 
        else :
            existing = await self.receipt_repository.find_by_key(receipt_key)
        if existing:
            raise AppError(
                message="Esta nota já foi utilizada",
                code="receipt_duplicate",
                status_code=409,
                details={"receipt_key": receipt_key, "status": existing.get("status", "used")},
            )

    @staticmethod
    def build_status(found_bars: int, review: bool) -> str:
        if review:
            return "error"
        return "valid" if found_bars > 0 else "invalid"
