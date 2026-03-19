from pydantic import BaseModel


class ProductInput(BaseModel):
    nome: str
    quantidade: float | int | str = 0
    unidade: str | None = None


class ProductMatchRequest(BaseModel):
    produtos: list[ProductInput]


class ProductMatchedItem(BaseModel):
    name: str
    quantity: int
    matched: bool


class ProductMatchResponse(BaseModel):
    items: list[ProductMatchedItem]
    found_bars: int


class ProductLearnRequest(BaseModel):
    name: str


class ProductLearnResponse(BaseModel):
    name: str
    created: bool
