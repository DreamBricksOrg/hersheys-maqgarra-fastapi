import argparse
import asyncio
from datetime import datetime, timezone
from bson import ObjectId

from motor.motor_asyncio import AsyncIOMotorClient

from src.core.config import settings
from logcenter_sdk.config import LogCenterConfig
from logcenter_sdk.sender import LogCenterSender


DEFAULT_START = "2026-03-22T00:00:00+00:00"


def to_logcenter_safe(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): to_logcenter_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_logcenter_safe(v) for v in value]
    if isinstance(value, tuple):
        return [to_logcenter_safe(v) for v in value]
    return value


def parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill de audit_events para o LogCenter."
    )
    parser.add_argument(
        "--start",
        default=DEFAULT_START,
        help="Data inicial ISO-8601. Ex: 2026-03-22T00:00:00+00:00",
    )
    parser.add_argument(
        "--end",
        default=None,
        help="Data final ISO-8601. Ex: 2026-03-23T23:59:59+00:00",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limite de documentos para teste.",
    )
    args = parser.parse_args()

    start_dt = parse_dt(args.start)
    end_dt = parse_dt(args.end) if args.end else datetime.now(timezone.utc)

    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    collection = db.audit_events

    cfg = LogCenterConfig(
        base_url=(settings.LOG_API or "").rstrip("/"),
        project_id=settings.LOG_PROJECT_ID,
        api_key=settings.LOG_API_KEY,
        enabled=True,
    )
    sender = LogCenterSender(cfg)

    query = {
        "created_at": {
            "$gte": start_dt,
            "$lte": end_dt,
        },
        "logcenter_backfilled_at": {"$exists": False},
    }

    cursor = collection.find(query).sort("created_at", 1)

    if args.limit:
        cursor = cursor.limit(args.limit)

    total_found = await collection.count_documents(query)
    sent_count = 0
    error_count = 0

    print(
        f"Iniciando backfill de audit_events | start={start_dt.isoformat()} "
        f"| end={end_dt.isoformat()} | encontrados={total_found}"
    )

    async for doc in cursor:
        event = doc.get("event", "audit-event")
        payload = to_logcenter_safe(doc.get("payload", {}))
        created_at = to_logcenter_safe(doc.get("created_at"))
        audit_id = str(doc["_id"])

        try:
            await sender.send(
                timestamp=created_at,
                level="INFO",
                message=event,
                status="ok",
                tags=["audit-events-backfill", event],
                data={
                    "source": "audit_events",
                    "audit_event_id": audit_id,
                    "payload": payload,
                    "created_at": created_at,
                },
                spool_on_fail=True,
            )

            await collection.update_one(
                {"_id": audit_id},
                {
                    "$set": {
                        "logcenter_backfilled_at": datetime.now(timezone.utc),
                    }
                },
            )

            sent_count += 1

            if sent_count % 100 == 0:
                print(f"{sent_count} eventos enviados...")
        except Exception as exc:
            error_count += 1
            print(f"Erro ao enviar audit_event {audit_id}: {exc}")

    try:
        await sender.stop_background_flush()
    finally:
        client.close()

    print(
        f"Backfill concluído | enviados={sent_count} | erros={error_count} "
        f"| janela={start_dt.isoformat()}..{end_dt.isoformat()}"
    )


if __name__ == "__main__":
    asyncio.run(main())
