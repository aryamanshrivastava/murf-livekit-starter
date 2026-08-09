import json
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "database.db"


@contextmanager
def get_db(db_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite connections with row_factory enabled."""
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize SQLite database table for sellers if it does not exist."""
    with get_db(db_path) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS callers (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                language_preference TEXT DEFAULT 'Hinglish',
                facts TEXT DEFAULT '{}',
                last_interaction TEXT NOT NULL
            )
            """
        )


def lookup_seller_db(
    name_or_id: str, db_path: Optional[Path] = None
) -> Optional[dict[str, Any]]:
    """Look up a seller by user_id or name (case-insensitive match)."""
    init_db(db_path)
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM callers WHERE user_id = ? OR LOWER(name) = LOWER(?)",
            (name_or_id, name_or_id),
        )
        row = cursor.fetchone()
        if not row:
            cursor.execute(
                "SELECT * FROM callers WHERE LOWER(name) LIKE LOWER(?)",
                (f"%{name_or_id}%",),
            )
            row = cursor.fetchone()

        if not row:
            return None

        facts_dict = json.loads(row["facts"]) if row["facts"] else {}
        return {
            "user_id": row["user_id"],
            "name": row["name"],
            "language_preference": row["language_preference"],
            "facts": facts_dict,
            "last_interaction": row["last_interaction"],
        }


def save_seller_db(
    user_id: str,
    name: str,
    language_preference: str = "Hinglish",
    facts: Optional[Union[dict[str, Any], str]] = None,
    last_interaction: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Insert or update seller record in SQLite database."""
    init_db(db_path)
    now_iso = last_interaction or datetime.now(timezone.utc).isoformat()

    parsed_facts: dict[str, Any] = {}
    if isinstance(facts, str):
        try:
            parsed_facts = json.loads(facts)
        except Exception:
            parsed_facts = {"notes": facts}
    elif isinstance(facts, dict):
        parsed_facts = facts

    existing = lookup_seller_db(user_id, db_path=db_path)
    if existing:
        merged_facts = existing.get("facts", {})
        merged_facts.update(parsed_facts)
        parsed_facts = merged_facts

    facts_json = json.dumps(parsed_facts)

    with get_db(db_path) as conn, conn:
        conn.execute(
            """
            INSERT INTO callers (user_id, name, language_preference, facts, last_interaction)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                name=excluded.name,
                language_preference=COALESCE(excluded.language_preference, callers.language_preference),
                facts=excluded.facts,
                last_interaction=excluded.last_interaction
            """,
            (user_id, name, language_preference, facts_json, now_iso),
        )

    return {
        "user_id": user_id,
        "name": name,
        "language_preference": language_preference,
        "facts": parsed_facts,
        "last_interaction": now_iso,
    }


# Aliases for compatibility
lookup_caller_db = lookup_seller_db
save_caller_db = save_seller_db
lookup_seller = lookup_seller_db
save_seller = save_seller_db
