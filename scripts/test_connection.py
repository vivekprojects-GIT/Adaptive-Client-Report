"""
Verify the MongoDB connection (Atlas or local) works.

Reads APE_MONGO_URI + APE_MONGO_DB from .env. Pings the cluster, lists
collections, and reports counts.

Run:
    cd ape_modulor_production
    PYTHONPATH=. python scripts/test_connection.py
"""

from __future__ import annotations

import os
import sys
from urllib.parse import urlparse

from dotenv import load_dotenv


def mask_uri(uri: str) -> str:
    """Redact the password so we can print the URI safely."""
    try:
        parsed = urlparse(uri)
        if parsed.password:
            netloc = parsed.netloc.replace(f":{parsed.password}@", ":<redacted>@")
            return uri.replace(parsed.netloc, netloc)
    except Exception:
        pass
    return uri


def main() -> int:
    load_dotenv()
    uri = os.getenv("APE_MONGO_URI")
    db_name = os.getenv("APE_MONGO_DB", "ape")

    if not uri:
        print("ERROR: APE_MONGO_URI is not set. Add it to .env.", file=sys.stderr)
        return 1

    print(f"Connecting to:  {mask_uri(uri)}")
    print(f"Database name:  {db_name}")

    from ape.store import MongoStore
    try:
        store = MongoStore(uri=uri, db_name=db_name)
        # Ping
        store.client.admin.command("ping")
        print("Ping: OK")

        # List collections
        cols = store.db.list_collection_names()
        print(f"Collections: {cols if cols else '(none yet)'}")

        # Counts per collection
        for c in ("ape_config", "ape_user_bandit_state", "ape_turn_record", "ape_admin_audit"):
            cnt = store.db[c].count_documents({}) if c in cols else 0
            print(f"  {c}: {cnt} docs")

        # Index check
        for c in ("ape_config", "ape_user_bandit_state", "ape_turn_record", "ape_admin_audit"):
            if c in cols:
                idx_names = [i["name"] for i in store.db[c].list_indexes()]
                print(f"  {c} indexes: {idx_names}")

        print("\nConnection verified.")
        return 0
    except Exception as e:
        print(f"\nConnection FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
