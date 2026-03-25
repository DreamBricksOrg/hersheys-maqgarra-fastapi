from datetime import datetime
from typing import Any, Annotated, Literal

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def parse_object_id_to_str(value: Any) -> str:
    if isinstance(value, ObjectId):
        return str(value)
    return str(value)


ObjectIdStr = Annotated[str, BeforeValidator(parse_object_id_to_str)]

SessionStatus = Literal["created", "queued", "called", "playing", "done", "cancelled"]


class SessionCreateRequest(BaseModel):
    receipt_ids: list[ObjectIdStr] = Field(min_length=1)
    player_id: ObjectIdStr
    total_plays: int = Field(default=1, ge=1, le=20)
    phone: str | None = None


class SessionPhoneUpdateRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=20)
    qr_code_url: str | None = None


class SessionPhoneUpdateResponse(BaseModel):
    session_id: str
    phone: str
    queue_number: int
    people_ahead: int
    sms_sent: bool


class SessionResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )

    session_id: ObjectIdStr
    receipt_ids: list[ObjectIdStr] = Field(default_factory=list)
    tag_ids: list[ObjectIdStr] = Field(default_factory=list)
    player_id: ObjectIdStr
    queue_entry_id: ObjectIdStr | None = None
    total_plays: int = 1
    phone: str | None = None
    status: SessionStatus = "created"
    created_at: datetime
    finished_at: datetime | None = None
    last_updated_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def map_mongo_id(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)

            if "session_id" not in data and "_id" in data:
                data["session_id"] = data["_id"]

            if "receipt_ids" in data:
                data["receipt_ids"] = [str(item) for item in data.get("receipt_ids", [])]

            if "tag_ids" in data:
                data["tag_ids"] = [str(item) for item in data.get("tag_ids", [])]

            if "player_id" in data and isinstance(data["player_id"], ObjectId):
                data["player_id"] = str(data["player_id"])

            if "queue_entry_id" in data and isinstance(data["queue_entry_id"], ObjectId):
                data["queue_entry_id"] = str(data["queue_entry_id"])

        return data
