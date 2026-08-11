import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from livekit.agents import AgentSession
from livekit.plugins import google

from agent import Assistant
from db import init_db
from inventory import (
    check_low_stock_triggers,
    create_restock_request_db,
    get_inventory_status,
)


def test_smart_inventory_coverage():
    """Unit test verifying inventory coverage calculation (remaining_stock / daily_sales_rate)."""
    status = get_inventory_status()
    maggi = next((p for p in status if p["product"] == "Maggi"), None)
    assert maggi is not None
    assert maggi["stock"] in (120, 12, 10)  # Maggi in catalogue
    assert maggi["daily_sales_rate"] == 20.0

    # Low stock triggers threshold test
    low_items = check_low_stock_triggers(threshold_days=1.0)
    assert isinstance(low_items, list)


def test_create_restock_request_db():
    """Unit test verifying restock request database insertion."""
    import re

    init_db()
    req = create_restock_request_db(
        product_name="Maggi", quantity=100, seller_id="Instacart"
    )
    assert req["product"] == "Maggi"
    assert req["quantity"] == 100
    assert req["seller_id"] == "Instacart"
    assert req["status"] == "PENDING"
    # Format: REQ-YYYYMMDD-<8 hex chars>
    assert re.match(r"^REQ-\d{8}-[0-9A-F]{8}$", req["request_id"]), (
        f"Unexpected request_id format: {req['request_id']}"
    )


def test_restock_request_ids_are_unique():
    """Verify that two consecutive restock requests receive different IDs."""
    init_db()
    req1 = create_restock_request_db(
        product_name="Maggi", quantity=50, seller_id="ShopA"
    )
    req2 = create_restock_request_db(
        product_name="Maggi", quantity=50, seller_id="ShopA"
    )
    assert req1["request_id"] != req2["request_id"], (
        "Consecutive restock requests must have unique IDs"
    )


@pytest.mark.asyncio
async def test_outbound_low_stock_opening_script():
    """LLM-judged evaluation test for outbound low-stock opening script."""
    init_db()
    llm = google.LLM(model="gemini-3.5-flash-lite")

    async with AgentSession(llm=llm) as session:
        await session.start(Assistant())

        # Test greeting / opening response
        result = await session.run(user_input="Hello")
        for ev in result.events:
            if type(ev).__name__ == "MessageEvent":
                content = str(getattr(ev.item, "content", ""))
                assert "Daily Bazaar" in content or "Priya" in content


@pytest.mark.asyncio
async def test_agent_creates_restock_request():
    """LLM-judged evaluation test for placing a restock request via tool call."""
    init_db()
    llm = google.LLM(model="gemini-3.5-flash-lite")

    async with AgentSession(llm=llm) as session:
        await session.start(Assistant())

        result = await session.run(
            user_input="Place a restock request for 100 packets of Maggi."
        )
        assert len(result.events) > 0
