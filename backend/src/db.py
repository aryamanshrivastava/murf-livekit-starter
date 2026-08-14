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
    init_call_outcomes_table(db_path)
    init_refund_claims_table(db_path)


def init_refund_claims_table(db_path: Optional[Path] = None) -> None:
    """Initialize the refund_claims table in SQLite."""
    with get_db(db_path) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS refund_claims (
                claim_id TEXT PRIMARY KEY,
                seller_id TEXT NOT NULL,
                product_name TEXT NOT NULL,
                issue_type TEXT NOT NULL,
                refund_amount REAL DEFAULT 0.0,
                claim_reason TEXT NOT NULL,
                status TEXT DEFAULT 'APPROVED',
                created_at TEXT NOT NULL
            )
            """
        )



def init_call_outcomes_table(db_path: Optional[Path] = None) -> None:
    """Initialize the call_outcomes table in SQLite."""
    with get_db(db_path) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS call_outcomes (
                call_id TEXT PRIMARY KEY,
                room_name TEXT NOT NULL,
                seller_id TEXT,
                outbound INTEGER DEFAULT 0,
                outcome TEXT NOT NULL,
                reason TEXT,
                started_at TEXT NOT NULL,
                ended_at TEXT NOT NULL,
                duration_seconds REAL DEFAULT 0.0
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


def record_call_outcome_db(
    call_id: str,
    room_name: str,
    outcome: str,
    seller_id: Optional[str] = None,
    outbound: bool = False,
    reason: Optional[str] = None,
    started_at: Optional[str] = None,
    ended_at: Optional[str] = None,
    duration_seconds: float = 0.0,
    db_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Insert or update a call outcome record into SQLite database."""
    target_path = db_path or DEFAULT_DB_PATH
    init_call_outcomes_table(target_path)

    now_iso = datetime.now(timezone.utc).isoformat()
    start_iso = started_at or now_iso
    end_iso = ended_at or now_iso
    valid_outcome = "SUCCESS" if str(outcome).upper() == "SUCCESS" else "FAILED"

    with get_db(target_path) as conn, conn:
        conn.execute(
            """
            INSERT INTO call_outcomes (
                call_id, room_name, seller_id, outbound,
                outcome, reason, started_at, ended_at, duration_seconds
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(call_id) DO UPDATE SET
                seller_id=excluded.seller_id,
                outcome=excluded.outcome,
                reason=excluded.reason,
                ended_at=excluded.ended_at,
                duration_seconds=excluded.duration_seconds
            """,
            (
                call_id,
                room_name,
                seller_id,
                1 if outbound else 0,
                valid_outcome,
                reason
                or (
                    "Call completed successfully"
                    if valid_outcome == "SUCCESS"
                    else "Call condition not met"
                ),
                start_iso,
                end_iso,
                round(duration_seconds, 2),
            ),
        )

    return {
        "call_id": call_id,
        "room_name": room_name,
        "seller_id": seller_id,
        "outbound": outbound,
        "outcome": valid_outcome,
        "reason": reason,
        "started_at": start_iso,
        "ended_at": end_iso,
        "duration_seconds": round(duration_seconds, 2),
    }


def get_call_metrics_db(
    db_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Retrieve call outcome statistics (total, successful, failed) and recent call history."""
    target_path = db_path or DEFAULT_DB_PATH
    init_call_outcomes_table(target_path)

    with get_db(target_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM call_outcomes")
        total = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT COUNT(*) as successful FROM call_outcomes WHERE outcome = 'SUCCESS'"
        )
        successful = cursor.fetchone()["successful"]

        cursor.execute(
            "SELECT COUNT(*) as failed FROM call_outcomes WHERE outcome = 'FAILED'"
        )
        failed = cursor.fetchone()["failed"]

        cursor.execute(
            "SELECT * FROM call_outcomes ORDER BY started_at DESC LIMIT 50"
        )
        recent_rows = cursor.fetchall()
        recent_calls = [dict(r) for r in recent_rows]

    return {
        "total_calls": total,
        "successful_calls": successful,
        "failed_calls": failed,
        "recent_calls": recent_calls,
    }


def create_refund_claim_db(
    seller_id: str,
    product_name: str,
    issue_type: str,
    refund_amount: float = 0.0,
    claim_reason: str = "",
    db_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Record a seller return/refund claim in SQLite database."""
    import uuid

    target_path = db_path or DEFAULT_DB_PATH
    init_refund_claims_table(target_path)

    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    date_str = now_dt.strftime("%Y%m%d")
    claim_id = f"REF-{date_str}-{uuid.uuid4().hex[:6].upper()}"

    with get_db(target_path) as conn, conn:
        conn.execute(
            """
            INSERT INTO refund_claims (
                claim_id, seller_id, product_name, issue_type,
                refund_amount, claim_reason, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'APPROVED', ?)
            """,
            (
                claim_id,
                seller_id,
                product_name,
                issue_type,
                float(refund_amount),
                claim_reason,
                now_iso,
            ),
        )

    return {
        "claim_id": claim_id,
        "seller_id": seller_id,
        "product_name": product_name,
        "issue_type": issue_type,
        "refund_amount": float(refund_amount),
        "claim_reason": claim_reason,
        "status": "APPROVED",
        "created_at": now_iso,
    }


def get_refund_claims_db(
    seller_id: Optional[str] = None, db_path: Optional[Path] = None
) -> list[dict[str, Any]]:
    """Retrieve processed refund claims from SQLite database."""
    target_path = db_path or DEFAULT_DB_PATH
    init_refund_claims_table(target_path)

    with get_db(target_path) as conn:
        cursor = conn.cursor()
        if seller_id:
            cursor.execute(
                "SELECT * FROM refund_claims WHERE seller_id = ? ORDER BY created_at DESC",
                (seller_id,),
            )
        else:
            cursor.execute("SELECT * FROM refund_claims ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


