from datetime import datetime, timezone

from repositories.raw_payload_repository import RawPayloadRepository
from repositories.receipt_repository import ReceiptRepository
from schemas.receipts import ReceiptResponse, ReceiptItemResponse
from services.observability_service import ObservabilityService
from services.parser_service import ParserService
from services.product_matching_service import ProductMatchingService
from services.receipt_validation_service import ReceiptValidationService


class ReceiptQRService:
    def __init__(
        self,
        parser_service: ParserService,
        product_matching_service: ProductMatchingService,
        receipt_validation_service: ReceiptValidationService,
        receipt_repository: ReceiptRepository,
        raw_payload_repository: RawPayloadRepository,
        observability_service: ObservabilityService,
    ):
        self.parser_service = parser_service
        self.product_matching_service = product_matching_service
        self.receipt_validation_service = receipt_validation_service
        self.receipt_repository = receipt_repository
        self.raw_payload_repository = raw_payload_repository
        self.observability_service = observability_service

    async def execute(self, qr_value: str) -> ReceiptResponse:
        await self.observability_service.emit("receipt-qr-received", {"qr_length": len(qr_value)})
        raw_payload = self.parser_service.parse_qr(qr_value)
        await self.observability_service.emit("receipt-qr-parsed", {"receipt_key": raw_payload.get("chave")})

        receipt_key = raw_payload.get("chave")
        await self.receipt_validation_service.ensure_not_duplicate(receipt_key)

        await self.observability_service.emit("product_matching-started", {"receipt_key": receipt_key})
        items, found_bars = await self.product_matching_service.match_products(raw_payload.get("produtos", []))
        await self.observability_service.emit("product_matching-finished", {"receipt_key": receipt_key, "found_bars": found_bars})

        review = False
        status = self.receipt_validation_service.build_status(found_bars, review)
        raw_payload_id = await self.raw_payload_repository.create(raw_payload)
        payload = {
            "receipt_key": receipt_key,
            "source": "qr",
            "timestamp": datetime.now(timezone.utc),
            "found_bars": found_bars,
            "final_bars": found_bars,
            "review": review,
            "status": status,
            "raw_payload_id": raw_payload_id,
            "raw_payload": raw_payload,
            "items": items,
            "session_id": None,
        }
        created = await self.receipt_repository.create(payload)
        await self.observability_service.emit("receipt-validation-finished", {"receipt_id": str(created["_id"]), "status": status})
        return ReceiptResponse(
            receipt_id=str(created["_id"]),
            receipt_key=created.get("receipt_key"),
            source=created["source"],
            timestamp=created["timestamp"],
            found_bars=created["found_bars"],
            final_bars=created["final_bars"],
            review=created["review"],
            status=created["status"],
            items=[ReceiptItemResponse(**item) for item in items],
            raw_payload=raw_payload,
            session_id=created.get("session_id"),
        )
