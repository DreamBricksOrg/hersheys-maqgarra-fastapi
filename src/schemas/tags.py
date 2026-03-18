from datetime import datetime
from typing import Any, Annotated

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def parse_object_id_to_str(value: Any) -> str:
    if isinstance(value, ObjectId):
        return str(value)
    return str(value)


ObjectIdStr = Annotated[str, BeforeValidator(parse_object_id_to_str)]


class TagAssociateRequest(BaseModel):
    session_id: str | None = None
    receipt_ids: list[str] | None = None
    tags: list[str]


class TagStatusResponse(BaseModel):
    tag_key: str
    status: str
    available_for_play: bool
    last_updated_at: datetime | None = None


class TagDeactivateRequest(BaseModel):
    reason: str | None = None


class TagActivateRequest(BaseModel):
    reason: str | None = None


class TagResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )

    tag_id: ObjectIdStr
    tag_key: str
    status: str
    last_updated_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def map_mongo_id(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            if "tag_id" not in data and "_id" in data:
                data["tag_id"] = data["_id"]
        return data


class TagAssociateResponse(BaseModel):
    session_id: ObjectIdStr | None = None
    receipt_ids: list[ObjectIdStr] = Field(default_factory=list)
    tags: list[TagResponse]
    associated: bool
