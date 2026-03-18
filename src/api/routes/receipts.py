from fastapi import APIRouter, Depends, File, UploadFile

from api.dependencies import (
    get_database,
    get_receipt_image_service,
    get_receipt_override_service,
    get_receipt_qr_service,
    require_auth,
)
from repositories.receipt_repository import ReceiptRepository
from schemas.auth import AuthContext
from schemas.receipts import ReceiptOverrideRequest, ReceiptQRRequest, ReceiptResponse
from core.exceptions import AppError
from motor.motor_asyncio import AsyncIOMotorDatabase
from services.receipt_image_service import ReceiptImageService
from services.receipt_override_service import ReceiptOverrideService
from services.receipt_qr_service import ReceiptQRService

router = APIRouter(prefix="/api/receipts", tags=["receipts"])


@router.post("/qr", response_model=ReceiptResponse)
async def validate_receipt_by_qr(
    payload: ReceiptQRRequest,
    auth: AuthContext = Depends(require_auth),
    service: ReceiptQRService = Depends(get_receipt_qr_service),
) -> ReceiptResponse:
    return await service.execute(payload.qr_value)


@router.post("/image", response_model=ReceiptResponse)
async def validate_receipt_by_image(
    image: UploadFile = File(...),
    auth: AuthContext = Depends(require_auth),
    service: ReceiptImageService = Depends(get_receipt_image_service),
) -> ReceiptResponse:
    return await service.execute(image)


@router.get("/{receipt_id}", response_model=ReceiptResponse)
async def get_receipt(
    receipt_id: str,
    auth: AuthContext = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> ReceiptResponse:
    repo = ReceiptRepository(db)
    receipt = await repo.find_by_id(receipt_id)
    if not receipt:
        raise AppError("Nota não encontrada", "receipt_not_found", 404)
    return ReceiptResponse(
        receipt_id=str(receipt["_id"]),
        receipt_key=receipt.get("receipt_key"),
        source=receipt["source"],
        timestamp=receipt["timestamp"],
        found_bars=receipt["found_bars"],
        final_bars=receipt["final_bars"],
        review=receipt["review"],
        status=receipt["status"],
        items=receipt.get("items", []),
        raw_payload=receipt.get("raw_payload"),
        session_id=receipt.get("session_id"),
    )


@router.post("/override", response_model=ReceiptResponse)
async def override_receipt(
    payload: ReceiptOverrideRequest,
    auth: AuthContext = Depends(require_auth),
    service: ReceiptOverrideService = Depends(get_receipt_override_service),
) -> ReceiptResponse:
    return await service.execute(payload.receipt_id, payload.final_bars, payload.reason)
