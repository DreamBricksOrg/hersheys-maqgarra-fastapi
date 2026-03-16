from core.exceptions import AppError
from repositories.receipt_repository import ReceiptRepository
from repositories.session_repository import SessionRepository
from repositories.tag_repository import TagRepository
from schemas.tags import TagAssociateResponse, TagResponse
from services.observability_service import ObservabilityService


class TagAssociationService:
    def __init__(
        self,
        receipt_repository: ReceiptRepository,
        session_repository: SessionRepository,
        tag_repository: TagRepository,
        observability_service: ObservabilityService,
    ):
        self.receipt_repository = receipt_repository
        self.session_repository = session_repository
        self.tag_repository = tag_repository
        self.observability_service = observability_service

    async def execute(self, session_id: str | None, receipt_ids: list[str] | None, tags: list[str]) -> TagAssociateResponse:
        if not session_id and not receipt_ids:
            raise AppError("invalid_request", "session_id ou receipt_ids é obrigatório", 422)

        if session_id:
            session = await self.session_repository.find_by_id(session_id)
            if not session:
                raise AppError("session_not_found", "Sessão não encontrada", 404)
            resolved_receipt_ids = session.get("receipt_ids", [])
        else:
            resolved_receipt_ids = receipt_ids or []
            session = await self.session_repository.create(receipt_ids=resolved_receipt_ids)
            session_id = str(session["_id"])

        for tag_key in tags:
            tag = await self.tag_repository.find_by_key(tag_key)
            if not tag:
                await self.observability_service.emit("tag-association-failed", {"tag_key": tag_key, "reason": "not_found"})
                raise AppError("tag_not_found", "Tag não encontrada", 404, {"tag_key": tag_key})
            if tag.get("status") == "valid":
                await self.observability_service.emit("tag-association-failed", {"tag_key": tag_key, "reason": "already_used"})
                raise AppError("tag_already_used", "Uma ou mais tags já estão em uso", 409, {"tags": [tag_key]})

        activated = await self.tag_repository.activate_many(tags)
        await self.receipt_repository.mark_used_many(resolved_receipt_ids)
        await self.session_repository.attach_tags(session_id, [item["tag_key"] for item in activated])
        await self.observability_service.emit("tag-association-created", {"session_id": session_id, "tags": tags})
        return TagAssociateResponse(
            session_id=session_id,
            receipt_ids=resolved_receipt_ids,
            tags=[TagResponse(tag_key=item["tag_key"], status=item["status"]) for item in activated],
            associated=True,
        )
