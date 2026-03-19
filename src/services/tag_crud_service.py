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

    async def _generate_unique_tag_key(self, delivery_mode: str) -> str:
        for _ in range(100):
            if delivery_mode == "digital":
                tag_key = str(secrets.randbelow(90000000) + 10000000)
            else:
                tag_key = f"T{secrets.randbelow(9000) + 1000}"

            existing = await self.tag_repository.find_by_key(tag_key)
            if not existing:
                return tag_key

        raise AppError("tag_generation_failed", "Não foi possível gerar uma tag única", 500)

    def _validate_tag_key_for_mode(self, tag_key: str, delivery_mode: str) -> None:
        if delivery_mode == "digital":
            if not tag_key.isdigit() or len(tag_key) != 8:
                raise AppError(
                    "invalid_tag_key",
                    "Tags digitais devem ter exatamente 8 dígitos numéricos",
                    422,
                    {"tag_key": tag_key, "delivery_mode": delivery_mode},
                )
            return

        if len(tag_key) != 5 or not tag_key.startswith("T") or not tag_key[1:].isdigit():
            raise AppError(
                "invalid_tag_key",
                "Tags físicas devem seguir o formato Txxxx",
                422,
                {"tag_key": tag_key, "delivery_mode": delivery_mode},
            )

    async def create(
        self,
        tag_key: str | None,
        delivery_mode: str,
        status: str = "available",
        session_id: str | None = None,
        invalid_reason: str | None = None,
    ) -> TagResponse:
        if tag_key:
            self._validate_tag_key_for_mode(tag_key, delivery_mode)
            existing = await self.tag_repository.find_by_key(tag_key)
            if existing:
                raise AppError("tag_already_exists", "Tag já existe", 409, {"tag_key": tag_key})
        else:
            tag_key = await self._generate_unique_tag_key(delivery_mode)

        created = await self.tag_repository.create(
            tag_key=tag_key,
            delivery_mode=delivery_mode,
            status=status,
            session_id=session_id,
            invalid_reason=invalid_reason,
        )

        await self.observability_service.emit(
            "tag-created",
            {"tag_key": tag_key, "status": status, "delivery_mode": delivery_mode},
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
        return TagListResponse(items=[TagResponse.model_validate(item) for item in items])

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
        tag = await self.tag_repository.find_by_id(tag_id)
        if not tag:
            raise AppError("tag_not_found", "Tag não encontrada", 404, {"tag_id": tag_id})

        updated = await self.tag_repository.update(
            tag_id=tag_id,
            status=status,
            session_id=session_id,
            invalid_reason=invalid_reason,
            delivery_mode=delivery_mode,
        )

        await self.observability_service.emit(
            "tag-updated",
            {
                "tag_id": tag_id,
                "status": status,
                "session_id": session_id,
                "delivery_mode": delivery_mode,
            },
        )

        return TagResponse.model_validate(updated)

    async def delete(self, tag_id: str) -> None:
        tag = await self.tag_repository.find_by_id(tag_id)
        if not tag:
            raise AppError("tag_not_found", "Tag não encontrada", 404, {"tag_id": tag_id})

        deleted = await self.tag_repository.delete(tag_id)
        if not deleted:
            raise AppError("tag_delete_failed", "Não foi possível excluir a tag", 500, {"tag_id": tag_id})

        await self.observability_service.emit(
            "tag-deleted",
            {"tag_id": tag_id},
        )
