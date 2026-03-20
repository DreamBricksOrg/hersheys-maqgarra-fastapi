from core.exceptions import AppError
from repositories.receipt_repository import ReceiptRepository
from repositories.session_repository import SessionRepository
from schemas.sessions import (
    SessionCreateRequest,
    SessionPhoneUpdateRequest,
    SessionPhoneUpdateResponse,
    SessionResponse,
)
from services.observability_service import ObservabilityService
from services.queue_service import QueueService


class SessionService:
    def __init__(
        self,
        session_repository: SessionRepository,
        receipt_repository: ReceiptRepository,
        observability_service: ObservabilityService,
        queue_service: QueueService,
    ):
        self.session_repository = session_repository
        self.receipt_repository = receipt_repository
        self.observability_service = observability_service
        self.queue_service = queue_service

    async def create(self, payload: SessionCreateRequest) -> SessionResponse:
        if not payload.receipt_ids:
            raise AppError(
                "É necessário informar ao menos um receipt_id",
                "invalid_request",
                422,
            )

        if not payload.player_id or not str(payload.player_id).strip():
            raise AppError(
                "É necessário informar um player_id",
                "invalid_player_id",
                422,
            )

        if payload.total_plays < 1:
            raise AppError(
                "É necessário informar ao menos uma jogada",
                "invalid_total_plays",
                422,
            )

        unique_receipt_ids = list(dict.fromkeys(payload.receipt_ids))
        validated_receipt_ids: list[str] = []

        for receipt_id in unique_receipt_ids:
            receipt = await self.receipt_repository.find_by_id(receipt_id)
            if not receipt:
                raise AppError(
                    "Receipt não encontrado",
                    "receipt_not_found",
                    404,
                    {"receipt_id": receipt_id},
                )

            receipt_status = receipt.get("status")
            if receipt_status not in {"valid", "approved"}:
                raise AppError(
                    "Receipt ainda não está elegível para criar sessão",
                    "receipt_not_eligible",
                    409,
                    {"receipt_id": receipt_id, "status": receipt_status},
                )

            existing_session_id = receipt.get("session_id")
            if existing_session_id:
                raise AppError(
                    "Receipt já está vinculado a uma sessão",
                    "receipt_already_attached",
                    409,
                    {
                        "receipt_id": receipt_id,
                        "session_id": str(existing_session_id),
                    },
                )

            validated_receipt_ids.append(receipt_id)

        created = await self.session_repository.create(
            receipt_ids=validated_receipt_ids,
            player_id=payload.player_id,
            total_plays=payload.total_plays,
            phone=payload.phone,
        )

        session_id = str(created["_id"])

        try:
            for receipt_id in validated_receipt_ids:
                await self.receipt_repository.attach_session_id(receipt_id, session_id)
        except Exception as exc:
            await self.observability_service.emit(
                "session-create-partial-failure",
                {
                    "session_id": session_id,
                    "player_id": payload.player_id,
                    "receipt_ids": validated_receipt_ids,
                    "error": str(exc),
                },
            )
            raise AppError(
                "Falha ao vincular os receipts à sessão criada",
                "session_receipt_attach_failed",
                500,
                {
                    "session_id": session_id,
                    "receipt_ids": validated_receipt_ids,
                },
            )

        await self.observability_service.emit(
            "session-created",
            {
                "session_id": session_id,
                "player_id": payload.player_id,
                "receipt_ids": validated_receipt_ids,
                "total_plays": payload.total_plays,
                "phone": payload.phone,
            },
        )

        return SessionResponse.model_validate(created)

    async def get_by_id(self, session_id: str) -> SessionResponse:
        session = await self.session_repository.find_by_id(session_id)
        if not session:
            raise AppError(
                "Sessão não encontrada",
                "session_not_found",
                404,
                {"session_id": session_id},
            )

        return SessionResponse.model_validate(session)

    async def update_phone(
        self,
        session_id: str,
        payload: SessionPhoneUpdateRequest,
    ) -> SessionPhoneUpdateResponse:
        session = await self.session_repository.find_by_id(session_id)
        if not session:
            raise AppError(
                "Sessão não encontrada",
                "session_not_found",
                404,
                {"session_id": session_id},
            )

        updated = await self.session_repository.update_phone(session_id, payload.phone)
        if not updated:
            raise AppError(
                "Não foi possível atualizar o telefone da sessão",
                "session_phone_update_failed",
                500,
                {"session_id": session_id},
            )

        sms_result = await self.queue_service.send_registration_sms_for_session(
            session_id, qr_code_url=payload.qr_code_url
        )

        await self.observability_service.emit(
            "session-phone-updated",
            {
                "session_id": session_id,
                "phone": payload.phone,
                "sms_sent": sms_result["sms_sent"],
                "queue_number": sms_result["queue_number"],
                "people_ahead": sms_result["people_ahead"],
            },
        )

        return SessionPhoneUpdateResponse(
            session_id=session_id,
            phone=payload.phone,
            queue_number=sms_result["queue_number"],
            people_ahead=sms_result["people_ahead"],
            sms_sent=sms_result["sms_sent"],
        )
