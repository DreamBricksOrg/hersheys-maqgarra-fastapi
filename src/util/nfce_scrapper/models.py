from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class NfceSellerModel(BaseModel):
    name: str
    cnpj: str
    address: str


class NfceBuyerModel(BaseModel):
    cnpj: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None
    cpf: Optional[str] = None


class NfceItemModel(BaseModel):
    code: Optional[str] = None
    description: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    total_price: Decimal


class NfceTotalsModel(BaseModel):
    item_count: int
    subtotal: Optional[Decimal] = None
    discounts: Optional[Decimal] = None
    total: Decimal
    total_taxes: Optional[Decimal] = None


class NfcePaymentModel(BaseModel):
    method: str
    amount_paid: Decimal
    change: Optional[Decimal] = None


class NfceData(BaseModel):
    access_key: str
    invoice_number: str
    series: str
    issue_date: str
    authorization_protocol: str
    authorization_date: str
    seller: NfceSellerModel
    buyer: Optional[NfceBuyerModel] = None
    items: list[NfceItemModel]
    totals: NfceTotalsModel
    payments: list[NfcePaymentModel]
    is_cancelled: bool = False
    is_denied: bool = False
    is_epec_only: bool = False
    source_url: str
    scraped_at: str  # ISO datetime
