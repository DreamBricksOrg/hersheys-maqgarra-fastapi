from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from bson import ObjectId
from fastapi import UploadFile

from repositories.receipt_repository import ReceiptRepository
from schemas.receipts import ReceiptResponse
from services.observability_service import ObservabilityService


UPLOAD_DIR = Path("src/static/uploads")


class ReceiptManualService:
    def __init__(
        self,
        receipt_repository: ReceiptRepository,
        observability_service: ObservabilityService,
    ):
        self.receipt_repository = receipt_repository
        self.observability_service = observability_service

    async def execute(self, image: UploadFile, found_bars: int) -> ReceiptResponse:
        suffix = Path(image.filename or "receipt.jpg").suffix or ".jpg"
        file_name = f"{uuid4().hex}{suffix}"
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        output_path = UPLOAD_DIR / file_name

        content = await image.read()
        output_path.write_bytes(content)
        await self.observability_service.emit(
            "receipt-manual-uploaded", {"file_name": file_name, "file_size": len(content)}
        )

        doc_id = ObjectId()
        payload = {
            "_id": doc_id,
            "receipt_key": str(doc_id),
            "source": "manual",
            "timestamp": datetime.now(timezone.utc),
            "found_bars": found_bars,
            "final_bars": found_bars,
            "review": False,
            "status": "valid",
            "raw_payload_id": None,
            "raw_payload": None,
            "items": None,
            "session_id": None,
            "image_path": str(output_path),
        }

        created = await self.receipt_repository.create(payload)
        await self.observability_service.emit(
            "receipt-manual-created",
            {"receipt_id": str(created["_id"]), "found_bars": found_bars},
        )

        return ReceiptResponse(
            receipt_id=str(created["_id"]),
            receipt_key=str(doc_id),
            source="manual",
            timestamp=created["timestamp"],
            found_bars=found_bars,
            final_bars=found_bars,
            review=False,
            status="valid",
            items=[],
            raw_payload=None,
            session_id=None,
        )
