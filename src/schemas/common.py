from typing import Any
from pydantic import BaseModel, Field


class ErrorDetails(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetails
