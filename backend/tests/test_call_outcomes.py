import tempfile
from pathlib import Path

import pytest
from livekit.agents import AgentSession, inference, llm

from agent import Assistant
from db import (
    DEFAULT_DB_PATH,
    get_call_metrics_db,
    init_db,
    record_call_outcome_db,
)


@pytest.fixture(autouse=True)
def clean_database():
    """Ensure a clean database for each test run."""
    if DEFAULT_DB_PATH.exists():
        DEFAULT_DB_PATH.unlink()
    init_db()
    yield
    if DEFAULT_DB_PATH.exists():
        DEFAULT_DB_PATH.unlink()


def test_call_outcomes_db():
    """Unit test for call outcomes DB recording and metrics aggregation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_calls.db"
        init_db(db_path)

        # Initial metrics should be 0
        metrics = get_call_metrics_db(db_path=db_path)
        assert metrics["total_calls"] == 0
        assert metrics["successful_calls"] == 0
        assert metrics["failed_calls"] == 0

        # Record a successful call
        res1 = record_call_outcome_db(
            call_id="call-001",
            room_name="room-001",
            seller_id="Ramesh Store",
            outbound=False,
            outcome="SUCCESS",
            reason="Completed catalogue inquiry",
            started_at="2026-08-13T10:00:00Z",
            ended_at="2026-08-13T10:02:00Z",
            duration_seconds=120.5,
            db_path=db_path,
        )
        assert res1["outcome"] == "SUCCESS"

        # Record a failed call
        res2 = record_call_outcome_db(
            call_id="call-002",
            room_name="room-002",
            seller_id=None,
            outbound=False,
            outcome="FAILED",
            reason="User hung up before shop identification",
            started_at="2026-08-13T10:05:00Z",
            ended_at="2026-08-13T10:05:15Z",
            duration_seconds=15.0,
            db_path=db_path,
        )
        assert res2["outcome"] == "FAILED"

        # Record another successful call
        record_call_outcome_db(
            call_id="call-003",
            room_name="room-003",
            seller_id="Suresh Kirana",
            outbound=True,
            outcome="SUCCESS",
            reason="Restock request completed",
            started_at="2026-08-13T10:10:00Z",
            ended_at="2026-08-13T10:11:30Z",
            duration_seconds=90.0,
            db_path=db_path,
        )

        # Check aggregated metrics
        metrics = get_call_metrics_db(db_path=db_path)
        assert metrics["total_calls"] == 3
        assert metrics["successful_calls"] == 2
        assert metrics["failed_calls"] == 1
        assert len(metrics["recent_calls"]) == 3
        assert metrics["recent_calls"][0]["call_id"] == "call-003"


def _llm() -> llm.LLM:
    return inference.LLM(model="openai/gpt-4.1-mini")


@pytest.mark.asyncio
async def test_assistant_call_success_flags():
    """Verify Assistant tracking flags on shop lookup and business inquiry."""
    assistant = Assistant()
    assert assistant.seller_identified is False
    assert assistant.business_action_completed is False

    async with (
        _llm() as llm_inst,
        AgentSession(llm=llm_inst) as session,
    ):
        await session.start(assistant)

        # User provides shop name and asks product stock
        result = await session.run(
            user_input="Namaste, my shop name is Ramesh Kirana. What is the stock of Maggi?"
        )

        # Consume any chat event
        if result.events and type(result.events[0]).__name__ == "ChatMessageEvent":
            result.expect.next_event().is_message(role="assistant")

        # Verify lookup_seller and lookup_product function calls occur
        assert assistant.seller_identified is True
        assert assistant.active_seller_id is not None
