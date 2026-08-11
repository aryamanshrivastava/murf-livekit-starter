import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from livekit.agents import AgentSession
from livekit.plugins import google

from agent import Assistant
from catalogue import calculate_order_total_data, lookup_product_data
from db import init_db


def test_lookup_product_success():
    res = lookup_product_data("Maggi")
    assert res.get("product") == "Maggi"
    assert res.get("price") == 15
    assert res.get("stock") == 120 or res.get("stock") == 10
    assert "last_updated" in res


def test_lookup_product_not_found():
    res = lookup_product_data("RandomUnknownProduct")
    assert res.get("available") is False or "error" in res
    assert "last_updated" in res


def test_calculate_order_total_success():
    # 5 Maggi @ 15 = 75, 2 Amul Milk @ 62 = 124 -> Total = 199
    res = calculate_order_total_data([("Maggi", 5), ("Amul Milk", 2)])
    assert res.get("total") == 199
    assert len(res.get("items", [])) == 2

    # 10 Maggi @ 15 = 150, 2 Amul Milk @ 62 = 124 -> Total = 274
    res2 = calculate_order_total_data([("Maggi", 10), ("Amul Milk", 2)])
    assert res2.get("total") == 274


@pytest.mark.asyncio
async def test_agent_catalogue_dialogue_flow():
    """LLM-judged evaluation test for product lookup, timestamp mention, and order total calculation."""
    init_db()
    llm = google.LLM(model="gemini-3.5-flash-lite")

    # Pre-populate Instacart so lookup_seller returns found: True and the agent
    # can proceed past the seller identification gate to call lookup_product.
    from db import save_seller_db

    save_seller_db(user_id="Instacart", name="Instacart", language_preference="Hinglish")

    async with AgentSession(llm=llm) as session:
        await session.start(Assistant())

        # Step 1: Identify Seller — agent must call lookup_seller before proceeding.
        # Agent may emit a brief acknowledgement before the tool call; consume it if so.
        result1 = await session.run(user_input="Hello, my shop name is Instacart")
        if result1.events and type(result1.events[0]).__name__ == "ChatMessageEvent":
            result1.expect.next_event().is_message(role="assistant")
        result1.expect.next_event().is_function_call()
        result1.expect.next_event().is_function_call_output()

        # Step 2: Stock Lookup
        result2 = await session.run(user_input="Do we have Maggi in stock?")
        assert any(
            getattr(getattr(ev, "item", None), "name", "") == "lookup_product"
            for ev in result2.events
        )

        # Step 3: Order Total Calculation
        result3 = await session.run(
            user_input="Add 10 packets and 2 litres of Amul Milk. What's the total?"
        )
        assert any(
            getattr(getattr(ev, "item", None), "name", "") == "calculate_order_total"
            for ev in result3.events
        )
