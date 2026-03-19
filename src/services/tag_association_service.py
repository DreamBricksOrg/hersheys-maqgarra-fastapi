import secrets

from core.exceptions import AppError
from repositories.session_repository import SessionRepository
from repositories.tag_repository import TagRepository
from schemas.tags import (
    TagAssociateRequest,
    TagAssociateResponse,
    TagGenerateRequest,
    TagResponse,
)
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

    async def _get_session_or_raise(self, session_id: str) -> dict:
        session = await self.session_repository.find_by_id(session_id)
        if not session:
            raise AppError(
                "Sessão não encontrada",
                "session_not_found",
                404,
                {"session_id": session_id},
            )
        return session

    async def _ensure_no_valid_tag_for_session(self, session_id: str) -> None:
        valid_tags = await self.tag_repository.find_valid_by_session_id(session_id)
        if valid_tags:
            raise AppError(
                "A sessão já possui uma tag válida associada",
                "session_already_has_valid_tag",
                409,
                {
                    "session_id": session_id,
                    "tag_keys": [item["tag_key"] for item in valid_tags],
                },
            )

    async def _generate_unique_tag_key(self) -> str:
        for _ in range(100):
            tag_key = f"T{secrets.randbelow(10000):04d}"
            existing = await self.tag_repository.find_by_key(tag_key)
            if not existing:
                return tag_key

        raise AppError(
            "Não foi possível gerar uma tag única",
            "tag_generation_failed",
            500,
        )

    async def generate(self, payload: TagGenerateRequest) -> TagResponse:
        await self._get_session_or_raise(payload.session_id)
        await self._ensure_no_valid_tag_for_session(payload.session_id)

        if payload.delivery_mode != "digital":
            raise AppError(
                "A rota de geração automática é destinada a tags digitais",
                "invalid_delivery_mode",
                422,
                {"delivery_mode": payload.delivery_mode},
            )

        tag_key = await self._generate_unique_tag_key()
        created = await self.tag_repository.create(
            tag_key=tag_key,
            delivery_mode="digital",
            status="valid",
            session_id=payload.session_id,
        )

        await self.session_repository.attach_tags(payload.session_id, [str(created["_id"])])

        await self.observability_service.emit(
            "tag-generated",
            {
                "session_id": payload.session_id,
                "tag_key": tag_key,
                "delivery_mode": "digital",
            },
        )

        return TagResponse.model_validate(created)

    async def associate(self, payload: TagAssociateRequest) -> TagAssociateResponse:
        await self._get_session_or_raise(payload.session_id)
        await self._ensure_no_valid_tag_for_session(payload.session_id)

        if payload.delivery_mode != "physical":
            raise AppError(
                "A rota de associação é destinada a tags físicas",
                "invalid_delivery_mode",
                422,
                {"delivery_mode": payload.delivery_mode},
            )

        tag: dict | None = None

        if payload.tag_key:
            tag = await self.tag_repository.find_by_key(payload.tag_key)
            if not tag:
                raise AppError(
                    "Tag não encontrada",
                    "tag_not_found",
                    404,
                    {"tag_key": payload.tag_key},
                )
        else:
            tag = await self.tag_repository.find_available_physical()
            if not tag:
                raise AppError(
                    "Não há tags físicas disponíveis",
                    "tag_not_available",
                    409,
                )

        status = tag.get("status")
        if status == "invalid":
            raise AppError("Tag inválida", "tag_invalid", 409, {"tag_key": tag["tag_key"]})

        if status == "used":
            raise AppError("Tag já foi usada", "tag_already_used", 409, {"tag_key": tag["tag_key"]})

        if status == "valid":
            raise AppError(
                "Tag já está associada",
                "tag_already_associated",
                409,
                {"tag_key": tag["tag_key"]},
            )

        if status != "available":
            raise AppError(
                "Tag em estado inválido para associação",
                "tag_invalid_state",
                409,
                {"tag_key": tag["tag_key"], "status": status},
            )

        associated = await self.tag_repository.associate_one(payload.session_id, tag["tag_key"])
        if not associated:
            raise AppError(
                "Não foi possível associar a tag à sessão",
                "tag_association_failed",
                409,
                {"tag_key": tag["tag_key"], "session_id": payload.session_id},
            )

        await self.session_repository.attach_tags(payload.session_id, [str(associated["_id"])])

        await self.observability_service.emit(
            "tag-associated",
            {
                "session_id": payload.session_id,
                "tag_key": associated["tag_key"],
                "delivery_mode": associated["delivery_mode"],
            },
        )

        return TagAssociateResponse(
            session_id=payload.session_id,
            tag=TagResponse.model_validate(associated),
            associated=True,
        )
