from fastapi import APIRouter, Depends

from api.dependencies import get_product_matching_service, require_auth
from schemas.auth import AuthContext
from schemas.products import (
    ProductLearnRequest,
    ProductLearnResponse,
    ProductMatchRequest,
    ProductMatchResponse,
)
from services.product_matching_service import ProductMatchingService

router = APIRouter(prefix="/api/products", tags=["products"])


@router.post("/match", response_model=ProductMatchResponse)
async def match_products(
    payload: ProductMatchRequest,
    auth: AuthContext = Depends(require_auth),
    service: ProductMatchingService = Depends(get_product_matching_service),
) -> ProductMatchResponse:
    produtos = [p.model_dump() for p in payload.produtos]
    items, found_bars = await service.match_products(produtos)
    return ProductMatchResponse(items=items, found_bars=found_bars)


@router.post("/learn", response_model=ProductLearnResponse)
async def learn_product(
    payload: ProductLearnRequest,
    auth: AuthContext = Depends(require_auth),
    service: ProductMatchingService = Depends(get_product_matching_service),
) -> ProductLearnResponse:
    _, created = await service.learn(payload.name)
    return ProductLearnResponse(name=payload.name, created=created)
