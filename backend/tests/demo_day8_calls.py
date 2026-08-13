from datetime import datetime, timezone
import time
from pathlib import Path
import json

from db import DEFAULT_DB_PATH, init_db, record_call_outcome_db, get_call_metrics_db


def main():
    print(f"Using database path: {DEFAULT_DB_PATH}")
    init_db()

    # Get initial metrics
    initial_metrics = get_call_metrics_db()
    print("Initial Call Metrics:", json.dumps(initial_metrics, indent=2))

    now = datetime.now(timezone.utc).isoformat()

    # Simulate a successful call
    call1_id = f"TEST-SUCCESS-{int(time.time())}"
    res1 = record_call_outcome_db(
        call_id=call1_id,
        room_name="demo-room-success",
        seller_id="Ramesh Kirana",
        outbound=False,
        outcome="SUCCESS",
        reason="Caller identified shop and completed product catalogue inquiry",
        started_at=now,
        ended_at=now,
        duration_seconds=45.2,
    )
    print(f"Recorded Successful Call: {res1['call_id']}")

    # Simulate a failed call
    call2_id = f"TEST-FAILED-{int(time.time())}"
    res2 = record_call_outcome_db(
        call_id=call2_id,
        room_name="demo-room-failed",
        seller_id=None,
        outbound=False,
        outcome="FAILED",
        reason="Call ended before shop identification or business inquiry completed",
        started_at=now,
        ended_at=now,
        duration_seconds=12.0,
    )
    print(f"Recorded Failed Call: {res2['call_id']}")

    # Query updated metrics
    updated_metrics = get_call_metrics_db()
    print("\nUpdated Call Metrics:", json.dumps(updated_metrics, indent=2))
    assert updated_metrics["total_calls"] >= initial_metrics["total_calls"] + 2
    assert updated_metrics["successful_calls"] >= initial_metrics["successful_calls"] + 1
    assert updated_metrics["failed_calls"] >= initial_metrics["failed_calls"] + 1
    print("\n✅ Verification Successful: Total calls and Successful/Failed call counters updated accurately!")

if __name__ == "__main__":
    main()
