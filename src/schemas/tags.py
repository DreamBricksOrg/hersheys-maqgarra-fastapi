from datetime import datetime

from pydantic import BaseModel, Field


class TagAssociateRequest(BaseModel):
    session_id: str | None = None
    receipt_ids: list[str] | None = None
    tags: list[str] = Field(min_length=1)


class TagStatusResponse(BaseModel):
    tag_key: str
    status: str
    available_for_play: bool
    last_updated_at: datetime | None = None


class TagDeactivateRequest(BaseModel):
    reason: str | None = None


class TagResponse(BaseModel):
    tag_key: str
    status: str


class TagAssociateResponse(BaseModel):
    session_id: str
    receipt_ids: list[str]
    tags: list[TagResponse]
    associated: bool
