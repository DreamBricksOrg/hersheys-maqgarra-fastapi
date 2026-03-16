from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ReceiptQRRequest(BaseModel):
    qr_value: str


class ReceiptOverrideRequest(BaseModel):
    receipt_id: str
    final_bars: int = Field(ge=0)
    reason: str | None = None


class ReceiptItemResponse(BaseModel):
    name: str
    quantity: int
    matched: bool


class ErrorAuditResponse(BaseModel):
    image_path: str


class ReceiptResponse(BaseModel):
    receipt_id: str
    receipt_key: str | None = None
    source: str
    timestamp: datetime
    found_bars: int
    final_bars: int
    review: bool
    status: str
    items: list[ReceiptItemResponse] = Field(default_factory=list)
    raw_payload: dict[str, Any] | None = None
    session_id: str | None = None
    error_audit: ErrorAuditResponse | None = None


class ReceiptListTagAssociateRequest(BaseModel):
    receipt_ids: list[str]
    tags: list[str]


class ReceiptLookupQueryResponse(ReceiptResponse):
    pass
