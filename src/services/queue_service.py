from core.exceptions import AppError
from repositories.queue_repository import QueueRepository
from repositories.session_repository import SessionRepository
from repositories.tag_repository import TagRepository
from schemas.queue import (
    QueueCompleteResponse,
    QueueCurrentResponse,
    QueueEntryResponse,
    QueueJoinResponse,
    QueueListResponse,
    QueueMobileViewResponse,
    QueueNextResponse,
    QueueSkipResponse,
    QueueStateResponse,
    QueueValidateResponse,
)
from services.observability_service import ObservabilityService


class QueueService:
    LATE_TOLERANCE = 10

    def __init__(
        self,
        queue_repository: QueueRepository,
        session_repository: SessionRepository,
        tag_repository: TagRepository,
        observability_service: ObservabilityService,
        mobile_base_url: str,
    ):
        self.queue_repository = queue_repository
        self.session_repository = session_repository
        self.tag_repository = tag_repository
        self.observability_service = observability_service
        self.mobile_base_url = mobile_base_url.rstrip("/")

    async def join(self, session_id: str, total_plays: int = 1) -> QueueJoinResponse:
        session = await self.session_repository.find_by_id(session_id)
        if not session:
            raise AppError("Sessão não encontrada", "session_not_found", 404, {"session_id": session_id})

        if not session.get("player_id"):
            raise AppError(
                "A sessão precisa ter player_id antes de entrar na fila",
                "session_missing_player",
                409,
                {"session_id": session_id},
            )

        existing_entry = await self.queue_repository.find_active_by_session_id(session_id)
        if existing_entry:
            people_ahead = await self.queue_repository.count_people_ahead(existing_entry["queue_number"])

            return QueueJoinResponse(
                player_id=str(existing_entry["_id"]),
                session_id=str(existing_entry["session_id"]),
                queue_number=existing_entry["queue_number"],
                status=existing_entry["status"],
                total_plays=existing_entry["total_plays"],
                remaining_plays=existing_entry["remaining_plays"],
                people_ahead=people_ahead,
                created_at=existing_entry["created_at"],
            )

        next_number = await self.queue_repository.get_next_queue_number()
        created = await self.queue_repository.create_entry(
            session_id=session_id,
            queue_number=next_number,
            total_plays=total_plays,
        )
        people_ahead = await self.queue_repository.count_people_ahead(next_number)

        await self.session_repository.set_queue_entry_id(session_id, str(created["_id"]))
        await self.session_repository.update_status(session_id, "queued")

        await self.observability_service.emit(
            "queue-joined",
            {
                "session_id": session_id,
                "player_id": str(created["_id"]),
                "queue_number": next_number,
                "total_plays": total_plays,
            },
        )

        return QueueJoinResponse(
            player_id=str(created["_id"]),
            session_id=str(created["session_id"]),
            queue_number=created["queue_number"],
            status=created["status"],
            total_plays=created["total_plays"],
            remaining_plays=created["remaining_plays"],
            people_ahead=people_ahead,
            created_at=created["created_at"],
        )

    async def get_state(self, player_id: str) -> QueueStateResponse:
        entry = await self.queue_repository.find_by_id(player_id)
        if not entry:
            raise AppError(
                "Entrada da fila não encontrada",
                "queue_entry_not_found",
                404,
                {"player_id": player_id},
            )

        current_queue_number = await self.queue_repository.get_current_queue_number()
        people_ahead = await self.queue_repository.count_people_ahead(entry["queue_number"])

        can_play = False
        if current_queue_number is not None:
            if entry["queue_number"] <= current_queue_number:
                can_play = True
            elif entry["queue_number"] <= current_queue_number + self.LATE_TOLERANCE:
                can_play = True

        return QueueStateResponse(
            player_id=str(entry["_id"]),
            session_id=str(entry["session_id"]),
            queue_number=entry["queue_number"],
            current_queue_number=current_queue_number,
            status=entry["status"],
            people_ahead=people_ahead,
            can_play=can_play,
            total_plays=entry["total_plays"],
            remaining_plays=entry["remaining_plays"],
            requeued_from=entry.get("requeued_from"),
        )

    async def get_current(self) -> QueueCurrentResponse:
        state = await self.queue_repository.get_current_state()
        if not state:
            return QueueCurrentResponse()

        current_player_id = state.get("player_id")
        return QueueCurrentResponse(
            current_queue_number=state.get("queue_number"),
            current_player_id=str(current_player_id) if current_player_id else None,
            current_status=state.get("status"),
        )

    async def next(self) -> QueueNextResponse:
        next_entry = await self.queue_repository.get_next_waiting_entry()
        if not next_entry:
            await self.queue_repository.clear_current_queue_number()
            raise AppError("Não há mais pessoas aguardando na fila", "queue_empty", 404)

        called = await self.queue_repository.mark_called(str(next_entry["_id"]))
        await self.queue_repository.set_current_queue_number(
            queue_number=called["queue_number"],
            player_id=str(called["_id"]),
            status=called["status"],
        )
        await self.session_repository.update_status(str(called["session_id"]), "called")

        waiting = await self.queue_repository.list_waiting_queue()

        await self.observability_service.emit(
            "queue-next-called",
            {
                "player_id": str(called["_id"]),
                "queue_number": called["queue_number"],
            },
        )

        return QueueNextResponse(
            current_queue_number=called["queue_number"],
            player=QueueEntryResponse.model_validate(called),
            people_still_waiting=max(len(waiting) - 1, 0),
        )

    async def validate_for_play(self, player_id: str) -> QueueValidateResponse:
        entry = await self.queue_repository.find_by_id(player_id)
        if not entry:
            raise AppError(
                "Entrada da fila não encontrada",
                "queue_entry_not_found",
                404,
                {"player_id": player_id},
            )

        if entry["status"] == "done":
            raise AppError(
                "Esta entrada da fila já foi concluída",
                "queue_entry_finished",
                409,
                {"player_id": player_id},
            )

        current_queue_number = await self.queue_repository.get_current_queue_number()
        if current_queue_number is None:
            raise AppError("A fila ainda não foi iniciada no tablet", "queue_not_started", 409)

        player_queue_number = entry["queue_number"]

        if player_queue_number <= current_queue_number:
            playing = await self.queue_repository.mark_playing(player_id)
            await self.queue_repository.set_current_queue_number(
                queue_number=playing["queue_number"],
                player_id=str(playing["_id"]),
                status=playing["status"],
            )
            await self.session_repository.update_status(str(playing["session_id"]), "playing")

            await self.observability_service.emit(
                "queue-play-allowed",
                {
                    "player_id": player_id,
                    "queue_number": player_queue_number,
                    "current_queue_number": current_queue_number,
                    "reason": "current_or_older",
                },
            )
            return QueueValidateResponse(
                allowed=True,
                action="play",
                player_id=player_id,
                queue_number=player_queue_number,
                current_queue_number=current_queue_number,
                new_queue_number=None,
                message="Jogador liberado para jogar.",
            )

        if player_queue_number <= current_queue_number + self.LATE_TOLERANCE:
            playing = await self.queue_repository.mark_playing(player_id)
            await self.session_repository.update_status(str(playing["session_id"]), "playing")

            await self.observability_service.emit(
                "queue-play-allowed",
                {
                    "player_id": player_id,
                    "queue_number": player_queue_number,
                    "current_queue_number": current_queue_number,
                    "reason": "late_within_tolerance",
                },
            )
            return QueueValidateResponse(
                allowed=True,
                action="play",
                player_id=player_id,
                queue_number=player_queue_number,
                current_queue_number=current_queue_number,
                new_queue_number=None,
                message="Jogador atrasado, mas ainda dentro da tolerância. Pode jogar.",
            )

        new_queue_number = await self.queue_repository.get_next_queue_number()
        requeued = await self.queue_repository.requeue(
            player_id=player_id,
            new_queue_number=new_queue_number,
            old_queue_number=player_queue_number,
        )
        await self.session_repository.update_status(str(requeued["session_id"]), "queued")

        await self.observability_service.emit(
            "queue-requeued",
            {
                "player_id": player_id,
                "old_queue_number": player_queue_number,
                "new_queue_number": new_queue_number,
                "current_queue_number": current_queue_number,
            },
        )

        return QueueValidateResponse(
            allowed=False,
            action="requeued",
            player_id=player_id,
            queue_number=requeued["queue_number"],
            current_queue_number=current_queue_number,
            new_queue_number=new_queue_number,
            message="Jogador chegou tarde demais e foi movido para o final da fila.",
        )

    async def complete(self, player_id: str) -> QueueCompleteResponse:
        entry = await self.queue_repository.find_by_id(player_id)
        if not entry:
            raise AppError(
                "Entrada da fila não encontrada",
                "queue_entry_not_found",
                404,
                {"player_id": player_id},
            )

        if entry["status"] not in {"playing", "called"}:
            raise AppError(
                "A entrada da fila não está em estado válido para conclusão",
                "queue_invalid_transition",
                409,
                {"player_id": player_id, "status": entry["status"]},
            )

        remaining = await self.queue_repository.decrement_remaining_play(player_id)
        finished = remaining <= 0

        if finished:
            updated = await self.queue_repository.mark_done(player_id, remaining_plays=remaining)
            await self.session_repository.update_status(str(updated["session_id"]), "finished")
        else:
            updated = await self.queue_repository.touch_status(player_id, "done")
            await self.session_repository.update_status(str(updated["session_id"]), "queued")

        await self.observability_service.emit(
            "queue-completed",
            {
                "player_id": player_id,
                "queue_number": updated["queue_number"],
                "remaining_plays": remaining,
                "finished": finished,
            },
        )

        return QueueCompleteResponse(
            player_id=str(updated["_id"]),
            queue_number=updated["queue_number"],
            status=updated["status"],
            remaining_plays=remaining,
            finished=finished,
        )

    async def skip_current(self, reason: str | None = None) -> QueueSkipResponse:
        state = await self.queue_repository.get_current_state()
        if not state or not state.get("player_id"):
            raise AppError("Nenhum jogador atual foi chamado", "queue_no_current_player", 404)

        current_player_id = str(state["player_id"])
        current_entry = await self.queue_repository.find_by_id(current_player_id)
        if not current_entry:
            raise AppError(
                "Entrada da fila não encontrada",
                "queue_entry_not_found",
                404,
                {"player_id": current_player_id},
            )

        skipped = await self.queue_repository.mark_skipped(current_player_id)
        await self.session_repository.update_status(str(skipped["session_id"]), "queued")

        await self.observability_service.emit(
            "queue-skipped",
            {
                "player_id": current_player_id,
                "queue_number": skipped["queue_number"],
                "reason": reason,
            },
        )

        next_player = await self.queue_repository.get_next_waiting_entry()
        if not next_player:
            await self.queue_repository.clear_current_queue_number()
            return QueueSkipResponse(
                skipped_player_id=str(skipped["_id"]),
                skipped_queue_number=skipped["queue_number"],
                next_player=None,
            )

        called = await self.queue_repository.mark_called(str(next_player["_id"]))
        await self.queue_repository.set_current_queue_number(
            queue_number=called["queue_number"],
            player_id=str(called["_id"]),
            status=called["status"],
        )
        await self.session_repository.update_status(str(called["session_id"]), "called")

        return QueueSkipResponse(
            skipped_player_id=str(skipped["_id"]),
            skipped_queue_number=skipped["queue_number"],
            next_player=QueueEntryResponse.model_validate(called),
        )

    async def list_active(self) -> QueueListResponse:
        items = await self.queue_repository.list_active_queue()
        current = await self.queue_repository.get_current_queue_number()
        waiting = await self.queue_repository.list_waiting_queue()

        return QueueListResponse(
            items=[QueueEntryResponse.model_validate(item) for item in items],
            current_queue_number=current,
            total_waiting=len(waiting),
        )

    async def get_mobile_view(self, player_id: str) -> QueueMobileViewResponse:
        entry = await self.queue_repository.find_by_id(player_id)
        if not entry:
            raise AppError(
                "Entrada da fila não encontrada",
                "queue_entry_not_found",
                404,
                {"player_id": player_id},
            )

        current_queue_number = await self.queue_repository.get_current_queue_number()
        people_ahead = await self.queue_repository.count_people_ahead(entry["queue_number"])

        can_play = False
        if current_queue_number is not None:
            if entry["queue_number"] <= current_queue_number:
                can_play = True
            elif entry["queue_number"] <= current_queue_number + self.LATE_TOLERANCE:
                can_play = True

        return QueueMobileViewResponse(
            player_id=str(entry["_id"]),
            session_id=str(entry["session_id"]),
            queue_number=entry["queue_number"],
            current_queue_number=current_queue_number,
            people_ahead=people_ahead,
            can_play=can_play,
            status=entry["status"],
            total_plays=entry["total_plays"],
            remaining_plays=entry["remaining_plays"],
            qr_value=str(entry["_id"]),
            qr_url=f"{self.mobile_base_url}/{str(entry['_id'])}",
        )
