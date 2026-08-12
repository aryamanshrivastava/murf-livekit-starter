import contextlib
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


def init_escalation_table(db_path: Optional[Path] = None) -> None:
    """Initialize the escalation_requests table in SQLite."""
    with get_db(db_path) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS escalation_requests (
                escalation_id TEXT PRIMARY KEY,
                seller_id TEXT NOT NULL,
                seller_name TEXT NOT NULL,
                contact_phone TEXT,
                category TEXT NOT NULL,
                issue_summary TEXT NOT NULL,
                agent_findings TEXT DEFAULT '',
                urgency_level TEXT DEFAULT 'MEDIUM',
                language TEXT DEFAULT 'Hinglish',
                contact_method TEXT DEFAULT 'phone',
                status TEXT DEFAULT 'OPEN',
                created_at TEXT NOT NULL
            )
            """
        )


def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize SQLite database tables for sellers and escalations if they do not exist."""
    with get_db(db_path) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS callers (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                language_preference TEXT DEFAULT 'Hinglish',
                facts TEXT DEFAULT '{}',
                phone TEXT,
                last_interaction TEXT NOT NULL
            )
            """
        )
        # Migration guard: add phone column if it doesn't exist yet
        with contextlib.suppress(Exception):
            conn.execute("ALTER TABLE callers ADD COLUMN phone TEXT")
    init_escalation_table(db_path)


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
            "phone": row["phone"],
            "last_interaction": row["last_interaction"],
        }


def save_seller_db(
    user_id: str,
    name: str,
    language_preference: str = "Hinglish",
    facts: Optional[Union[dict[str, Any], str]] = None,
    phone: Optional[str] = None,
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
            INSERT INTO callers (user_id, name, language_preference, facts, phone, last_interaction)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                name=excluded.name,
                language_preference=COALESCE(excluded.language_preference, callers.language_preference),
                facts=excluded.facts,
                phone=COALESCE(excluded.phone, callers.phone),
                last_interaction=excluded.last_interaction
            """,
            (user_id, name, language_preference, facts_json, phone, now_iso),
        )

    return {
        "user_id": user_id,
        "name": name,
        "language_preference": language_preference,
        "facts": parsed_facts,
        "phone": phone,
        "last_interaction": now_iso,
    }


def create_escalation_request_db(
    seller_id: str,
    seller_name: str,
    category: str,
    issue_summary: str,
    agent_findings: str = "",
    urgency_level: str = "MEDIUM",
    language: str = "Hinglish",
    contact_method: str = "phone",
    contact_phone: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Save a human escalation/support ticket to SQLite database."""
    import uuid

    target_path = db_path or DEFAULT_DB_PATH
    init_escalation_table(target_path)

    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    date_str = now_dt.strftime("%Y%m%d")
    esc_id = f"ESC-{date_str}-{uuid.uuid4().hex[:8].upper()}"

    with get_db(target_path) as conn, conn:
        conn.execute(
            """
            INSERT INTO escalation_requests (
                escalation_id, seller_id, seller_name, contact_phone,
                category, issue_summary, agent_findings, urgency_level,
                language, contact_method, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)
            """,
            (
                esc_id,
                seller_id,
                seller_name,
                contact_phone,
                category,
                issue_summary,
                agent_findings,
                urgency_level,
                language,
                contact_method,
                now_iso,
            ),
        )

    return {
        "escalation_id": esc_id,
        "seller_id": seller_id,
        "seller_name": seller_name,
        "contact_phone": contact_phone,
        "category": category,
        "issue_summary": issue_summary,
        "agent_findings": agent_findings,
        "urgency_level": urgency_level,
        "language": language,
        "contact_method": contact_method,
        "status": "OPEN",
        "created_at": now_iso,
    }


def get_escalation_requests_db(
    seller_id: Optional[str] = None, db_path: Optional[Path] = None
) -> list[dict[str, Any]]:
    """Retrieve open or past escalation tickets from SQLite database."""
    target_path = db_path or DEFAULT_DB_PATH
    init_escalation_table(target_path)

    with get_db(target_path) as conn:
        cursor = conn.cursor()
        if seller_id:
            cursor.execute(
                "SELECT * FROM escalation_requests WHERE seller_id = ? ORDER BY created_at DESC",
                (seller_id,),
            )
        else:
            cursor.execute("SELECT * FROM escalation_requests ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


# Aliases for compatibility
lookup_caller_db = lookup_seller_db
save_caller_db = save_seller_db
lookup_seller = lookup_seller_db
save_seller = save_seller_db
