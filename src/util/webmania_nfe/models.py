from typing import Optional
from pydantic import BaseModel


class SerproCredentials(BaseModel):
    consumer_key: str
    consumer_secret: str


class DfeImageRequest(BaseModel):
    imagens: list[str]
    modelo: str = "nfe"
    antifraude: bool = False


class DfeValidationResult(BaseModel):
    uuid: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None
    data: Optional[dict] = None


class CreditInfo(BaseModel):
    saldo: Optional[float] = None
    creditos_utilizados: Optional[float] = None
    data: Optional[dict] = None


class LogEntry(BaseModel):
    uuid: str
    status: Optional[str] = None
    data: Optional[dict] = None
