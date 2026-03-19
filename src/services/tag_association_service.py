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
                "session_not_found",
                "Sessão não encontrada",
                404,
                {"session_id": session_id},
            )
        return session

    async def _ensure_tag_capacity_for_session(self, session_id: str) -> dict:
        session = await self._get_session_or_raise(session_id)
        max_tags = int(session.get("total_plays", 1))
        valid_tags = await self.tag_repository.find_valid_by_session_id(session_id)

        if len(valid_tags) >= max_tags:
            raise AppError(
                "session_tag_limit_reached",
                "Limite de tags válidas da sessão já foi atingido",
                409,
                {
                    "session_id": session_id,
                    "max_tags": max_tags,
                    "current_valid_tags": len(valid_tags),
                },
            )

        return session

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

    async def generate(self, payload: TagGenerateRequest) -> TagResponse:
        await self._ensure_tag_capacity_for_session(payload.session_id)

        if payload.delivery_mode != "digital":
            raise AppError(
                "invalid_delivery_mode",
                "A rota de geração automática é destinada a tags digitais",
                422,
                {"delivery_mode": payload.delivery_mode},
            )

        tag_key = await self._generate_unique_digital_tag_key()
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
        await self._ensure_tag_capacity_for_session(payload.session_id)

        if payload.delivery_mode != "physical":
            raise AppError(
                "invalid_delivery_mode",
                "A rota de associação é destinada a tags físicas",
                422,
                {"delivery_mode": payload.delivery_mode},
            )

        if payload.tag_key:
            tag = await self.tag_repository.find_by_key(payload.tag_key)
            if not tag:
                raise AppError(
                    "tag_not_found",
                    "Tag não encontrada",
                    404,
                    {"tag_key": payload.tag_key},
                )
        else:
            tag = await self.tag_repository.find_available_physical()
            if not tag:
                raise AppError(
                    "tag_not_available",
                    "Não há tags físicas disponíveis",
                    409,
                )

        status = tag.get("status")
        if status == "invalid":
            raise AppError("tag_invalid", "Tag inválida", 409, {"tag_key": tag["tag_key"]})

        if status == "used":
            raise AppError("tag_already_used", "Tag já foi usada", 409, {"tag_key": tag["tag_key"]})

        if status == "valid":
            raise AppError(
                "tag_already_associated",
                "Tag já está associada",
                409,
                {"tag_key": tag["tag_key"]},
            )

        if status != "available":
            raise AppError(
                "tag_invalid_state",
                "Tag em estado inválido para associação",
                409,
                {"tag_key": tag["tag_key"], "status": status},
            )

        if tag.get("delivery_mode") != "physical":
            raise AppError(
                "invalid_tag_delivery_mode",
                "A tag informada não é física",
                409,
                {
                    "tag_key": tag["tag_key"],
                    "delivery_mode": tag.get("delivery_mode"),
                },
            )

        associated = await self.tag_repository.associate_one(payload.session_id, tag["tag_key"])
        if not associated:
            raise AppError(
                "tag_association_failed",
                "Não foi possível associar a tag à sessão",
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
