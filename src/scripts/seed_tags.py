from __future__ import annotations

import argparse
import os
import random
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient
from pymongo.collection import Collection


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
    mongo_db = os.getenv("MONGO_DB", "hersheys_capibarra-dev")

    if not mongo_uri:
        raise RuntimeError("MONGO_URI não definido. Configure no .env ou nas variáveis de ambiente.")

    client = MongoClient(mongo_uri)
    db = client[mongo_db]
    return db["tags"]


def generate_random_tag_keys(quantity: int, width: int) -> list[str]:
    max_number = 10**width - 1
    min_number = 0

    if quantity > (max_number - min_number + 1):
        raise ValueError("Quantidade maior que o total possível de combinações para esse width.")

    numbers = random.sample(range(min_number, max_number + 1), quantity)
    return [str(number).zfill(width) for number in numbers]


def seed_tags(collection: Collection, tag_keys: list[str], force_update: bool = False) -> None:
    now = datetime.now(timezone.utc)

    for tag_key in tag_keys:
        payload = {
            "tag_key": tag_key,
            "status": "invalid",
            "last_updated_at": now,
            "updated_at": now,
        }

        existing = collection.find_one({"tag_key": tag_key})
        if existing and not force_update:
            print(f"[skip] tag já existe: {tag_key}")
            continue

        if existing and force_update:
            collection.update_one(
                {"_id": existing["_id"]},
                {"$set": payload, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
            print(f"[updated] {tag_key}")
            continue

        payload["created_at"] = now
        collection.insert_one(payload)
        print(f"[created] {tag_key}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed de tags para o backend Capibarra.")
    parser.add_argument("--env-file", default=".env", help="Caminho do arquivo .env")
    parser.add_argument("--quantity", type=int, default=100, help="Quantidade de tags aleatórias para gerar")
    parser.add_argument("--width", type=int, default=5, help="Quantidade de dígitos da tag")
    parser.add_argument(
        "--force-update",
        action="store_true",
        help="Atualiza documentos existentes com a mesma tag_key.",
    )
    args = parser.parse_args()

    load_dotenv(args.env_file)
    collection = build_collection()
    tag_keys = generate_random_tag_keys(args.quantity, args.width)
    seed_tags(collection, tag_keys, force_update=args.force_update)
