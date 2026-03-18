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

    async def create(
        self,
        tag_key: str,
        status: str = "available",
        session_id: str | None = None,
        invalid_reason: str | None = None,
    ) -> TagResponse:
        existing = await self.tag_repository.find_by_key(tag_key)
        if existing:
            raise AppError("tag_already_exists", "Tag já existe", 409, {"tag_key": tag_key})

        created = await self.tag_repository.create(
            tag_key=tag_key,
            status=status,
            session_id=session_id,
            invalid_reason=invalid_reason,
        )

        await self.observability_service.emit(
            "tag-created",
            {"tag_key": tag_key, "status": status},
        )

        return TagResponse.model_validate(created)

    async def list(
        self,
        status: str | None = None,
        session_id: str | None = None,
        tag_key: str | None = None,
    ) -> TagListResponse:
        items = await self.tag_repository.list_tags(
            status=status,
            session_id=session_id,
            tag_key=tag_key,
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
    ) -> TagResponse:
        tag = await self.tag_repository.find_by_id(tag_id)
        if not tag:
            raise AppError("tag_not_found", "Tag não encontrada", 404, {"tag_id": tag_id})

        updated = await self.tag_repository.update(
            tag_id=tag_id,
            status=status,
            session_id=session_id,
            invalid_reason=invalid_reason,
        )

        await self.observability_service.emit(
            "tag-updated",
            {"tag_id": tag_id, "status": status, "session_id": session_id},
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
