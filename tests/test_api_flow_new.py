from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

import requests
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


BASE_URL = os.getenv("CAPIGARRA_BASE_URL", "http://localhost:8000").rstrip("/")
MONGO_URI = os.getenv("CAPIGARRA_MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("CAPIGARRA_DB_NAME", "hersheys_capigarra")
API_KEY = os.getenv("CAPIGARRA_API_KEY", "dev-api-key")
DEVICE_ID = os.getenv("CAPIGARRA_DEVICE_ID", "capigarra-test-runner")

TIMEOUT = int(os.getenv("CAPIGARRA_HTTP_TIMEOUT", "20"))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def headers() -> dict[str, str]:
    return {
        "x-api-key": API_KEY,
        "x-device-id": DEVICE_ID,
        "content-type": "application/json",
    }


class TestFailure(Exception):
    pass


def log(title: str, payload: Any | None = None) -> None:
    print(f"\n=== {title} ===")
    if payload is not None:
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))


def assert_status(response: requests.Response, expected: int) -> dict[str, Any]:
    try:
        data = response.json()
    except Exception:
        data = {"raw": response.text}

    if response.status_code != expected:
        raise TestFailure(
            f"Esperado status {expected}, mas veio {response.status_code}\n"
            f"URL: {response.request.method} {response.request.url}\n"
            f"Resposta: {json.dumps(data, indent=2, ensure_ascii=False, default=str)}"
        )
    return data


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise TestFailure(message)


def api_post(
    path: str,
    payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    response = requests.post(
        url,
        headers=headers(),
        json=payload,
        params=params,
        timeout=TIMEOUT,
    )
    return assert_status(response, 200 if path not in {"/api/sessions", "/api/tags"} else 201)


def api_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    response = requests.get(
        url,
        headers=headers(),
        params=params,
        timeout=TIMEOUT,
    )
    return assert_status(response, 200)


def api_post_expect(
    path: str,
    expected_status: int,
    payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    response = requests.post(
        url,
        headers=headers(),
        json=payload,
        params=params,
        timeout=TIMEOUT,
    )
    return assert_status(response, expected_status)


def api_get_expect(
    path: str,
    expected_status: int,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    response = requests.get(
        url,
        headers=headers(),
        params=params,
        timeout=TIMEOUT,
    )
    return assert_status(response, expected_status)


def get_db() -> tuple[AsyncIOMotorClient, AsyncIOMotorDatabase]:
    client = AsyncIOMotorClient(MONGO_URI)
    return client, client[DB_NAME]


async def seed_receipt(db: AsyncIOMotorDatabase, status: str = "valid") -> str:
    doc = {
        "_id": ObjectId(),
        "receipt_key": f"FAKE-{ObjectId()}",
        "source": "manual",
        "found_bars": 1,
        "final_bars": 1,
        "review": False,
        "status": status,
        "items": [],
        "raw_payload": {"test_seed": True},
        "session_id": None,
        "created_at": utc_now(),
        "last_updated_at": utc_now(),
    }
    await db.receipts.insert_one(doc)
    return str(doc["_id"])


async def seed_physical_tag(
    db: AsyncIOMotorDatabase,
    tag_key: str,
    status: str = "available",
) -> str:
    existing = await db.tags.find_one({"tag_key": tag_key})

    if existing:
        await db.tags.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "delivery_mode": "physical",
                    "status": status,
                    "session_id": None,
                    "last_updated_at": utc_now(),
                    "used_at": None,
                    "invalid_reason": None,
                }
            },
        )
        return str(existing["_id"])

    doc = {
        "_id": ObjectId(),
        "tag_key": tag_key,
        "delivery_mode": "physical",
        "status": status,
        "session_id": None,
        "last_updated_at": utc_now(),
        "used_at": None,
        "invalid_reason": None,
    }
    await db.tags.insert_one(doc)
    return str(doc["_id"])


def create_fake_player_id() -> str:
    return str(ObjectId())


async def run_digital_flow(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    receipt_id = await seed_receipt(db, "valid")
    player_id = create_fake_player_id()

    create_session_payload = {
        "receipt_ids": [receipt_id],
        "player_id": player_id,
        "phone": "5511999999999",
    }
    session = api_post("/api/sessions", create_session_payload)
    session_id = session["session_id"]

    joined = api_post("/api/queue/join", {"session_id": session_id, "total_plays": 1})
    queue_player_id = joined["player_id"]

    generated_tag = api_post("/api/tags/generate", {"session_id": session_id, "delivery_mode": "digital"})
    mobile_before = api_get(f"/api/queue/mobile/{queue_player_id}")
    current_before = api_get("/api/queue/current")

    next_called = api_post("/api/queue/next", {})
    validate = api_post("/api/queue/validate", params={"player_id": queue_player_id})
    complete = api_post("/api/queue/complete", params={"player_id": queue_player_id})
    used_tag = api_post("/api/tags/use", {"tag_key": generated_tag["tag_key"]})
    mobile_after = api_get(f"/api/queue/mobile/{queue_player_id}")
    session_after = api_get(f"/api/sessions/{session_id}")

    assert_true(session["status"] == "created", "Session deveria iniciar como created")
    assert_true(joined["status"] in {"waiting", "requeued", "called", "playing"}, "Join retornou status inesperado")
    assert_true(generated_tag["delivery_mode"] == "digital", "Tag digital deveria ter delivery_mode=digital")
    assert_true(generated_tag["status"] == "valid", "Tag digital recém-criada deveria estar valid")
    assert_true(mobile_before["player_id"] == queue_player_id, "Mobile view deveria retornar a queue entry")
    assert_true(validate["allowed"] is True, "Jogador digital deveria estar liberado para jogar após next")
    assert_true(used_tag["status"] == "used", "Tag digital usada deveria virar used")
    assert_true(session_after["status"] == "finished", "Sessão digital deveria terminar como finished")
    assert_true(session_after["queue_entry_id"] == queue_player_id, "queue_entry_id deveria estar salvo na session")

    return {
        "receipt_id": receipt_id,
        "player_id": player_id,
        "session": session,
        "join_queue": joined,
        "generated_tag": generated_tag,
        "mobile_before": mobile_before,
        "current_before": current_before,
        "next_called": next_called,
        "validate": validate,
        "complete": complete,
        "used_tag": used_tag,
        "mobile_after": mobile_after,
        "session_after": session_after,
    }


async def run_physical_flow(db: AsyncIOMotorDatabase) -> dict[str, Any]:
    receipt_id = await seed_receipt(db, "valid")
    player_id = create_fake_player_id()

    await seed_physical_tag(db, "T1284", "available")
    await seed_physical_tag(db, "T2309", "available")

    session = api_post(
        "/api/sessions",
        {
            "receipt_ids": [receipt_id],
            "player_id": player_id,
            "phone": None,
        },
    )
    session_id = session["session_id"]

    joined = api_post("/api/queue/join", {"session_id": session_id, "total_plays": 1})
    queue_player_id = joined["player_id"]

    associated_tag = api_post("/api/tags/associate", {"session_id": session_id, "delivery_mode": "physical"})
    mobile_before = api_get(f"/api/queue/mobile/{queue_player_id}")
    next_called = api_post("/api/queue/next", {})
    validate = api_post("/api/queue/validate", params={"player_id": queue_player_id})
    complete = api_post("/api/queue/complete", params={"player_id": queue_player_id})
    used_tag = api_post("/api/tags/use", {"tag_key": associated_tag["tag"]["tag_key"]})
    session_after = api_get(f"/api/sessions/{session_id}")

    assert_true(associated_tag["tag"]["delivery_mode"] == "physical", "Tag física deveria ter delivery_mode=physical")
    assert_true(associated_tag["tag"]["status"] == "valid", "Tag física associada deveria estar valid")
    assert_true(validate["allowed"] is True, "Jogador físico deveria estar liberado para jogar após next")
    assert_true(used_tag["status"] == "available", "Tag física usada deveria voltar para available")
    assert_true(used_tag["session_id"] is None, "Tag física usada deveria limpar session_id")
    assert_true(session_after["status"] == "finished", "Sessão física deveria terminar como finished")

    return {
        "receipt_id": receipt_id,
        "player_id": player_id,
        "session": session,
        "join_queue": joined,
        "associated_tag": associated_tag,
        "mobile_before": mobile_before,
        "next_called": next_called,
        "validate": validate,
        "complete": complete,
        "used_tag": used_tag,
        "session_after": session_after,
    }


async def run_negative_checks(db: AsyncIOMotorDatabase) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    receipt_id = await seed_receipt(db, "valid")
    player_id = create_fake_player_id()
    await seed_physical_tag(db, "T9998", "available")

    session = api_post("/api/sessions", {"receipt_ids": [receipt_id], "player_id": player_id})
    session_id = session["session_id"]

    first_tag = api_post("/api/tags/generate", {"session_id": session_id, "delivery_mode": "digital"})

    second_attempt = requests.post(
        f"{BASE_URL}/api/tags/associate",
        headers=headers(),
        json={"session_id": session_id, "delivery_mode": "physical", "tag_key": "T9998"},
        timeout=TIMEOUT,
    )
    second_data = assert_status(second_attempt, 409)
    results.append(
        {
            "name": "block_multiple_valid_tags_per_session",
            "first_tag_key": first_tag["tag_key"],
            "response": second_data,
        }
    )

    reuse_attempt = requests.post(
        f"{BASE_URL}/api/sessions",
        headers=headers(),
        json={"receipt_ids": [receipt_id], "player_id": create_fake_player_id()},
        timeout=TIMEOUT,
    )
    reuse_data = assert_status(reuse_attempt, 409)
    results.append(
        {
            "name": "block_receipt_already_attached",
            "response": reuse_data,
        }
    )

    return results


async def async_main() -> int:
    log(
        "Configuração",
        {
            "base_url": BASE_URL,
            "mongo_uri": MONGO_URI,
            "db_name": DB_NAME,
            "device_id": DEVICE_ID,
        },
    )

    client, db = get_db()

    try:
        digital = await run_digital_flow(db)
        log("Fluxo digital OK", digital)

        physical = await run_physical_flow(db)
        log("Fluxo físico OK", physical)

        negative = await run_negative_checks(db)
        log("Validações negativas OK", negative)

        summary = {
            "result": "success",
            "digital_session_id": digital["session"]["session_id"],
            "physical_session_id": physical["session"]["session_id"],
            "digital_tag_key": digital["generated_tag"]["tag_key"],
            "physical_tag_key": physical["associated_tag"]["tag"]["tag_key"],
            "negative_checks": [item["name"] for item in negative],
        }
        log("Resumo final", summary)
        print("\nTeste concluído com sucesso.")
        return 0

    except TestFailure as exc:
        print("\nFALHA NO TESTE:")
        print(str(exc))
        return 1

    except requests.RequestException as exc:
        print("\nERRO HTTP:")
        print(str(exc))
        return 1

    except Exception as exc:
        print("\nERRO INESPERADO:")
        print(repr(exc))
        return 1

    finally:
        client.close()


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    sys.exit(main())