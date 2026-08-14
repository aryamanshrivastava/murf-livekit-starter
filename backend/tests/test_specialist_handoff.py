import tempfile
from pathlib import Path

import pytest
from livekit.agents import AgentSession, inference, llm

from agent import Assistant
from db import (
    DEFAULT_DB_PATH,
    create_refund_claim_db,
    get_refund_claims_db,
    init_db,
    save_seller_db,
)
from specialist import RefundSpecialist
from specialist_prompt import SPECIALIST_NAME


@pytest.fixture(autouse=True)
def clean_database():
    """Ensure a clean database for each test run."""
    if DEFAULT_DB_PATH.exists():
        DEFAULT_DB_PATH.unlink()
    init_db()
    # Pre-populate returning seller profile for Ramesh Store
    save_seller_db(
        user_id="Ramesh Store",
        name="Ramesh Store",
        language_preference="Hinglish",
        facts={"preferred_delivery": "morning"},
    )
    yield
    if DEFAULT_DB_PATH.exists():
        DEFAULT_DB_PATH.unlink()


def test_refund_claim_db():
    """Unit test verifying refund claim database operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_refunds.db"
        init_db(db_path)

        # Initial claims should be empty
        claims = get_refund_claims_db(db_path=db_path)
        assert len(claims) == 0

        # Save a refund claim
        claim = create_refund_claim_db(
            seller_id="Ramesh Store",
            product_name="Maggi",
            issue_type="damaged_goods",
            refund_amount=250.0,
            claim_reason="5 damaged packets upon delivery",
            db_path=db_path,
        )

        assert claim["claim_id"].startswith("REF-")
        assert claim["seller_id"] == "Ramesh Store"
        assert claim["refund_amount"] == 250.0
        assert claim["status"] == "APPROVED"

        # Query claims from DB
        fetched = get_refund_claims_db(seller_id="Ramesh Store", db_path=db_path)
        assert len(fetched) == 1
        assert fetched[0]["claim_id"] == claim["claim_id"]
        assert fetched[0]["product_name"] == "Maggi"


from livekit.plugins import google


def _llm() -> llm.LLM:
    return google.LLM(model="gemini-3.5-flash-lite")



@pytest.mark.asyncio
async def test_normal_path_no_handoff():
    """Step 6 Test: Normal question (catalogue lookup) is answered directly by Priya without handoff."""
    assistant = Assistant()

    async with (
        _llm() as llm_inst,
        AgentSession(llm=llm_inst) as session,
    ):
        await session.start(assistant)

        # User asks a normal stock/price query
        result = await session.run(
            user_input="Namaste! My shop is Ramesh Store. What is the stock and price of Maggi?"
        )

        tool_calls = [
            getattr(ev.item, "name", "")
            for ev in result.events
            if type(ev).__name__ == "FunctionCallEvent"
        ]

        assert "handoff_to_refund_specialist" not in tool_calls, "Normal query should not trigger handoff"
        assert type(session.current_agent).__name__ == "Assistant", "Active agent should remain Priya"


@pytest.mark.asyncio
async def test_specialist_handoff_path():
    """Step 6 Test: Refund question triggers handoff to Karan (Refund Specialist)."""
    assistant = Assistant()

    async with (
        _llm() as llm_inst,
        AgentSession(llm=llm_inst) as session,
    ):
        await session.start(assistant)

        # Path 1: Initial query to establish shop identity
        await session.run(
            user_input="Namaste! My shop is Ramesh Store. What is the stock and price of Maggi?"
        )

        # Path 2: Refund request triggering handoff to specialist
        result = await session.run(
            user_input="I received 5 damaged packets of Maggi in my delivery today. I want a refund of ₹100 for them."
        )

        tool_calls = [
            getattr(ev.item, "name", "")
            for ev in result.events
            if type(ev).__name__ == "FunctionCallEvent"
        ]

        assert "handoff_to_refund_specialist" in tool_calls, f"Refund request should call handoff_to_refund_specialist. Calls made: {tool_calls}"
        assert type(session.current_agent).__name__ == "RefundSpecialist", "Active agent should switch to RefundSpecialist"


@pytest.mark.asyncio
async def test_specialist_handoff_back_to_priya():
    """Test that Karan hands off back to Priya when user asks standard catalogue or order queries."""
    assistant = Assistant()

    async with (
        _llm() as llm_inst,
        AgentSession(llm=llm_inst) as session,
    ):
        await session.start(assistant)

        # 1. Establish identity with Priya
        await session.run(
            user_input="Namaste! My shop is Ramesh Store."
        )

        # 2. Trigger handoff to Karan (Refund Specialist)
        await session.run(
            user_input="I received 5 damaged packets of Maggi. I want a refund."
        )
        assert type(session.current_agent).__name__ == "RefundSpecialist", "Agent should be Karan"

        # 3. User asks standard catalogue question -> Should trigger handoff back to Priya
        result = await session.run(
            user_input="Thank you Karan! Now can you take me back to Priya? I want to place a new order for Amul Butter."
        )

        tool_calls = [
            getattr(ev.item, "name", "")
            for ev in result.events
            if type(ev).__name__ == "FunctionCallEvent"
        ]

        assert "handoff_to_main_assistant" in tool_calls, f"Catalogue request while with Karan should call handoff_to_main_assistant. Calls made: {tool_calls}"
        assert type(session.current_agent).__name__ == "Assistant", "Active agent should switch back to Priya (Assistant)"

