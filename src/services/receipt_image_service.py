from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from core.config import settings
from repositories.raw_payload_repository import RawPayloadRepository
from repositories.receipt_repository import ReceiptRepository
from schemas.receipts import ErrorAuditResponse, ReceiptResponse
from services.observability_service import ObservabilityService
from services.parser_service import ParserService
from services.product_matching_service import ProductMatchingService
from services.receipt_validation_service import ReceiptValidationService


class ReceiptImageService:
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

    async def execute(self, image: UploadFile, webmania_data: dict | None = None) -> ReceiptResponse:
        suffix = Path(image.filename or "receipt.jpg").suffix or ".jpg"
        file_name = f"{uuid4().hex}{suffix}"
        output_path = settings.UPLOAD_DIR / file_name
        output_path.parent.mkdir(parents=True, exist_ok=True)

        content = await image.read()
        output_path.write_bytes(content)
        await self.observability_service.emit("receipt-image-erro-uploaded", {"file_name": file_name, "file_size": len(content)})
        await self.observability_service.emit("receipt-image-erro-stored", {"image_path": str(output_path)})

        if webmania_data:
            # Usa o JSON da Webmania diretamente como raw_payload
            raw_payload = dict(webmania_data)
            raw_payload.setdefault("image_path", str(output_path))
        else:
            # Fallback: placeholder (sem integração com terceiros)
            raw_payload = self.parser_service.parse_image(str(output_path))

        await self.observability_service.emit("product_matching-started", {"image_path": str(output_path)})
        items, found_bars = await self.product_matching_service.match_products(raw_payload.get("produtos", []))
        await self.observability_service.emit("product_matching-finished", {"image_path": str(output_path), "found_bars": found_bars})

        review = True
        status = self.receipt_validation_service.build_status(found_bars, review)
        raw_payload_id = await self.raw_payload_repository.create(raw_payload)
        payload = {
            "receipt_key": raw_payload.get("chave"),
            "source": "image",
            "timestamp": datetime.now(timezone.utc),
            "found_bars": found_bars,
            "final_bars": found_bars,
            "review": review,
            "status": status,
            "raw_payload_id": raw_payload_id,
            "raw_payload": raw_payload,
            "items": items,
            "session_id": None,
            "image_path": str(output_path),
        }
        created = await self.receipt_repository.create(payload)
        await self.observability_service.emit("receipt-image-audited", {"receipt_id": str(created["_id"]), "image_path": str(output_path)})

        return ReceiptResponse(
            receipt_id=str(created["_id"]),
            receipt_key=created.get("receipt_key"),
            source=created["source"],
            timestamp=created["timestamp"],
            found_bars=created["found_bars"],
            final_bars=created["final_bars"],
            review=created["review"],
            status=created["status"],
            items=items,
            raw_payload=raw_payload,
            session_id=None,
            error_audit=ErrorAuditResponse(image_path=str(output_path)),
        )
