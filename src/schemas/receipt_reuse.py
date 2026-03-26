from typing import Literal, Optional

from pydantic import BaseModel


ReceiptReuseStatus = Literal[
    "valid",
    "already_used_not_played",
    "already_used_and_played",
]


ReceiptReuseAction = Literal[
    "create_new_session",
    "invalidate_previous_session",
    "deny",
]


class ReceiptReuseCheckRequest(BaseModel):
    receipt_key: str


class ReceiptReuseCheckResponse(BaseModel):
    status: ReceiptReuseStatus
    can_reuse: bool
    action: ReceiptReuseAction
    session_id: Optional[str] = None
    session_status: Optional[str] = None
    receipt_id: Optional[str] = None


class CancelSessionForReuseRequest(BaseModel):
    session_id: str
    receipt_key: Optional[str] = None


class CancelSessionForReuseResponse(BaseModel):
    session_id: str
    status: str
    invalidated_tags: int
    marked_receipts_as_replaced: int
