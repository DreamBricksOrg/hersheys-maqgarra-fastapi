#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

import requests
from bson import ObjectId
from pymongo import MongoClient


BASE_URL = os.getenv("CAPIGARRA_BASE_URL", "http://localhost:8000").rstrip("/")
MONGO_URI = os.getenv("CAPIGARRA_MONGO_DIRECT_URI") or os.getenv(
    "CAPIGARRA_MONGO_URI", "mongodb://localhost:27017"
)
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


def api_post(path: str, payload: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    response = requests.post(url, headers=headers(), json=payload, params=params, timeout=TIMEOUT)
    expected = 201 if path == "/api/sessions" else 200
    return assert_status(response, expected)


def api_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    response = requests.get(url, headers=headers(), params=params, timeout=TIMEOUT)
    return assert_status(response, 200)


def get_db():
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]


def seed_receipt(db, status: str = "valid") -> str:
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
    db.receipts.insert_one(doc)
    return str(doc["_id"])


def seed_physical_tag(db, tag_key: str, status: str = "available") -> str:
    existing = db.tags.find_one({"tag_key": tag_key})
    if existing:
        db.tags.update_one(
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
    db.tags.insert_one(doc)
    return str(doc["_id"])


def create_fake_player_id() -> str:
    return str(ObjectId())


def run_multi_tag_digital_flow() -> dict[str, Any]:
    db = get_db()

    receipt_id = seed_receipt(db, "valid")
    player_id = create_fake_player_id()

    session = api_post(
        "/api/sessions",
        {
            "receipt_ids": [receipt_id],
            "player_id": player_id,
            "total_plays": 2,
            "phone": "5511999999999",
        },
    )
    session_id = session["session_id"]

    joined = api_post("/api/queue/join", {"session_id": session_id, "total_plays": 2})
    queue_player_id = joined["player_id"]

    tag1 = api_post("/api/tags/generate", {"session_id": session_id, "delivery_mode": "digital"})
    tag2 = api_post("/api/tags/generate", {"session_id": session_id, "delivery_mode": "digital"})
    mobile_before = api_get(f"/api/queue/mobile/{queue_player_id}")

    assert_true(tag1["status"] == "valid", "Primeira tag deveria estar valid")
    assert_true(tag2["status"] == "valid", "Segunda tag deveria estar valid")
    assert_true(tag1["tag_key"] != tag2["tag_key"], "As tags geradas devem ser diferentes")

    next_called = api_post("/api/queue/next", {})
    validate = api_post("/api/queue/validate", params={"player_id": queue_player_id})

    complete1 = api_post("/api/queue/complete", params={"player_id": queue_player_id})
    used1 = api_post("/api/tags/use", {"tag_key": tag1["tag_key"]})

    complete2 = api_post("/api/queue/complete", params={"player_id": queue_player_id})
    used2 = api_post("/api/tags/use", {"tag_key": tag2["tag_key"]})

    session_after = api_get(f"/api/sessions/{session_id}")

    assert_true(validate["allowed"] is True, "Jogador deveria estar liberado após next")
    assert_true(used1["status"] == "used", "Primeira tag digital deveria virar used")
    assert_true(used2["status"] == "used", "Segunda tag digital deveria virar used")
    assert_true(session_after["total_plays"] == 2, "Session deveria manter total_plays=2")
    assert_true(session_after["status"] == "finished", "Session deveria terminar como finished")

    return {
        "receipt_id": receipt_id,
        "player_id": player_id,
        "session": session,
        "join_queue": joined,
        "tag1": tag1,
        "tag2": tag2,
        "mobile_before": mobile_before,
        "next_called": next_called,
        "validate": validate,
        "complete1": complete1,
        "used1": used1,
        "complete2": complete2,
        "used2": used2,
        "session_after": session_after,
    }


def run_multi_tag_physical_flow() -> dict[str, Any]:
    db = get_db()

    receipt_id = seed_receipt(db, "valid")
    player_id = create_fake_player_id()
    seed_physical_tag(db, "T1284", "available")
    seed_physical_tag(db, "T2309", "available")
    seed_physical_tag(db, "T9998", "available")

    session = api_post(
        "/api/sessions",
        {
            "receipt_ids": [receipt_id],
            "player_id": player_id,
            "total_plays": 2,
        },
    )
    session_id = session["session_id"]

    joined = api_post("/api/queue/join", {"session_id": session_id, "total_plays": 2})
    queue_player_id = joined["player_id"]

    assoc1 = api_post("/api/tags/associate", {"session_id": session_id, "delivery_mode": "physical"})
    assoc2 = api_post("/api/tags/associate", {"session_id": session_id, "delivery_mode": "physical"})
    mobile_before = api_get(f"/api/queue/mobile/{queue_player_id}")

    assert_true(assoc1["tag"]["status"] == "valid", "Primeira tag física deveria estar valid")
    assert_true(assoc2["tag"]["status"] == "valid", "Segunda tag física deveria estar valid")
    assert_true(assoc1["tag"]["tag_key"] != assoc2["tag"]["tag_key"], "As tags físicas associadas devem ser diferentes")

    api_post("/api/queue/next", {})
    validate = api_post("/api/queue/validate", params={"player_id": queue_player_id})

    complete1 = api_post("/api/queue/complete", params={"player_id": queue_player_id})
    used1 = api_post("/api/tags/use", {"tag_key": assoc1["tag"]["tag_key"]})

    complete2 = api_post("/api/queue/complete", params={"player_id": queue_player_id})
    used2 = api_post("/api/tags/use", {"tag_key": assoc2["tag"]["tag_key"]})

    session_after = api_get(f"/api/sessions/{session_id}")

    assert_true(validate["allowed"] is True, "Jogador físico deveria estar liberado")
    assert_true(used1["status"] == "available", "Tag física usada deve voltar para available")
    assert_true(used2["status"] == "available", "Segunda tag física usada deve voltar para available")
    assert_true(used1["session_id"] is None, "Tag física usada deve limpar session_id")
    assert_true(used2["session_id"] is None, "Tag física usada deve limpar session_id")
    assert_true(session_after["status"] == "finished", "Session física deveria terminar como finished")

    return {
        "receipt_id": receipt_id,
        "player_id": player_id,
        "session": session,
        "join_queue": joined,
        "assoc1": assoc1,
        "assoc2": assoc2,
        "mobile_before": mobile_before,
        "validate": validate,
        "complete1": complete1,
        "used1": used1,
        "complete2": complete2,
        "used2": used2,
        "session_after": session_after,
    }


def run_negative_checks() -> list[dict[str, Any]]:
    db = get_db()
    results: list[dict[str, Any]] = []

    receipt_id = seed_receipt(db, "valid")
    player_id = create_fake_player_id()
    seed_physical_tag(db, "T5555", "available")

    session = api_post(
        "/api/sessions",
        {
            "receipt_ids": [receipt_id],
            "player_id": player_id,
            "total_plays": 2,
        },
    )
    session_id = session["session_id"]

    tag1 = api_post("/api/tags/generate", {"session_id": session_id, "delivery_mode": "digital"})
    tag2 = api_post("/api/tags/associate", {"session_id": session_id, "delivery_mode": "physical", "tag_key": "T5555"})

    third_attempt = requests.post(
        f"{BASE_URL}/api/tags/generate",
        headers=headers(),
        json={"session_id": session_id, "delivery_mode": "digital"},
        timeout=TIMEOUT,
    )
    third_data = assert_status(third_attempt, 409)
    results.append(
        {
            "name": "block_tag_generation_above_total_plays",
            "tag1": tag1["tag_key"],
            "tag2": tag2["tag"]["tag_key"],
            "response": third_data,
        }
    )

    reuse_attempt = requests.post(
        f"{BASE_URL}/api/sessions",
        headers=headers(),
        json={"receipt_ids": [receipt_id], "player_id": create_fake_player_id(), "total_plays": 1},
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


def main() -> int:
    log("Configuração", {
        "base_url": BASE_URL,
        "mongo_uri": MONGO_URI,
        "db_name": DB_NAME,
        "device_id": DEVICE_ID,
    })

    try:
        digital = run_multi_tag_digital_flow()
        log("Fluxo digital multi-tag OK", digital)

        physical = run_multi_tag_physical_flow()
        log("Fluxo físico multi-tag OK", physical)

        negative = run_negative_checks()
        log("Validações negativas OK", negative)

        summary = {
            "result": "success",
            "digital_session_id": digital["session"]["session_id"],
            "physical_session_id": physical["session"]["session_id"],
            "digital_tag_keys": [digital["tag1"]["tag_key"], digital["tag2"]["tag_key"]],
            "physical_tag_keys": [physical["assoc1"]["tag"]["tag_key"], physical["assoc2"]["tag"]["tag_key"]],
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


if __name__ == "__main__":
    sys.exit(main())