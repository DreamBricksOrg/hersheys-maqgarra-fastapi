from core.exceptions import AppError
from repositories.session_repository import SessionRepository
from repositories.tag_repository import TagRepository
from schemas.tags import SessionTagsResponse, TagResponse, SessionWithTagResponse


class SessionTagsService:
    def __init__(
        self,
        session_repository: SessionRepository,
        tag_repository: TagRepository,
    ):
        self.session_repository = session_repository
        self.tag_repository = tag_repository

    async def get_tags(self, session_id: str) -> SessionTagsResponse:
        session = await self.session_repository.find_by_id(session_id)
        if not session:
            raise AppError(
                "Sessão não encontrada",
                "session_not_found",
                404,
                {"session_id": session_id},
            )

        tags = await self.tag_repository.find_by_session_id(session_id)

        return SessionTagsResponse(
            session_id=session_id,
            tags=[TagResponse.model_validate(item) for item in tags],
        )

    async def get_session_with_tags(self, tag_key: str) -> SessionWithTagResponse:
        tags = await self.tag_repository.find_by_key(tag_key)
        if not tags:
            raise AppError(
                "Tag não encontrada",
                "tag_not_found",
                404,
                {"tag_key": tag_key},
            )
        if tags["session_id"] is None:
            raise AppError(
                "Tag não possui sessão",
                "tag_does_not_have_session",
                409,
                {"tag_key": tag_key},
            )
        return SessionWithTagResponse(
            session_id=tags["session_id"]
        )
