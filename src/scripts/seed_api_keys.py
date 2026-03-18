from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient
from pymongo.collection import Collection


DEFAULT_KEYS = [
    {"name": "tablet-01", "api_key": "capibarra-tablet-01", "is_active": True},
    {"name": "tablet-02", "api_key": "capibarra-tablet-02", "is_active": True},
    {"name": "tablet-03", "api_key": "capibarra-tablet-03", "is_active": True},
]


def load_dotenv(dotenv_path: str = ".env") -> None:
    path = Path(dotenv_path)
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def build_collection() -> Collection:
    mongo_uri = os.getenv("MONGO_URI")
    mongo_db = os.getenv("MONGO_DB", "hersheys_capibarra_test")

    if not mongo_uri:
        raise RuntimeError("MONGO_URI não definido. Configure no .env ou nas variáveis de ambiente.")

    client = MongoClient(mongo_uri)
    db = client[mongo_db]
    return db["api_keys"]


def seed_api_keys(collection: Collection, keys: list[dict], force_update: bool = False) -> None:
    now = datetime.now(timezone.utc)

    for key_doc in keys:
        payload = {
            "name": key_doc["name"],
            "api_key": key_doc["api_key"],
            "is_active": key_doc.get("is_active", True),
            "updated_at": now,
        }

        existing = collection.find_one({"api_key": key_doc["api_key"]})
        if existing and not force_update:
            print(f"[skip] api_key já existe: {key_doc['name']}")
            continue

        if existing and force_update:
            collection.update_one(
                {"_id": existing["_id"]},
                {"$set": payload, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
            print(f"[updated] {key_doc['name']}")
            continue

        payload["created_at"] = now
        payload["last_used_at"] = None
        collection.insert_one(payload)
        print(f"[created] {key_doc['name']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed de API keys para o backend Capibarra.")
    parser.add_argument("--env-file", default=".env", help="Caminho do arquivo .env")
    parser.add_argument(
        "--force-update",
        action="store_true",
        help="Atualiza documentos existentes com a mesma api_key.",
    )
    args = parser.parse_args()

    load_dotenv(args.env_file)
    collection = build_collection()
    seed_api_keys(collection, DEFAULT_KEYS, force_update=args.force_update)
