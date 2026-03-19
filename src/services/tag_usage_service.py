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
            raise AppError("Tag não encontrada", "tag_not_found", 404, {"tag_key": tag_key})

        status = tag.get("status")
        delivery_mode = tag.get("delivery_mode")

        if status == "invalid":
            raise AppError("Tag inválida", "tag_invalid", 409, {"tag_key": tag_key})

        if status == "available":
            raise AppError(
                "Tag ainda não foi associada",
                "tag_not_associated",
                409,
                {"tag_key": tag_key},
            )

        if status == "used" and delivery_mode != "physical":
            raise AppError("Tag já foi usada", "tag_already_used", 409, {"tag_key": tag_key})

        if status != "valid":
            raise AppError(
                "Estado inválido para uso",
                "tag_invalid_state",
                409,
                {"tag_key": tag_key, "status": status},
            )

        updated = await self.tag_repository.mark_used(tag_key)
        if not updated:
            raise AppError(
                "Não foi possível atualizar a tag",
                "tag_use_failed",
                500,
                {"tag_key": tag_key},
            )

        await self.observability_service.emit(
            "tag-used",
            {
                "tag_key": tag_key,
                "delivery_mode": updated.get("delivery_mode"),
                "result_status": updated.get("status"),
                "session_id": str(updated.get("session_id")) if updated.get("session_id") else None,
            },
        )

        return TagResponse.model_validate(updated)
