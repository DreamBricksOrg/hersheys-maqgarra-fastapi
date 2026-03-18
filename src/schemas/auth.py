from pydantic import BaseModel


class AuthContext(BaseModel):
    api_key_id: str
    device_id: str | None = None
    api_key_name: str | None = None
