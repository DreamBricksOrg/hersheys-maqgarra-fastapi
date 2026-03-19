from datetime import datetime
from typing import Any, Annotated

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def parse_object_id_to_str(value: Any) -> str:
    if isinstance(value, ObjectId):
        return str(value)
    return str(value)


ObjectIdStr = Annotated[str, BeforeValidator(parse_object_id_to_str)]


class ReceiptQRRequest(BaseModel):
    qr_value: str | None = None
    scraped_payload: dict | None = None
    matched_items: list[dict] | None = None
    qr_url: str | None = None


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
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )

    receipt_id: ObjectIdStr
    receipt_key: str | None = None
    source: str
    timestamp: datetime
    found_bars: int
    final_bars: int
    review: bool
    status: str
    items: list[ReceiptItemResponse] = Field(default_factory=list)
    raw_payload: dict[str, Any] | None = None
    session_id: ObjectIdStr | None = None
    error_audit: ErrorAuditResponse | None = None

    @model_validator(mode="before")
    @classmethod
    def map_mongo_id(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            if "receipt_id" not in data and "_id" in data:
                data["receipt_id"] = data["_id"]
        return data


class ReceiptListTagAssociateRequest(BaseModel):
    receipt_ids: list[str]
    tags: list[str]


class ReceiptCheckRequest(BaseModel):
    receipt_key: str


class ReceiptCheckResponse(BaseModel):
    is_duplicate: bool


class ReceiptLookupQueryResponse(ReceiptResponse):
    pass