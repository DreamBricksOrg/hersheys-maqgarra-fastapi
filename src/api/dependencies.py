from fastapi import Depends, Header
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.config import settings
from db.utils import get_db
from repositories.api_key_repository import ApiKeyRepository
from repositories.audit_repository import AuditRepository
from repositories.queue_repository import QueueRepository
from repositories.bars_name_repository import BarsNameRepository
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
from services.receipt_qr_service import ReceiptQRService
from services.receipt_validation_service import ReceiptValidationService
from services.session_tags_service import SessionTagsService
from services.tag_association_service import TagAssociationService
from services.tag_crud_service import TagCrudService
from services.tag_state_service import TagStateService
from services.tag_usage_service import TagUsageService


async def get_database() -> AsyncIOMotorDatabase:
    return await get_db()


def get_observability_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> ObservabilityService:
    return ObservabilityService(AuditRepository(db))


def get_bars_name_repository(db: AsyncIOMotorDatabase = Depends(get_database)) -> BarsNameRepository:
    return BarsNameRepository(db)


def get_product_matching_service(
    repo: BarsNameRepository = Depends(get_bars_name_repository),
) -> ProductMatchingService:
    return ProductMatchingService(repo)


async def require_auth(
    db: AsyncIOMotorDatabase = Depends(get_database),
    api_key: str | None = Header(default=None, alias=settings.API_KEY_HEADER),
    device_id: str | None = Header(default=None, alias=settings.DEVICE_ID_HEADER),
) -> AuthContext:
    auth_service = ApiKeyAuthService(ApiKeyRepository(db), ObservabilityService(AuditRepository(db)))
    if not api_key:
        return await auth_service.authenticate("", device_id)
    return await auth_service.authenticate(api_key, device_id)


def get_receipt_qr_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> ReceiptQRService:
    observability = ObservabilityService(AuditRepository(db))
    return ReceiptQRService(
        parser_service=ParserService(),
        product_matching_service=ProductMatchingService(BarsNameRepository(db)),
        receipt_validation_service=ReceiptValidationService(ReceiptRepository(db)),
        receipt_repository=ReceiptRepository(db),
        raw_payload_repository=RawPayloadRepository(db),
        observability_service=observability,
    )


def get_receipt_image_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> ReceiptImageService:
    observability = ObservabilityService(AuditRepository(db))
    return ReceiptImageService(
        parser_service=ParserService(),
        product_matching_service=ProductMatchingService(BarsNameRepository(db)),
        receipt_validation_service=ReceiptValidationService(ReceiptRepository(db)),
        receipt_repository=ReceiptRepository(db),
        raw_payload_repository=RawPayloadRepository(db),
        observability_service=observability,
    )


def get_receipt_override_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> ReceiptOverrideService:
    return ReceiptOverrideService(
        ReceiptRepository(db),
        ObservabilityService(AuditRepository(db)),
    )


def get_queue_repository(db: AsyncIOMotorDatabase = Depends(get_database)) -> QueueRepository:
    return QueueRepository(db)


def get_queue_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> QueueService:
    return QueueService(
        queue_repository=QueueRepository(db),
        session_repository=SessionRepository(db),
        observability_service=ObservabilityService(AuditRepository(db)),
    )


def get_queue_intake_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> QueueIntakeService:
    return QueueIntakeService(
        receipt_repository=ReceiptRepository(db),
        session_repository=SessionRepository(db),
        queue_repository=QueueRepository(db),
        queue_service=QueueService(
            queue_repository=QueueRepository(db),
            session_repository=SessionRepository(db),
            observability_service=ObservabilityService(AuditRepository(db)),
        ),
        observability_service=ObservabilityService(AuditRepository(db)),
        mobile_base_url=settings.BASE_URL,
    )


def get_receipt_manual_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> ReceiptManualService:
    return ReceiptManualService(
        receipt_repository=ReceiptRepository(db),
        observability_service=ObservabilityService(AuditRepository(db)),
    )


def get_tag_association_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> TagAssociationService:
    return TagAssociationService(
        session_repository=SessionRepository(db),
        tag_repository=TagRepository(db),
        observability_service=ObservabilityService(AuditRepository(db)),
    )


def get_tag_state_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> TagStateService:
    return TagStateService(TagRepository(db))


def get_tag_crud_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> TagCrudService:
    return TagCrudService(
        tag_repository=TagRepository(db),
        observability_service=ObservabilityService(AuditRepository(db)),
    )


def get_tag_usage_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> TagUsageService:
    return TagUsageService(
        tag_repository=TagRepository(db),
        observability_service=ObservabilityService(AuditRepository(db)),
    )


def get_session_tags_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> SessionTagsService:
    return SessionTagsService(
        session_repository=SessionRepository(db),
        tag_repository=TagRepository(db),
    )
