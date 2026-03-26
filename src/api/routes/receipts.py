import json
from fastapi import APIRouter, Depends, File, Form, UploadFile

from api.dependencies import (
    get_database,
    get_receipt_image_service,
    get_receipt_manual_service,
    get_receipt_override_service,
    get_receipt_unused_service,
    get_receipt_qr_service,
    get_receipt_reuse_service,
    require_auth,
)
from repositories.receipt_repository import ReceiptRepository
from schemas.auth import AuthContext
from schemas.receipts import (
    ReceiptCheckRequest,
    ReceiptCheckResponse,
    ReceiptOverrideRequest,
    ReceiptQRRequest,
    ReceiptResponse,
    ReceiptUnusedRequest,
    ReceiptUnusedResponse,
)
from schemas.receipt_reuse import (
    CancelSessionForReuseRequest,
    CancelSessionForReuseResponse,
    ReceiptReuseCheckRequest,
    ReceiptReuseCheckResponse,
)
from core.exceptions import AppError
from motor.motor_asyncio import AsyncIOMotorDatabase
from services.receipt_image_service import ReceiptImageService
from services.receipt_manual_service import ReceiptManualService
from services.receipt_override_service import ReceiptOverrideService
from services.receipt_unused_service import ReceiptUnusedService
from services.receipt_qr_service import ReceiptQRService
from services.receipt_reuse_service import ReceiptReuseService

router = APIRouter(prefix="/api/receipts", tags=["receipts"])


@router.post("/qr", response_model=ReceiptResponse)
async def validate_receipt_by_qr(
    payload: ReceiptQRRequest,
    auth: AuthContext = Depends(require_auth),
    service: ReceiptQRService = Depends(get_receipt_qr_service),
) -> ReceiptResponse:
    return await service.execute(
        qr_value=payload.qr_value or "",
        scraped_payload=payload.scraped_payload,
        matched_items=payload.matched_items,
        qr_url=payload.qr_url,
    )


@router.post("/image", response_model=ReceiptResponse)
async def validate_receipt_by_image(
    image: UploadFile = File(...),
    webmania_payload: str = Form(None),
    matched_items: str = Form(None),
    processed_path: str = Form(None),
    auth: AuthContext = Depends(require_auth),
    service: ReceiptImageService = Depends(get_receipt_image_service),
) -> ReceiptResponse:
    parsed_webmania = json.loads(webmania_payload) if webmania_payload else None
    parsed_items = json.loads(matched_items) if matched_items else None
    return await service.execute(image, parsed_webmania, parsed_items, processed_path)


@router.post("/manual", response_model=ReceiptResponse)
async def create_manual_receipt(
    image: UploadFile = File(...),
    found_bars: int = Form(...),
    auth: AuthContext = Depends(require_auth),
    service: ReceiptManualService = Depends(get_receipt_manual_service),
) -> ReceiptResponse:
    return await service.execute(image, found_bars)


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


@router.post("/check", response_model=ReceiptCheckResponse)
async def check_duplicate_receipt(
    payload: ReceiptCheckRequest,
    auth: AuthContext = Depends(require_auth),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> ReceiptCheckResponse:
    repo = ReceiptRepository(db)
    existing = await repo.find_by_key(payload.receipt_key)
    return ReceiptCheckResponse(is_duplicate=bool(existing))


@router.post("/override", response_model=ReceiptResponse)
async def override_receipt(
    payload: ReceiptOverrideRequest,
    auth: AuthContext = Depends(require_auth),
    service: ReceiptOverrideService = Depends(get_receipt_override_service),
) -> ReceiptResponse:
    return await service.execute(payload.receipt_id, payload.final_bars, payload.reason)

@router.post("/unused", response_model=ReceiptUnusedResponse)
async def unused(
    payload: ReceiptUnusedRequest,
    auth: AuthContext = Depends(require_auth),
    service: ReceiptUnusedService = Depends(get_receipt_unused_service),
) -> ReceiptUnusedResponse:
    return await service.execute(payload.receipt_ids)

@router.post(
    "/reuse-check",
    response_model=ReceiptReuseCheckResponse,
)
async def receipt_reuse_check(
    payload: ReceiptReuseCheckRequest,
    receipt_reuse_service: ReceiptReuseService = Depends(get_receipt_reuse_service),
):
    return await receipt_reuse_service.check_receipt_reuse(payload.receipt_key)


@router.post(
    "/cancel-session-for-reuse",
    response_model=CancelSessionForReuseResponse,
)
async def cancel_session_for_reuse(
    payload: CancelSessionForReuseRequest,
    receipt_reuse_service: ReceiptReuseService = Depends(get_receipt_reuse_service),
):
    return await receipt_reuse_service.cancel_session_for_reuse(
        session_id=payload.session_id,
        receipt_key=payload.receipt_key,
    )
