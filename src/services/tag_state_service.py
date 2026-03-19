from core.exceptions import AppError
from repositories.tag_repository import TagRepository
from schemas.tags import TagStatusResponse


class TagStateService:
    def __init__(self, tag_repository: TagRepository):
        self.tag_repository = tag_repository

    async def get_state(self, tag_key: str) -> TagStatusResponse:
        tag = await self.tag_repository.find_by_key(tag_key)
        if not tag:
            raise AppError("Tag não encontrada", "tag_not_found", 404, {"tag_key": tag_key})

        return TagStatusResponse(
            tag_key=tag["tag_key"],
            status=tag["status"],
            available_for_play=tag["status"] == "valid",
            last_updated_at=tag.get("last_updated_at"),
        )

    async def activate(self, tag_key: str, reason: str | None = None) -> TagStatusResponse:
        tag = await self.tag_repository.find_by_key(tag_key)
        if not tag:
            raise AppError("Tag não encontrada", "tag_not_found", 404, {"tag_key": tag_key})

        if tag.get("status") == "available":
            raise AppError("A tag já está disponível", "tag_already_available", 409, {"tag_key": tag_key})

        if tag.get("status") == "valid":
            raise AppError("A tag já está associada", "tag_already_associated", 409, {"tag_key": tag_key})

        updated = await self.tag_repository.activate(tag_key, reason)

        return TagStatusResponse(
            tag_key=updated["tag_key"],
            status=updated["status"],
            available_for_play=False,
            last_updated_at=updated.get("last_updated_at"),
        )

    async def deactivate(self, tag_key: str, reason: str | None = None) -> TagStatusResponse:
        tag = await self.tag_repository.find_by_key(tag_key)
        if not tag:
            raise AppError("Tag não encontrada", "tag_not_found", 404, {"tag_key": tag_key})

        if tag.get("status") == "invalid":
            raise AppError("A tag já está inativa", "tag_already_inactive", 409, {"tag_key": tag_key})

        updated = await self.tag_repository.deactivate(tag_key, reason or "manual")

        return TagStatusResponse(
            tag_key=updated["tag_key"],
            status=updated["status"],
            available_for_play=False,
            last_updated_at=updated.get("last_updated_at"),
        )

    async def list_tags(self, amount: int) -> list[str]:
        tags = await self.tag_repository.find_by_status(limit=amount)
        return [t["tag_key"] for t in tags]
