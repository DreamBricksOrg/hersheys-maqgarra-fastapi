from datetime import datetime
from typing import Any, Annotated, Literal

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def parse_object_id_to_str(value: Any) -> str:
    if isinstance(value, ObjectId):
        return str(value)
    return str(value)


ObjectIdStr = Annotated[str, BeforeValidator(parse_object_id_to_str)]

QueueStatus = Literal["waiting", "called", "playing", "done", "skipped", "requeued"]


class QueueJoinRequest(BaseModel):
    session_id: ObjectIdStr
    total_plays: int = Field(default=1, ge=1, le=20)


class QueueJoinResponse(BaseModel):
    player_id: ObjectIdStr
    session_id: ObjectIdStr
    queue_number: int
    status: QueueStatus
    total_plays: int
    remaining_plays: int
    people_ahead: int
    created_at: datetime


class QueueEntryResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )

    player_id: ObjectIdStr
    session_id: ObjectIdStr
    queue_number: int
    status: QueueStatus
    total_plays: int
    remaining_plays: int
    created_at: datetime
    called_at: datetime | None = None
    played_at: datetime | None = None
    completed_at: datetime | None = None
    requeued_from: int | None = None

    @model_validator(mode="before")
    @classmethod
    def map_mongo_id(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            if "player_id" not in data and "_id" in data:
                data["player_id"] = data["_id"]
        return data


class QueueStateResponse(BaseModel):
    player_id: ObjectIdStr
    session_id: ObjectIdStr
    queue_number: int
    current_queue_number: int | None = None
    status: QueueStatus
    people_ahead: int
    can_play: bool
    total_plays: int
    remaining_plays: int
    requeued_from: int | None = None


class QueueCurrentResponse(BaseModel):
    current_queue_number: int | None = None
    current_player_id: ObjectIdStr | None = None
    current_status: QueueStatus | None = None


class QueueNextResponse(BaseModel):
    current_queue_number: int
    player: QueueEntryResponse
    people_still_waiting: int


class QueueValidateRequest(BaseModel):
    player_id: ObjectIdStr


class QueueValidateResponse(BaseModel):
    allowed: bool
    action: Literal["play", "requeued"]
    player_id: ObjectIdStr
    queue_number: int
    current_queue_number: int | None = None
    new_queue_number: int | None = None
    message: str


class QueueCompleteRequest(BaseModel):
    player_id: ObjectIdStr


class QueueCompleteResponse(BaseModel):
    player_id: ObjectIdStr
    queue_number: int
    status: QueueStatus
    remaining_plays: int
    finished: bool


class QueueSkipRequest(BaseModel):
    reason: str | None = None


class QueueSkipResponse(BaseModel):
    skipped_player_id: ObjectIdStr
    skipped_queue_number: int
    next_player: QueueEntryResponse | None = None


class QueueListResponse(BaseModel):
    items: list[QueueEntryResponse] = Field(default_factory=list)
    current_queue_number: int | None = None
    total_waiting: int

class QueueIntakeRequest(BaseModel):
    receipt_id: ObjectIdStr
    total_plays: int = Field(default=1, ge=1, le=20)
    phone: str | None = None


class UserMobilePayloadResponse(BaseModel):
    player_id: ObjectIdStr
    queue_number: int
    phone: str | None = None
    qr_value: str
    qr_url: str
    total_plays: int
    remaining_plays: int
    message: str


class QueueIntakeResponse(BaseModel):
    session_id: ObjectIdStr
    receipt_id: ObjectIdStr
    player_id: ObjectIdStr
    queue_number: int
    people_ahead: int
    status: QueueStatus
    mobile_payload: UserMobilePayloadResponse


class QueueMobileViewResponse(BaseModel):
    player_id: ObjectIdStr
    session_id: ObjectIdStr
    queue_number: int
    current_queue_number: int | None = None
    people_ahead: int
    can_play: bool
    status: QueueStatus
    total_plays: int
    remaining_plays: int
    qr_value: str
    qr_url: str
