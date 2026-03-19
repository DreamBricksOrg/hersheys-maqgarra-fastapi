from datetime import datetime
from typing import Any, Annotated, Literal

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def parse_object_id_to_str(value: Any) -> str:
    if isinstance(value, ObjectId):
        return str(value)
    return str(value)


ObjectIdStr = Annotated[str, BeforeValidator(parse_object_id_to_str)]

TagStatus = Literal["invalid", "available", "valid", "used"]
TagDeliveryMode = Literal["digital", "physical"]


class TagGenerateRequest(BaseModel):
    session_id: ObjectIdStr
    delivery_mode: TagDeliveryMode = "digital"


class TagAssociateRequest(BaseModel):
    session_id: ObjectIdStr
    delivery_mode: TagDeliveryMode = "physical"
    tag_key: str | None = None


class TagActivateRequest(BaseModel):
    reason: str | None = None


class TagDeactivateRequest(BaseModel):
    reason: str | None = None


class TagUseRequest(BaseModel):
    tag_key: str


class TagCreateRequest(BaseModel):
    tag_key: str | None = None
    delivery_mode: TagDeliveryMode = "digital"
    status: TagStatus = "available"
    session_id: ObjectIdStr | None = None


class TagUpdateRequest(BaseModel):
    status: TagStatus | None = None
    session_id: ObjectIdStr | None = None
    invalid_reason: str | None = None
    delivery_mode: TagDeliveryMode | None = None


class TagStatusResponse(BaseModel):
    tag_key: str
    status: TagStatus
    available_for_play: bool
    last_updated_at: datetime | None = None


class TagResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )

    tag_id: ObjectIdStr
    tag_key: str
    delivery_mode: TagDeliveryMode
    status: TagStatus
    session_id: ObjectIdStr | None = None
    last_updated_at: datetime | None = None
    used_at: datetime | None = None
    invalid_reason: str | None = None

    @model_validator(mode="before")
    @classmethod
    def map_mongo_id(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)

            if "tag_id" not in data and "_id" in data:
                data["tag_id"] = data["_id"]

            if "session_id" in data and isinstance(data["session_id"], ObjectId):
                data["session_id"] = str(data["session_id"])

        return data


class TagAssociateResponse(BaseModel):
    session_id: ObjectIdStr
    tag: TagResponse
    associated: bool


class TagListResponse(BaseModel):
    items: list[TagResponse] = Field(default_factory=list)


class SessionTagsResponse(BaseModel):
    session_id: ObjectIdStr
    tags: list[TagResponse] = Field(default_factory=list)
