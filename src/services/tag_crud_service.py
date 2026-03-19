import secrets

from core.exceptions import AppError
from repositories.tag_repository import TagRepository
from schemas.tags import TagListResponse, TagResponse
from services.observability_service import ObservabilityService


class TagCrudService:
    def __init__(
        self,
        tag_repository: TagRepository,
        observability_service: ObservabilityService,
    ):
        self.tag_repository = tag_repository
        self.observability_service = observability_service

    async def _generate_unique_digital_tag_key(self) -> str:
        for _ in range(100):
            tag_key = f"{secrets.randbelow(100000000):08d}"
            existing = await self.tag_repository.find_by_key(tag_key)
            if not existing:
                return tag_key

        raise AppError(
            "tag_generation_failed",
            "Não foi possível gerar uma tag digital única",
            500,
        )

    async def create(
        self,
        tag_key: str | None = None,
        delivery_mode: str = "digital",
        status: str = "available",
        session_id: str | None = None,
    ) -> TagResponse:
        normalized_delivery_mode = delivery_mode.lower().strip()
        normalized_status = status.lower().strip()

        if normalized_delivery_mode not in {"digital", "physical"}:
            raise AppError(
                "invalid_delivery_mode",
                "delivery_mode inválido",
                422,
                {"delivery_mode": delivery_mode},
            )

        if normalized_status not in {"invalid", "available", "valid", "used"}:
            raise AppError(
                "invalid_tag_status",
                "status inválido",
                422,
                {"status": status},
            )

        final_tag_key = (tag_key or "").strip().upper()

        if normalized_delivery_mode == "digital":
            if final_tag_key:
                existing = await self.tag_repository.find_by_key(final_tag_key)
                if existing:
                    raise AppError(
                        "tag_already_exists",
                        "Já existe uma tag com esta chave",
                        409,
                        {"tag_key": final_tag_key},
                    )
            else:
                final_tag_key = await self._generate_unique_digital_tag_key()

        elif normalized_delivery_mode == "physical":
            if not final_tag_key:
                raise AppError(
                    "physical_tag_key_required",
                    "Tag física precisa ser criada com tag_key explícita",
                    422,
                )

            existing = await self.tag_repository.find_by_key(final_tag_key)
            if existing:
                raise AppError(
                    "tag_already_exists",
                    "Já existe uma tag com esta chave",
                    409,
                    {"tag_key": final_tag_key},
                )

        created = await self.tag_repository.create(
            tag_key=final_tag_key,
            delivery_mode=normalized_delivery_mode,
            status=normalized_status,
            session_id=session_id,
        )

        await self.observability_service.emit(
            "tag-created",
            {
                "tag_key": final_tag_key,
                "delivery_mode": normalized_delivery_mode,
                "status": normalized_status,
                "session_id": session_id,
            },
        )

        return TagResponse.model_validate(created)

    async def list(
        self,
        status: str | None = None,
        session_id: str | None = None,
        tag_key: str | None = None,
        delivery_mode: str | None = None,
    ) -> TagListResponse:
        items = await self.tag_repository.list_tags(
            status=status,
            session_id=session_id,
            tag_key=tag_key,
            delivery_mode=delivery_mode,
        )
        return TagListResponse(
            items=[TagResponse.model_validate(item) for item in items]
        )

    async def get_by_id(self, tag_id: str) -> TagResponse:
        tag = await self.tag_repository.find_by_id(tag_id)
        if not tag:
            raise AppError("tag_not_found", "Tag não encontrada", 404, {"tag_id": tag_id})

        return TagResponse.model_validate(tag)

    async def update(
        self,
        tag_id: str,
        status: str | None = None,
        session_id: str | None = None,
        invalid_reason: str | None = None,
        delivery_mode: str | None = None,
    ) -> TagResponse:
        existing = await self.tag_repository.find_by_id(tag_id)
        if not existing:
            raise AppError("tag_not_found", "Tag não encontrada", 404, {"tag_id": tag_id})

        updated = await self.tag_repository.update(
            tag_id=tag_id,
            status=status,
            session_id=session_id,
            invalid_reason=invalid_reason,
            delivery_mode=delivery_mode,
            clear_session_id=session_id == "",
        )
        if not updated:
            raise AppError("tag_update_failed", "Não foi possível atualizar a tag", 500, {"tag_id": tag_id})

        await self.observability_service.emit(
            "tag-updated",
            {
                "tag_id": tag_id,
                "status": status,
                "session_id": session_id,
                "invalid_reason": invalid_reason,
                "delivery_mode": delivery_mode,
            },
        )

        return TagResponse.model_validate(updated)

    async def delete(self, tag_id: str) -> None:
        existing = await self.tag_repository.find_by_id(tag_id)
        if not existing:
            raise AppError("tag_not_found", "Tag não encontrada", 404, {"tag_id": tag_id})

        deleted = await self.tag_repository.delete(tag_id)
        if not deleted:
            raise AppError("tag_delete_failed", "Não foi possível excluir a tag", 500, {"tag_id": tag_id})

        await self.observability_service.emit(
            "tag-deleted",
            {
                "tag_id": tag_id,
                "tag_key": existing.get("tag_key"),
            },
        )
