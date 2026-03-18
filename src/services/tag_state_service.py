from datetime import datetime, timezone

from core.exceptions import AppError
from repositories.tag_repository import TagRepository
from schemas.tags import TagStatusResponse


class TagStateService:
    def __init__(self, tag_repository: TagRepository):
        self.tag_repository = tag_repository

    async def get_state(self, tag_key: str) -> TagStatusResponse:
        tag = await self.tag_repository.find_by_key(tag_key)
        if not tag:
            raise AppError("tag_not_found", "Tag não encontrada", 404, {"tag_key": tag_key})

        return TagStatusResponse(
            tag_key=tag["tag_key"],
            status=tag["status"],
            available_for_play=tag["status"] == "valid",
            last_updated_at=tag.get("last_updated_at"),
        )

    async def activate(self, tag_key: str, reason: str | None = None) -> TagStatusResponse:
        tag = await self.tag_repository.find_by_key(tag_key)
        if not tag:
            raise AppError("tag_not_found", "Tag não encontrada", 404, {"tag_key": tag_key})

        if tag["status"] == "available":
            raise AppError("tag_already_available", "A tag já está disponível", 409, {"tag_key": tag_key})

        if tag["status"] == "valid":
            raise AppError("tag_already_associated", "A tag já está associada", 409, {"tag_key": tag_key})

        if tag["status"] == "used":
            raise AppError("tag_already_used", "A tag já foi utilizada", 409, {"tag_key": tag_key})

        await self.tag_repository.collection.update_one(
            {"tag_key": tag_key},
            {
                "$set": {
                    "status": "available",
                    "invalid_reason": None,
                    "last_updated_at": datetime.now(timezone.utc),
                }
            },
        )

        updated = await self.tag_repository.find_by_key(tag_key)

        return TagStatusResponse(
            tag_key=updated["tag_key"],
            status=updated["status"],
            available_for_play=False,
            last_updated_at=updated.get("last_updated_at"),
        )

    async def deactivate(self, tag_key: str, reason: str | None = None) -> TagStatusResponse:
        tag = await self.tag_repository.find_by_key(tag_key)
        if not tag:
            raise AppError("tag_not_found", "Tag não encontrada", 404, {"tag_key": tag_key})

        if tag["status"] == "invalid":
            raise AppError("tag_already_inactive", "A tag já está inativa", 409, {"tag_key": tag_key})

        await self.tag_repository.collection.update_one(
            {"tag_key": tag_key},
            {
                "$set": {
                    "status": "invalid",
                    "invalid_reason": reason or "timeout",
                    "last_updated_at": datetime.now(timezone.utc),
                }
            },
        )

        updated = await self.tag_repository.find_by_key(tag_key)

        return TagStatusResponse(
            tag_key=updated["tag_key"],
            status=updated["status"],
            available_for_play=False,
            last_updated_at=updated.get("last_updated_at"),
        )