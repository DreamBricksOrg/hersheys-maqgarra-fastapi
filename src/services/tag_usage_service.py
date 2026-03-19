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

    async def _get_tag_or_raise(self, tag_key: str) -> dict:
        tag = await self.tag_repository.find_by_key(tag_key)
        if not tag:
            raise AppError(
                "Tag não encontrada",
                "tag_not_found",
                404,
                {"tag_key": tag_key},
            )
        return tag

    async def _ensure_tag_can_be_used(self, tag: dict) -> None:
        status = tag.get("status")
        tag_key = tag.get("tag_key")

        if status == "invalid":
            raise AppError(
                "Tag inválida",
                "tag_invalid",
                409,
                {"tag_key": tag_key},
            )

        if status == "available":
            raise AppError(
                "Tag ainda não foi associada a uma sessão",
                "tag_not_associated",
                409,
                {"tag_key": tag_key},
            )

        if status == "used":
            raise AppError(
                "Tag já foi usada",
                "tag_already_used",
                409,
                {"tag_key": tag_key},
            )

        if status != "valid":
            raise AppError(
                "Estado inválido para uso",
                "tag_invalid_state",
                409,
                {"tag_key": tag_key, "status": status},
            )

    async def use(self, tag_key: str) -> TagResponse:
        tag = await self._get_tag_or_raise(tag_key)
        await self._ensure_tag_can_be_used(tag)

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

    async def use_for_session(self, session_id: str, tag_key: str) -> TagResponse:
        tag = await self._get_tag_or_raise(tag_key)
        await self._ensure_tag_can_be_used(tag)

        tag_session_id = tag.get("session_id")
        if not tag_session_id or str(tag_session_id) != str(session_id):
            raise AppError(
                "A tag não pertence à sessão informada",
                "tag_not_belongs_to_session",
                409,
                {
                    "tag_key": tag_key,
                    "session_id": session_id,
                    "tag_session_id": str(tag_session_id) if tag_session_id else None,
                },
            )

        updated = await self.tag_repository.mark_used(tag_key)
        if not updated:
            raise AppError(
                "Não foi possível atualizar a tag",
                "tag_use_failed",
                500,
                {"tag_key": tag_key, "session_id": session_id},
            )

        await self.observability_service.emit(
            "tag-used-for-session",
            {
                "tag_key": tag_key,
                "session_id": session_id,
                "delivery_mode": updated.get("delivery_mode"),
                "result_status": updated.get("status"),
            },
        )

        return TagResponse.model_validate(updated)
