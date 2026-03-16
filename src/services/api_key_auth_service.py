from schemas.auth import AuthContext
from core.exceptions import AuthError
from repositories.api_key_repository import ApiKeyRepository
from services.observability_service import ObservabilityService


class ApiKeyAuthService:
    def __init__(self, api_key_repository: ApiKeyRepository, observability_service: ObservabilityService):
        self.api_key_repository = api_key_repository
        self.observability_service = observability_service

    async def authenticate(self, api_key: str, device_id: str | None = None) -> AuthContext:
        api_key_doc = await self.api_key_repository.find_active(api_key)
        if not api_key_doc:
            await self.observability_service.emit(
                "auth-api_key-rejected", {"device_id": device_id}
            )
            raise AuthError()

        await self.api_key_repository.touch(api_key)
        await self.observability_service.emit(
            "auth-api_key-validated",
            {"device_id": device_id, "api_key_id": str(api_key_doc["_id"])}
        )
        return AuthContext(
            api_key_id=str(api_key_doc["_id"]),
            device_id=device_id,
            api_key_name=api_key_doc.get("name"),
        )
