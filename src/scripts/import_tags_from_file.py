"""
Import tag codes from a text file into the MongoDB tags collection.

File format: one tag_key per line; blank lines and lines starting with '#' are ignored.

Usage:
    python src/scripts/import_tags_from_file.py docs/tag_codes.txt
    python src/scripts/import_tags_from_file.py docs/tag_codes.txt --delivery-mode physical
    python src/scripts/import_tags_from_file.py docs/tag_codes.txt --status available --force-update
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient
from pymongo.collection import Collection


VALID_STATUSES = ("available", "invalid", "valid", "used")
VALID_DELIVERY_MODES = ("physical", "digital")


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
        raise RuntimeError("MONGO_URI not set. Configure it in .env or as an environment variable.")

    client = MongoClient(mongo_uri)
    return client[mongo_db]["tags"]


def read_tag_keys(file_path: Path) -> list[str]:
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    keys = []
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        keys.append(line)

    return keys


def import_tags(
    collection: Collection,
    tag_keys: list[str],
    delivery_mode: str,
    status: str,
    force_update: bool,
) -> None:
    now = datetime.now(timezone.utc)
    created = skipped = updated = 0

    for tag_key in tag_keys:
        existing = collection.find_one({"tag_key": tag_key})

        if existing and not force_update:
            print(f"[skip]    {tag_key}")
            skipped += 1
            continue

        payload = {
            "tag_key": tag_key,
            "delivery_mode": delivery_mode,
            "status": status,
            "session_id": None,
            "last_updated_at": now,
            "used_at": None,
            "invalid_reason": None,
        }

        if existing and force_update:
            collection.update_one({"_id": existing["_id"]}, {"$set": payload})
            print(f"[updated] {tag_key}")
            updated += 1
        else:
            payload["created_at"] = now
            collection.insert_one(payload)
            print(f"[created] {tag_key}")
            created += 1

    print(f"\nDone — created: {created}, updated: {updated}, skipped: {skipped}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import tag codes from a text file into MongoDB.")
    parser.add_argument("file", type=Path, help="Path to the text file (one tag_key per line)")
    parser.add_argument(
        "--delivery-mode",
        choices=VALID_DELIVERY_MODES,
        default="physical",
        help="Delivery mode for all imported tags (default: physical)",
    )
    parser.add_argument(
        "--status",
        choices=VALID_STATUSES,
        default="available",
        help="Initial status for new tags (default: available)",
    )
    parser.add_argument(
        "--force-update",
        action="store_true",
        help="Overwrite existing tags with the same tag_key instead of skipping them",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to the .env file (default: .env)",
    )
    args = parser.parse_args()

    load_dotenv(args.env_file)

    try:
        tag_keys = read_tag_keys(args.file)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not tag_keys:
        print("No tag keys found in file. Nothing to import.")
        sys.exit(0)

    print(f"Found {len(tag_keys)} tag(s) in '{args.file}'")
    print(f"delivery_mode={args.delivery_mode}  status={args.status}  force_update={args.force_update}\n")

    try:
        collection = build_collection()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    import_tags(collection, tag_keys, args.delivery_mode, args.status, args.force_update)


if __name__ == "__main__":
    main()
