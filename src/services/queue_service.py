import asyncio
import logging

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
    QueueRequeueResponse,
    QueueSkipResponse,
    QueueStateResponse,
    QueueValidateResponse,
)
from services.observability_service import ObservabilityService
from util.sms import (
    send_queue_fifth_position_sms,
    send_queue_next_up_sms,
    send_queue_registration_sms,
)


logger = logging.getLogger(__name__)


class QueueService:
    _next_lock: asyncio.Semaphore | None = None
    _skip_lock: asyncio.Semaphore | None = None

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

    async def _send_registration_sms_if_possible(self, session: dict, queue_entry: dict, qr_code_url: str | None = None) -> bool:
        phone = session.get("phone")
        if not phone:
            return False

        if queue_entry.get("registration_sms_sent_at"):
            return False

        sent = send_queue_registration_sms(
            destination_number=phone,
            queue_number=queue_entry["queue_number"],
            qr_code_url=qr_code_url,
        )
        if sent:
            await self.queue_repository.mark_registration_sms_sent(str(queue_entry["_id"]))
            return True

        logger.warning(
            "queue.sms_registration_failed",
            extra={
                "session_id": str(session["_id"]),
                "player_id": str(queue_entry["_id"]),
                "queue_number": queue_entry["queue_number"],
            },
        )
        return False

    async def send_registration_sms_for_session(self, session_id: str, qr_code_url: str | None = None) -> dict:
        session = await self.session_repository.find_by_id(session_id)
        if not session:
            raise AppError(
                "Sessão não encontrada",
                "session_not_found",
                404,
                {"session_id": session_id},
            )

        queue_entry = await self.queue_repository.find_active_by_session_id(session_id)
        if not queue_entry:
            raise AppError(
                "Sessão não possui entrada ativa na fila",
                "queue_entry_not_found_for_session",
                404,
                {"session_id": session_id},
            )

        sms_sent = await self._send_registration_sms_if_possible(session, queue_entry, qr_code_url=qr_code_url)

        people_ahead = await self.queue_repository.count_people_ahead(queue_entry["queue_number"])

        return {
            "session_id": str(session["_id"]),
            "player_id": str(queue_entry["_id"]),
            "queue_number": queue_entry["queue_number"],
            "people_ahead": people_ahead,
            "phone": session.get("phone"),
            "sms_sent": sms_sent,
        }

    async def _send_fifth_position_sms_if_needed(self) -> None:
        waiting_entries = await self.queue_repository.list_waiting_queue()

        for item in waiting_entries:
            if item.get("fifth_position_sms_sent_at"):
                continue

            people_ahead = await self.queue_repository.count_people_ahead(item["queue_number"])
            if people_ahead != 4:
                continue

            session = await self.session_repository.find_by_id(str(item["session_id"]))
            if not session or not session.get("phone"):
                continue

            sent = send_queue_fifth_position_sms(
                destination_number=session["phone"],
                queue_number=item["queue_number"],
            )
            if sent:
                await self.queue_repository.mark_fifth_position_sms_sent(str(item["_id"]))
            else:
                logger.warning(
                    "queue.sms_fifth_position_failed",
                    extra={
                        "session_id": str(item["session_id"]),
                        "player_id": str(item["_id"]),
                        "queue_number": item["queue_number"],
                    },
                )

    async def _send_next_up_sms_if_needed(self) -> None:
        next_after_called = await self.queue_repository.get_next_waiting_entry()
        if not next_after_called:
            return

        if next_after_called.get("next_up_sms_sent_at"):
            return

        session = await self.session_repository.find_by_id(str(next_after_called["session_id"]))
        if not session or not session.get("phone"):
            return

        sent = send_queue_next_up_sms(
            destination_number=session["phone"],
            queue_number=next_after_called["queue_number"],
        )
        if sent:
            await self.queue_repository.mark_next_up_sms_sent(str(next_after_called["_id"]))
        else:
            logger.warning(
                "queue.sms_next_up_failed",
                extra={
                    "session_id": str(next_after_called["session_id"]),
                    "player_id": str(next_after_called["_id"]),
                    "queue_number": next_after_called["queue_number"],
                },
            )

    async def join(self, session_id: str, total_plays: int = 1) -> QueueJoinResponse:
        session = await self.session_repository.find_by_id(session_id)
        if not session:
            raise AppError(
                "Sessão não encontrada",
                "session_not_found",
                404,
                {"session_id": session_id},
            )

        if not session.get("player_id"):
            raise AppError(
                "A sessão precisa ter player_id antes de entrar na fila",
                "session_missing_player",
                409,
                {"session_id": session_id},
            )

        session_total_plays = int(session.get("total_plays", 1))
        effective_total_plays = session_total_plays

        if total_plays and total_plays != session_total_plays:
            raise AppError(
                "total_plays da fila difere do total_plays da sessão",
                "queue_total_plays_mismatch",
                409,
                {
                    "session_id": session_id,
                    "session_total_plays": session_total_plays,
                    "requested_total_plays": total_plays,
                },
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
            total_plays=effective_total_plays,
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
                "total_plays": effective_total_plays,
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

        is_current_player = current_queue_number is not None and entry["queue_number"] == current_queue_number
        can_play = is_current_player or bool(entry.get("late_play_allowed"))

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
        if QueueService._next_lock is None:
            QueueService._next_lock = asyncio.Semaphore(1)

        async with QueueService._next_lock:
            current_state = await self.queue_repository.get_current_state()
            current_queue_number = current_state.get("queue_number") if current_state else None
            if current_queue_number is not None:
                current_entry = await self.queue_repository.find_by_queue_number(current_queue_number)
                if current_entry and current_entry["status"] in {"called", "playing"}:
                    current_player_id = current_state.get("player_id") if current_state else None
                    current_player = (
                        await self.queue_repository.find_by_id(str(current_player_id))
                        if current_player_id else None
                    )
                    waiting = await self.queue_repository.list_waiting_queue()
                    return QueueNextResponse(
                        current_queue_number=current_queue_number,
                        player=QueueEntryResponse.model_validate(current_player or current_entry),
                        people_still_waiting=max(len(waiting) - 1, 0),
                    )

            called = await self.queue_repository.get_and_mark_called()
            if not called:
                await self.queue_repository.clear_current_queue_number()
                raise AppError(
                    "Não há mais pessoas aguardando na fila",
                    "queue_empty",
                    404,
                )

            await self.queue_repository.clear_late_play_allowed(str(called["_id"]))
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

            await self._send_fifth_position_sms_if_needed()
            await self._send_next_up_sms_if_needed()

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
        player_queue_number = entry["queue_number"]
        is_late_allowed = bool(entry.get("late_play_allowed"))

        if current_queue_number is None:
            if not is_late_allowed:
                raise AppError(
                    "A fila ainda não foi iniciada no tablet",
                    "queue_not_started",
                    409,
                )
        else:
            is_current_player = player_queue_number == current_queue_number

            if not is_current_player and not is_late_allowed:
                raise AppError(
                    "Ainda não é a vez deste jogador",
                    "queue_not_current_player",
                    409,
                    {
                        "player_id": player_id,
                        "queue_number": player_queue_number,
                        "current_queue_number": current_queue_number,
                    },
                )

        playing = await self.queue_repository.mark_playing(player_id)
        if current_queue_number is None or is_current_player:
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
                "reason": (
                    "late_play_allowed_without_current"
                    if current_queue_number is None and is_late_allowed
                    else "current_player"
                    if current_queue_number is not None and player_queue_number == current_queue_number
                    else "late_play_allowed"
                ),
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

    async def mark_preferential(self, player_id: str) -> dict:
        entry = await self.queue_repository.find_by_id(player_id)
        if not entry:
            raise AppError(
                "Entrada da fila não encontrada",
                "queue_entry_not_found",
                404,
                {"player_id": player_id},
            )

        updated = await self.queue_repository.allow_late_play(player_id)
        
        await self.observability_service.emit(
            "queue-marked-preferential",
            {
                "player_id": player_id,
                "queue_number": updated["queue_number"],
            },
        )
        
        return {
            "player_id": str(updated["_id"]),
            "queue_number": updated["queue_number"],
            "status": updated["status"],
            "message": "Jogador marcado como preferencial com sucesso."
        }

    async def play(self, player_id: str, tag_key: str) -> dict:
        entry = await self.queue_repository.find_by_id(player_id)
        if not entry:
            raise AppError(
                "Entrada da fila não encontrada",
                "queue_entry_not_found",
                404,
                {"player_id": player_id},
            )

        if entry["status"] in {"done"}:
            raise AppError(
                "A entrada da fila não está em estado jogável",
                "queue_entry_not_playable",
                409,
                {"player_id": player_id, "status": entry["status"]},
            )

        if int(entry.get("remaining_plays", 0)) <= 0:
            raise AppError(
                "Não há mais jogadas restantes para esta entrada da fila",
                "queue_no_remaining_plays",
                409,
                {"player_id": player_id},
            )

        current_queue_number = await self.queue_repository.get_current_queue_number()
        player_queue_number = entry["queue_number"]
        is_late_allowed = bool(entry.get("late_play_allowed"))

        if current_queue_number is None:
            if not is_late_allowed:
                raise AppError(
                    "A fila ainda não foi iniciada no tablet",
                    "queue_not_started",
                    409,
                )
        else:
            is_current_player = player_queue_number == current_queue_number

            if not is_current_player and not is_late_allowed:
                raise AppError(
                    "Ainda não é a vez deste jogador",
                    "queue_not_current_player",
                    409,
                    {
                        "player_id": player_id,
                        "queue_number": player_queue_number,
                        "current_queue_number": current_queue_number,
                    },
                )

        if entry["status"] != "playing" and entry["status"] != "skipped" :
            entry = await self.queue_repository.mark_playing(player_id)
            await self.session_repository.update_status(str(entry["session_id"]), "playing")
            if current_queue_number is None or is_current_player:
                await self.queue_repository.set_current_queue_number(
                    queue_number=entry["queue_number"],
                    player_id=str(entry["_id"]),
                    status=entry["status"],
                )

        tag = await self.tag_repository.find_by_key(tag_key)
        if not tag:
            raise AppError(
                "Tag não encontrada",
                "tag_not_found",
                404,
                {"tag_key": tag_key},
            )

        tag_session_id = tag.get("session_id")
        if not tag_session_id or str(tag_session_id) != str(entry["session_id"]):
            raise AppError(
                "A tag não pertence à sessão da fila",
                "tag_not_belongs_to_session",
                409,
                {
                    "tag_key": tag_key,
                    "queue_session_id": str(entry["session_id"]),
                    "tag_session_id": str(tag_session_id) if tag_session_id else None,
                },
            )

        tag_status = tag.get("status")
        if tag_status != "valid":
            raise AppError(
                "A tag não está válida para jogar",
                "tag_invalid_state",
                409,
                {"tag_key": tag_key, "status": tag_status},
            )

        updated_tag = await self.tag_repository.mark_used(tag_key)
        if not updated_tag:
            raise AppError(
                "Não foi possível consumir a tag",
                "tag_use_failed",
                500,
                {"tag_key": tag_key},
            )

        remaining = await self.queue_repository.decrement_remaining_play(player_id)
        finished = remaining <= 0

        if finished:
            updated_entry = await self.queue_repository.mark_done(
                player_id=player_id,
                remaining_plays=remaining,
            )
            await self.session_repository.update_status(str(updated_entry["session_id"]), "finished")
            await self.queue_repository.clear_late_play_allowed(player_id)
        else:
            updated_entry = await self.queue_repository.touch_status(player_id, "playing")
            await self.session_repository.update_status(str(updated_entry["session_id"]), "playing")

        await self.observability_service.emit(
            "queue-play-consumed",
            {
                "player_id": player_id,
                "session_id": str(updated_entry["session_id"]),
                "queue_number": updated_entry["queue_number"],
                "tag_key": tag_key,
                "tag_result_status": updated_tag.get("status"),
                "remaining_plays": remaining,
                "finished": finished,
            },
        )

        return {
            "allowed": True,
            "action": "played",
            "player_id": str(updated_entry["_id"]),
            "session_id": str(updated_entry["session_id"]),
            "queue_number": updated_entry["queue_number"],
            "current_queue_number": current_queue_number,
            "tag_key": tag_key,
            "tag_status": updated_tag.get("status"),
            "remaining_plays": remaining,
            "finished": finished,
            "message": "Jogada consumida com sucesso.",
        }

    async def requeue(self, player_id: str) -> QueueRequeueResponse:
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

        old_queue_number = entry["queue_number"]
        new_queue_number = await self.queue_repository.get_next_queue_number()

        requeued = await self.queue_repository.requeue(
            player_id=player_id,
            new_queue_number=new_queue_number,
            old_queue_number=old_queue_number,
        )
        await self.session_repository.update_status(str(requeued["session_id"]), "queued")

        current_state = await self.queue_repository.get_current_state()
        if current_state and current_state.get("player_id") and str(current_state["player_id"]) == player_id:
            called = await self.queue_repository.get_and_mark_called()
            if called:
                await self.queue_repository.clear_late_play_allowed(str(called["_id"]))
                await self.queue_repository.set_current_queue_number(
                    queue_number=called["queue_number"],
                    player_id=str(called["_id"]),
                    status=called["status"],
                )
                await self.session_repository.update_status(str(called["session_id"]), "called")
                await self._send_fifth_position_sms_if_needed()
                await self._send_next_up_sms_if_needed()
            else:
                await self.queue_repository.clear_current_queue_number()

        await self.observability_service.emit(
            "queue-requeued-manually",
            {
                "player_id": player_id,
                "old_queue_number": old_queue_number,
                "new_queue_number": new_queue_number,
            },
        )

        return QueueRequeueResponse(
            player_id=str(requeued["_id"]),
            old_queue_number=old_queue_number,
            new_queue_number=requeued["queue_number"],
            status=requeued["status"],
            message="Jogador movido para o fim da fila com sucesso.",
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

        await self.queue_repository.update_one_force_finish(player_id)
        updated = await self.queue_repository.find_by_id(player_id)
        await self.session_repository.update_status(str(updated["session_id"]), "finished")
        await self.queue_repository.clear_late_play_allowed(player_id)

        await self.observability_service.emit(
            "queue-force-completed",
            {
                "player_id": player_id,
                "queue_number": updated["queue_number"],
            },
        )

        return QueueCompleteResponse(
            player_id=str(updated["_id"]),
            queue_number=updated["queue_number"],
            status=updated["status"],
            remaining_plays=updated["remaining_plays"],
            finished=True,
        )

    async def skip_current(self, reason: str | None = None) -> QueueSkipResponse:
        if QueueService._skip_lock is None:
            QueueService._skip_lock = asyncio.Semaphore(1)

        async with QueueService._skip_lock:
            return await self._skip_current(reason)

    async def _skip_current(self, reason: str | None = None) -> QueueSkipResponse:
        state = await self.queue_repository.get_current_state()
        if not state or not state.get("player_id"):
            raise AppError(
                "Nenhum jogador atual foi chamado",
                "queue_no_current_player",
                404,
            )

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

        called = await self.queue_repository.get_and_mark_called()
        if not called:
            await self.queue_repository.clear_current_queue_number()
            return QueueSkipResponse(
                skipped_player_id=str(skipped["_id"]),
                skipped_queue_number=skipped["queue_number"],
                next_player=None,
            )

        await self.queue_repository.clear_late_play_allowed(str(called["_id"]))
        await self.queue_repository.set_current_queue_number(
            queue_number=called["queue_number"],
            player_id=str(called["_id"]),
            status=called["status"],
        )
        await self.session_repository.update_status(str(called["session_id"]), "called")

        await self._send_fifth_position_sms_if_needed()
        await self._send_next_up_sms_if_needed()

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

        is_current_player = current_queue_number is not None and entry["queue_number"] == current_queue_number
        can_play = is_current_player or bool(entry.get("late_play_allowed"))

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
