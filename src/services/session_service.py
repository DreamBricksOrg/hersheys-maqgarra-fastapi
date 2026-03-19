from core.exceptions import AppError
from repositories.receipt_repository import ReceiptRepository
from repositories.session_repository import SessionRepository
from schemas.sessions import SessionCreateRequest, SessionResponse
from services.observability_service import ObservabilityService


class SessionService:
    def __init__(
        self,
        session_repository: SessionRepository,
        receipt_repository: ReceiptRepository,
        observability_service: ObservabilityService,
    ):
        self.session_repository = session_repository
        self.receipt_repository = receipt_repository
        self.observability_service = observability_service

    async def create(self, payload: SessionCreateRequest) -> SessionResponse:
        if not payload.receipt_ids:
            raise AppError("invalid_request", "É necessário informar ao menos um receipt_id", 422)

        validated_receipt_ids: list[str] = []

        for receipt_id in payload.receipt_ids:
            receipt = await self.receipt_repository.find_by_id(receipt_id)
            if not receipt:
                raise AppError("receipt_not_found", "Receipt não encontrado", 404, {"receipt_id": receipt_id})

            receipt_status = receipt.get("status")
            if receipt_status not in {"valid", "approved"}:
                raise AppError(
                    "receipt_not_eligible",
                    "Receipt ainda não está elegível para criar sessão",
                    409,
                    {"receipt_id": receipt_id, "status": receipt_status},
                )

            existing_session_id = receipt.get("session_id")
            if existing_session_id:
                raise AppError(
                    "receipt_already_attached",
                    "Receipt já está vinculado a uma sessão",
                    409,
                    {"receipt_id": receipt_id, "session_id": str(existing_session_id)},
                )

            validated_receipt_ids.append(receipt_id)

        created = await self.session_repository.create(
            receipt_ids=validated_receipt_ids,
            player_id=payload.player_id,
            phone=payload.phone,
        )

        session_id = str(created["_id"])

        for receipt_id in validated_receipt_ids:
            await self.receipt_repository.attach_session_id(receipt_id, session_id)

        await self.observability_service.emit(
            "session-created",
            {
                "session_id": session_id,
                "player_id": payload.player_id,
                "receipt_ids": validated_receipt_ids,
                "phone": payload.phone,
            },
        )

        return SessionResponse.model_validate(created)

    async def get_by_id(self, session_id: str) -> SessionResponse:
        session = await self.session_repository.find_by_id(session_id)
        if not session:
            raise AppError("session_not_found", "Sessão não encontrada", 404, {"session_id": session_id})

        return SessionResponse.model_validate(session)
