from core.exceptions import AppError
from repositories.tag_repository import TagRepository
from schemas.tags import TagResponse
from services.observability_service import ObservabilityService


class TagUsageService:
    def __init__(
        self,
        tag_repository: TagRepository,
        observability_service: ObservabilityService,
    ):
        self.tag_repository = tag_repository
        self.observability_service = observability_service

    async def use(self, tag_key: str) -> TagResponse:
        tag = await self.tag_repository.find_by_key(tag_key)
        if not tag:
            raise AppError("tag_not_found", "Tag não encontrada", 404, {"tag_key": tag_key})

        status = tag.get("status")

        if status == "invalid":
            raise AppError("tag_invalid", "Tag inválida ou expirada", 409, {"tag_key": tag_key})

        if status == "available":
            raise AppError("tag_not_associated", "Tag ainda não foi associada", 409, {"tag_key": tag_key})

        if status == "used":
            raise AppError("tag_already_used", "Tag já foi usada", 409, {"tag_key": tag_key})

        if status != "valid":
            raise AppError("tag_invalid_state", "Estado inválido para uso", 409, {"tag_key": tag_key, "status": status})

        updated = await self.tag_repository.mark_used(tag_key)

        await self.observability_service.emit(
            "tag-used",
            {"tag_key": tag_key},
        )

        return TagResponse.model_validate(updated)