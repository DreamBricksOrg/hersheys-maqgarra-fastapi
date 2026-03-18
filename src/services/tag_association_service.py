from core.exceptions import AppError
from repositories.session_repository import SessionRepository
from repositories.tag_repository import TagRepository
from schemas.tags import TagAssociateResponse, TagResponse
from services.observability_service import ObservabilityService


class TagAssociationService:
    def __init__(
        self,
        session_repository: SessionRepository,
        tag_repository: TagRepository,
        observability_service: ObservabilityService,
    ):
        self.session_repository = session_repository
        self.tag_repository = tag_repository
        self.observability_service = observability_service

    async def execute(self, session_id: str, tags: list[str]) -> TagAssociateResponse:
        session = await self.session_repository.find_by_id(session_id)
        if not session:
            raise AppError("session_not_found", "Sessão não encontrada", 404, {"session_id": session_id})

        if not tags:
            raise AppError("invalid_request", "É necessário informar ao menos uma tag", 422)

        if len(tags) != len(set(tags)):
            raise AppError("duplicate_tags", "Existem tags duplicadas na requisição", 422, {"tags": tags})

        for tag_key in tags:
            tag = await self.tag_repository.find_by_key(tag_key)

            if not tag:
                await self.observability_service.emit(
                    "tag-association-failed",
                    {"tag_key": tag_key, "reason": "not_found"},
                )
                raise AppError("tag_not_found", "Tag não encontrada", 404, {"tag_key": tag_key})

            status = tag.get("status")

            if status == "invalid":
                await self.observability_service.emit(
                    "tag-association-failed",
                    {"tag_key": tag_key, "reason": "invalid"},
                )
                raise AppError(
                    "tag_invalid",
                    "Uma ou mais tags estão inválidas",
                    409,
                    {"tags": [tag_key]},
                )

            if status == "valid":
                await self.observability_service.emit(
                    "tag-association-failed",
                    {"tag_key": tag_key, "reason": "already_associated"},
                )
                raise AppError(
                    "tag_already_associated",
                    "Uma ou mais tags já estão associadas",
                    409,
                    {"tags": [tag_key]},
                )

            if status == "used":
                await self.observability_service.emit(
                    "tag-association-failed",
                    {"tag_key": tag_key, "reason": "already_used"},
                )
                raise AppError(
                    "tag_already_used",
                    "Uma ou mais tags já foram usadas",
                    409,
                    {"tags": [tag_key]},
                )

            if status != "available":
                await self.observability_service.emit(
                    "tag-association-failed",
                    {"tag_key": tag_key, "reason": "invalid_state", "status": status},
                )
                raise AppError(
                    "tag_invalid_state",
                    "Uma ou mais tags estão em estado inválido para associação",
                    409,
                    {"tags": [tag_key], "status": status},
                )

            existing_session_id = tag.get("session_id")
            if existing_session_id and str(existing_session_id) != session_id:
                await self.observability_service.emit(
                    "tag-association-failed",
                    {
                        "tag_key": tag_key,
                        "reason": "belongs_to_another_session",
                        "session_id": str(existing_session_id),
                    },
                )
                raise AppError(
                    "tag_belongs_to_another_session",
                    "Uma ou mais tags já pertencem a outra sessão",
                    409,
                    {"tags": [tag_key]},
                )

        associated = await self.tag_repository.associate_many(session_id, tags)

        await self.session_repository.attach_tags(
            session_id,
            [str(item["_id"]) for item in associated],
        )

        await self.observability_service.emit(
            "tag-association-created",
            {"session_id": session_id, "tags": tags},
        )

        return TagAssociateResponse(
            session_id=session_id,
            tags=[TagResponse.model_validate(item) for item in associated],
            associated=True,
        )
