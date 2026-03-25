from typing import Any

from fastapi import Depends, Header, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.config import settings
from db.utils import get_db
from repositories.api_key_repository import ApiKeyRepository
from repositories.audit_repository import AuditRepository
from repositories.bars_name_repository import BarsNameRepository
from repositories.queue_repository import QueueRepository
from repositories.raw_payload_repository import RawPayloadRepository
from repositories.receipt_repository import ReceiptRepository
from repositories.session_repository import SessionRepository
from repositories.tag_repository import TagRepository
from schemas.auth import AuthContext
from services.api_key_auth_service import ApiKeyAuthService
from services.observability_service import ObservabilityService
from services.parser_service import ParserService
from services.product_matching_service import ProductMatchingService
from services.queue_intake_service import QueueIntakeService
from services.queue_service import QueueService
from services.receipt_image_service import ReceiptImageService
from services.receipt_manual_service import ReceiptManualService
from services.receipt_override_service import ReceiptOverrideService
from services.receipt_unused_service import ReceiptUnusedService
from services.receipt_qr_service import ReceiptQRService
from services.receipt_validation_service import ReceiptValidationService
from services.session_service import SessionService
from services.session_tags_service import SessionTagsService
from services.tag_association_service import TagAssociationService
from services.tag_crud_service import TagCrudService
from services.tag_state_service import TagStateService
from services.tag_usage_service import TagUsageService


async def get_database() -> AsyncIOMotorDatabase:
    return await get_db()


def get_logcenter_sender(request: Request) -> Any | None:
    sender = getattr(request.app.state, "log_sender", None)

    if not sender:
        import logging
        logging.getLogger(__name__).warning("log_sender not found in app.state")

    return sender


def get_observability_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
    log_sender: Any | None = Depends(get_logcenter_sender),
) -> ObservabilityService:
    return ObservabilityService(
        audit_repository=AuditRepository(db),
        log_sender=log_sender,
    )


def get_bars_name_repository(
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> BarsNameRepository:
    return BarsNameRepository(db)


def get_product_matching_service(
    repo: BarsNameRepository = Depends(get_bars_name_repository),
) -> ProductMatchingService:
    return ProductMatchingService(repo)


def get_queue_repository(
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> QueueRepository:
    return QueueRepository(db)


def get_queue_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
    observability_service: ObservabilityService = Depends(get_observability_service),
) -> QueueService:
    return QueueService(
        queue_repository=QueueRepository(db),
        session_repository=SessionRepository(db),
        tag_repository=TagRepository(db),
        observability_service=observability_service,
        mobile_base_url=settings.BASE_URL,
    )


def get_session_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
    queue_service: QueueService = Depends(get_queue_service),
    observability_service: ObservabilityService = Depends(get_observability_service),
) -> SessionService:
    return SessionService(
        session_repository=SessionRepository(db),
        receipt_repository=ReceiptRepository(db),
        observability_service=observability_service,
        queue_service=queue_service,
    )


async def require_auth(
    db: AsyncIOMotorDatabase = Depends(get_database),
    observability_service: ObservabilityService = Depends(get_observability_service),
    api_key: str | None = Header(default=None, alias=settings.API_KEY_HEADER),
    device_id: str | None = Header(default=None, alias=settings.DEVICE_ID_HEADER),
) -> AuthContext:
    auth_service = ApiKeyAuthService(
        ApiKeyRepository(db),
        observability_service,
    )

    if not api_key:
        return await auth_service.authenticate("", device_id)

    return await auth_service.authenticate(api_key, device_id)


def get_receipt_qr_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
    observability_service: ObservabilityService = Depends(get_observability_service),
) -> ReceiptQRService:
    return ReceiptQRService(
        parser_service=ParserService(),
        product_matching_service=ProductMatchingService(BarsNameRepository(db)),
        receipt_validation_service=ReceiptValidationService(ReceiptRepository(db)),
        receipt_repository=ReceiptRepository(db),
        raw_payload_repository=RawPayloadRepository(db),
        observability_service=observability_service,
    )


def get_receipt_image_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
    observability_service: ObservabilityService = Depends(get_observability_service),
) -> ReceiptImageService:
    return ReceiptImageService(
        parser_service=ParserService(),
        product_matching_service=ProductMatchingService(BarsNameRepository(db)),
        receipt_validation_service=ReceiptValidationService(ReceiptRepository(db)),
        receipt_repository=ReceiptRepository(db),
        raw_payload_repository=RawPayloadRepository(db),
        observability_service=observability_service,
    )


def get_receipt_override_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
    observability_service: ObservabilityService = Depends(get_observability_service),
) -> ReceiptOverrideService:
    return ReceiptOverrideService(
        ReceiptRepository(db),
        observability_service,
    )

def get_receipt_unused_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
    observability_service: ObservabilityService = Depends(get_observability_service),
) -> ReceiptUnusedService:
    return ReceiptUnusedService(
        ReceiptRepository(db),
        observability_service,
    )


def get_receipt_manual_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
    observability_service: ObservabilityService = Depends(get_observability_service),
) -> ReceiptManualService:
    return ReceiptManualService(
        receipt_repository=ReceiptRepository(db),
        observability_service=observability_service,
    )


def get_queue_intake_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
    queue_service: QueueService = Depends(get_queue_service),
    observability_service: ObservabilityService = Depends(get_observability_service),
) -> QueueIntakeService:
    return QueueIntakeService(
        receipt_repository=ReceiptRepository(db),
        session_repository=SessionRepository(db),
        queue_repository=QueueRepository(db),
        queue_service=queue_service,
        observability_service=observability_service,
        mobile_base_url=settings.BASE_URL,
    )


def get_tag_association_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
    observability_service: ObservabilityService = Depends(get_observability_service),
) -> TagAssociationService:
    return TagAssociationService(
        session_repository=SessionRepository(db),
        tag_repository=TagRepository(db),
        observability_service=observability_service,
    )


def get_tag_state_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> TagStateService:
    return TagStateService(TagRepository(db))


def get_tag_crud_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
    observability_service: ObservabilityService = Depends(get_observability_service),
) -> TagCrudService:
    return TagCrudService(
        tag_repository=TagRepository(db),
        observability_service=observability_service,
    )


def get_tag_usage_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
    observability_service: ObservabilityService = Depends(get_observability_service),
) -> TagUsageService:
    return TagUsageService(
        tag_repository=TagRepository(db),
        observability_service=observability_service,
    )


def get_session_tags_service(
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> SessionTagsService:
    return SessionTagsService(
        session_repository=SessionRepository(db),
        tag_repository=TagRepository(db),
    )
