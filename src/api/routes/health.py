from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/alive")
async def alive() -> dict[str, str]:
    return {"status": "ok"}
