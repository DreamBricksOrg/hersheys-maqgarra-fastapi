from core.exceptions import AppError
from repositories.queue_repository import QueueRepository
from repositories.receipt_repository import ReceiptRepository
from repositories.session_repository import SessionRepository
from schemas.queue import QueueIntakeResponse, UserMobilePayloadResponse
from services.observability_service import ObservabilityService
from services.queue_service import QueueService


class QueueIntakeService:
    def __init__(
        self,
        receipt_repository: ReceiptRepository,
        session_repository: SessionRepository,
        queue_repository: QueueRepository,
        queue_service: QueueService,
        observability_service: ObservabilityService,
        mobile_base_url: str,
    ):
        self.receipt_repository = receipt_repository
        self.session_repository = session_repository
        self.queue_repository = queue_repository
        self.queue_service = queue_service
        self.observability_service = observability_service
        self.mobile_base_url = mobile_base_url.rstrip("/")

    async def execute(
        self,
        receipt_id: str,
        total_plays: int = 1,
        phone: str | None = None,
    ) -> QueueIntakeResponse:
        receipt = await self.receipt_repository.find_by_id(receipt_id)
        if not receipt:
            raise AppError("receipt_not_found", "Receipt não encontrado", 404, {"receipt_id": receipt_id})

        receipt_status = receipt.get("status")
        if receipt_status not in {"valid", "approved"}:
            raise AppError(
                "receipt_not_eligible",
                "Receipt ainda não está elegível para entrar na fila",
                409,
                {"receipt_id": receipt_id, "status": receipt_status},
            )

        session = await self.session_repository.find_by_receipt_id(receipt_id)
        if not session:
            raise AppError(
                "session_required",
                "A sessão precisa ser criada antes do intake da fila",
                409,
                {"receipt_id": receipt_id},
            )

        if not session.get("player_id"):
            raise AppError(
                "session_missing_player",
                "A sessão precisa ter player_id antes de entrar na fila",
                409,
                {"session_id": str(session["_id"])},
            )

        joined = await self.queue_service.join(
            session_id=str(session["_id"]),
            total_plays=total_plays,
        )

        qr_value = joined.player_id
        qr_url = f"{self.mobile_base_url}/user-qrcode?pid={joined.player_id}"

        await self.observability_service.emit(
            "queue-intake-created",
            {
                "receipt_id": receipt_id,
                "session_id": str(session["_id"]),
                "player_id": joined.player_id,
                "queue_number": joined.queue_number,
                "total_plays": total_plays,
            },
        )

        return QueueIntakeResponse(
            session_id=str(session["_id"]),
            receipt_id=receipt_id,
            player_id=joined.player_id,
            queue_number=joined.queue_number,
            people_ahead=joined.people_ahead,
            status=joined.status,
            mobile_payload=UserMobilePayloadResponse(
                player_id=joined.player_id,
                queue_number=joined.queue_number,
                phone=phone or session.get("phone"),
                qr_value=qr_value,
                qr_url=qr_url,
                total_plays=joined.total_plays,
                remaining_plays=joined.remaining_plays,
                message="Você entrou na fila com sucesso.",
            ),
        )
