from core.exceptions import AppError
from repositories.receipt_repository import ReceiptRepository
from repositories.session_repository import SessionRepository
from repositories.tag_repository import TagRepository
from schemas.receipt_reuse import (
    CancelSessionForReuseResponse,
    ReceiptReuseCheckResponse,
)
from services.observability_service import ObservabilityService


REUSABLE_SESSION_STATUSES = {"created", "queued", "called"}
BLOCKED_SESSION_STATUSES = {"playing", "finished"}


class ReceiptReuseService:
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

    async def check_receipt_reuse(
        self,
        receipt_key: str,
    ) -> ReceiptReuseCheckResponse:
        receipt = await self.receipt_repository.find_latest_by_receipt_key(receipt_key)

        if not receipt:
            await self.observability_service.emit(
                "receipt-reuse-check-valid",
                {"receipt_key": receipt_key, "reason": "receipt_not_found"},
                tags=["receipt-reuse", "valid"],
            )
            return ReceiptReuseCheckResponse(
                status="valid",
                can_reuse=True,
                action="create_new_session",
            )

        session_id = receipt.get("session_id")
        receipt_id = str(receipt.get("_id"))

        if not session_id:
            await self.observability_service.emit(
                "receipt-reuse-check-valid",
                {
                    "receipt_key": receipt_key,
                    "receipt_id": receipt_id,
                    "reason": "receipt_without_session",
                },
                tags=["receipt-reuse", "valid"],
            )
            return ReceiptReuseCheckResponse(
                status="valid",
                can_reuse=True,
                action="create_new_session",
                receipt_id=receipt_id,
            )

        session = await self.session_repository.find_by_id(session_id)

        if not session:
            await self.observability_service.emit(
                "receipt-reuse-check-valid",
                {
                    "receipt_key": receipt_key,
                    "receipt_id": receipt_id,
                    "session_id": session_id,
                    "reason": "session_not_found",
                },
                tags=["receipt-reuse", "valid"],
            )
            return ReceiptReuseCheckResponse(
                status="valid",
                can_reuse=True,
                action="create_new_session",
                session_id=session_id,
                receipt_id=receipt_id,
            )

        session_status = session.get("status")

        if session_status == "cancelled":
            await self.observability_service.emit(
                "receipt-reuse-check-valid",
                {
                    "receipt_key": receipt_key,
                    "receipt_id": receipt_id,
                    "session_id": session_id,
                    "session_status": session_status,
                    "reason": "cancelled_session",
                },
                tags=["receipt-reuse", "valid"],
            )
            return ReceiptReuseCheckResponse(
                status="valid",
                can_reuse=True,
                action="create_new_session",
                session_id=session_id,
                session_status=session_status,
                receipt_id=receipt_id,
            )

        if session_status in REUSABLE_SESSION_STATUSES:
            await self.observability_service.emit(
                "receipt-reuse-check-already-used-not-played",
                {
                    "receipt_key": receipt_key,
                    "receipt_id": receipt_id,
                    "session_id": session_id,
                    "session_status": session_status,
                },
                tags=["receipt-reuse", "already-used-not-played"],
            )
            return ReceiptReuseCheckResponse(
                status="already_used_not_played",
                can_reuse=True,
                action="invalidate_previous_session",
                session_id=session_id,
                session_status=session_status,
                receipt_id=receipt_id,
            )

        if session_status in BLOCKED_SESSION_STATUSES:
            await self.observability_service.emit(
                "receipt-reuse-check-already-used-and-played",
                {
                    "receipt_key": receipt_key,
                    "receipt_id": receipt_id,
                    "session_id": session_id,
                    "session_status": session_status,
                },
                tags=["receipt-reuse", "already-used-and-played"],
            )
            return ReceiptReuseCheckResponse(
                status="already_used_and_played",
                can_reuse=False,
                action="deny",
                session_id=session_id,
                session_status=session_status,
                receipt_id=receipt_id,
            )

        await self.observability_service.emit(
            "receipt-reuse-check-denied-unknown-session-status",
            {
                "receipt_key": receipt_key,
                "receipt_id": receipt_id,
                "session_id": session_id,
                "session_status": session_status,
            },
            tags=["receipt-reuse", "deny", "unknown-status"],
        )
        return ReceiptReuseCheckResponse(
            status="already_used_and_played",
            can_reuse=False,
            action="deny",
            session_id=session_id,
            session_status=session_status,
            receipt_id=receipt_id,
        )

    async def cancel_session_for_reuse(
        self,
        session_id: str,
        receipt_key: str | None = None,
    ) -> CancelSessionForReuseResponse:
        session = await self.session_repository.find_by_id(session_id)

        if not session:
            raise AppError(
                "Sessão não encontrada",
                "session_not_found",
                404,
                {"session_id": session_id},
            )

        session_status = session.get("status")

        if session_status not in REUSABLE_SESSION_STATUSES:
            raise AppError(
                "Sessão não pode ser cancelada para reuso da nota",
                "session_cannot_be_cancelled_for_reuse",
                409,
                {
                    "session_id": session_id,
                    "session_status": session_status,
                },
            )

        invalidated_tags = await self.tag_repository.invalidate_by_session_id(session_id)
        invalidated_receipts = await self.receipt_repository.mark_session_receipts_as_replaced(
            session_id
        )
        cancelled_session = await self.session_repository.cancel(session_id)

        await self.observability_service.emit(
            "session-cancelled-for-reuse",
            {
                "session_id": session_id,
                "receipt_key": receipt_key,
                "invalidated_tags": invalidated_tags,
                "invalidated_receipts": invalidated_receipts,
                "previous_status": session_status,
                "new_status": cancelled_session.get("status"),
            },
            tags=["receipt-reuse", "session-cancelled"],
        )

        return CancelSessionForReuseResponse(
            session_id=session_id,
            status=cancelled_session.get("status"),
            invalidated_tags=invalidated_tags,
            invalidated_receipts=invalidated_receipts,
        )
