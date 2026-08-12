import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from livekit.agents import AgentSession
from livekit.plugins import google

from agent import Assistant
from db import (
    create_escalation_request_db,
    get_escalation_requests_db,
    init_db,
    save_seller_db,
)


def test_create_escalation_request_db():
    """Unit test verifying human escalation database ticket insertion and retrieval."""
    init_db()

    req = create_escalation_request_db(
        seller_id="Instacart",
        seller_name="Instacart",
        category="Payment Dispute",
        issue_summary="Seller reports missing payout of Rs. 4,500 for order #8812.",
        agent_findings="Confirmed completed order in DB; payout status shows pending past 48h.",
        urgency_level="HIGH",
        language="Hinglish",
        contact_method="phone",
    )

    assert req["seller_id"] == "Instacart"
    assert req["category"] == "Payment Dispute"
    assert req["urgency_level"] == "HIGH"
    assert req["status"] == "OPEN"
    # Format: ESC-YYYYMMDD-<8 hex chars>
    assert re.match(r"^ESC-\d{8}-[0-9A-F]{8}$", req["escalation_id"]), (
        f"Unexpected escalation_id format: {req['escalation_id']}"
    )

    tickets = get_escalation_requests_db(seller_id="Instacart")
    assert len(tickets) >= 1
    latest = tickets[0]
    assert latest["escalation_id"] == req["escalation_id"]
    assert latest["category"] == "Payment Dispute"


@pytest.mark.asyncio
async def test_agent_escalation_on_dispute():
    """LLM-judged evaluation test for human escalation trigger on payment dispute."""
    init_db()
    save_seller_db(
        user_id="Instacart",
        name="Instacart",
        language_preference="Hinglish",
        phone="+917067250520",
    )
    llm = google.LLM(model="gemini-3.5-flash-lite")

    async with AgentSession(llm=llm) as session:
        await session.start(Assistant())

        # Step 1: Identify seller
        result1 = await session.run(user_input="Hello, my shop name is Instacart")
        if result1.events and type(result1.events[0]).__name__ == "ChatMessageEvent":
            result1.expect.next_event().is_message(role="assistant")
        result1.expect.next_event().is_function_call()
        result1.expect.next_event().is_function_call_output()

        # Step 2: Dispute query
        result2 = await session.run(
            user_input="I have a payment dispute. My payout of 5000 rupees for yesterday's orders has not been credited. Please connect me to a human manager."
        )

        # Agent should either ask permission or directly invoke create_escalation
        tool_called = any(
            getattr(getattr(ev, "item", None), "name", "") == "create_escalation"
            for ev in result2.events
        )

        if not tool_called:
            # Grant explicit consent if agent asked for permission first
            result3 = await session.run(
                user_input="Yes, please submit a support ticket to your team with my shop details."
            )
            tool_called = any(
                getattr(getattr(ev, "item", None), "name", "") == "create_escalation"
                for ev in result3.events
            )

        assert tool_called, (
            "Agent should call create_escalation when requested on payment dispute."
        )


@pytest.mark.asyncio
async def test_agent_normal_flow_does_not_escalate():
    """Verify that routine inventory queries do NOT trigger create_escalation."""
    init_db()
    save_seller_db(user_id="Instacart", name="Instacart")
    llm = google.LLM(model="gemini-3.5-flash-lite")

    async with AgentSession(llm=llm) as session:
        await session.start(Assistant())

        # Step 1: Identify seller
        result1 = await session.run(user_input="Hello, my shop name is Instacart")
        if result1.events and type(result1.events[0]).__name__ == "ChatMessageEvent":
            result1.expect.next_event().is_message(role="assistant")
        result1.expect.next_event().is_function_call()
        result1.expect.next_event().is_function_call_output()

        # Step 2: Routine stock query
        result2 = await session.run(
            user_input="How many packets of Maggi do I have in stock?"
        )
        assert not any(
            getattr(getattr(ev, "item", None), "name", "") == "create_escalation"
            for ev in result2.events
        ), "Routine stock queries must NOT invoke create_escalation."
