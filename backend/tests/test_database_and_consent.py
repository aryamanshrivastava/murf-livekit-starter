import tempfile
from pathlib import Path

import pytest
from livekit.agents import AgentSession, inference, llm

from agent import Assistant
from db import DEFAULT_DB_PATH, init_db, lookup_seller_db, save_seller_db


@pytest.fixture(autouse=True)
def clean_database():
    """Ensure a clean database for each test run."""
    if DEFAULT_DB_PATH.exists():
        DEFAULT_DB_PATH.unlink()
    init_db()
    yield
    if DEFAULT_DB_PATH.exists():
        DEFAULT_DB_PATH.unlink()


def test_db_crud():
    """Unit test for database CRUD operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_data.db"
        init_db(db_path)

        # Lookup non-existent record
        assert lookup_seller_db("ramesh_123", db_path=db_path) is None

        # Save record
        saved = save_seller_db(
            user_id="ramesh_123",
            name="Ramesh",
            language_preference="Hinglish",
            facts={
                "past_orders": ["10kg rice", "5kg sugar"],
                "usual_quantities": "10kg",
                "preferred_delivery_slot": "morning",
            },
            db_path=db_path,
        )
        assert saved["user_id"] == "ramesh_123"
        assert saved["name"] == "Ramesh"
        assert saved["facts"]["preferred_delivery_slot"] == "morning"

        # Lookup by user_id
        res_by_id = lookup_seller_db("ramesh_123", db_path=db_path)
        assert res_by_id is not None
        assert res_by_id["name"] == "Ramesh"
        assert res_by_id["facts"]["usual_quantities"] == "10kg"

        # Lookup by name
        res_by_name = lookup_seller_db("Ramesh", db_path=db_path)
        assert res_by_name is not None
        assert res_by_name["user_id"] == "ramesh_123"


def _llm() -> llm.LLM:
    return inference.LLM(model="openai/gpt-4.1-mini")


@pytest.mark.asyncio
async def test_agent_asks_consent_before_saving():
    """Evaluation verifying the agent asks caller consent before saving information for a new caller."""
    async with (
        _llm() as llm_inst,
        AgentSession(llm=llm_inst) as session,
    ):
        await session.start(Assistant())

        result = await session.run(
            user_input="Hello, my shop name is Suresh Store. Can you save my preferred delivery slot as morning?"
        )

        # Agent may acknowledge the request before calling the tool ("Let me check your profile first...").
        # Consume any leading chat message so the function call assertion is always on the right event.
        if result.events and type(result.events[0]).__name__ == "ChatMessageEvent":
            result.expect.next_event().is_message(role="assistant")

        # Handle lookup tool invocation then evaluate assistant's consent response
        result.expect.next_event().is_function_call()
        result.expect.next_event().is_function_call_output()
        await (
            result.expect.next_event()
            .is_message(role="assistant")
            .judge(
                llm_inst,
                intent="""
                The response must ask for explicit permission or confirmation before saving or remembering the user's details (e.g. 'Would you like me to remember your delivery slot preference?').
                """,
            )
        )


@pytest.mark.asyncio
async def test_returning_caller_greeting():
    """Evaluation verifying returning caller greeting and context continuation."""
    # Pre-populate database with Ramesh's profile
    save_seller_db(
        user_id="Ramesh",
        name="Ramesh",
        language_preference="Hinglish",
        facts={
            "past_orders": ["5kg cotton seeds"],
            "usual_quantities": "5kg",
            "preferred_delivery_slot": "morning",
        },
    )

    async with (
        _llm() as llm_inst,
        AgentSession(llm=llm_inst) as session,
    ):
        await session.start(Assistant())

        result = await session.run(user_input="Hello, my shop name is Ramesh.")

        # Handle lookup tool invocation then evaluate assistant's greeting
        result.expect.next_event().is_function_call()
        result.expect.next_event().is_function_call_output()
        await (
            result.expect.next_event()
            .is_message(role="assistant")
            .judge(
                llm_inst,
                intent="""
                Greets Ramesh by name (e.g. 'Namaste Ramesh' or 'Welcome back Ramesh') AND
                references at least one piece of their stored context, such as:
                - Past orders (cotton seeds or 5kg cotton seeds)
                - Preferred delivery slot (morning)
                - Usual quantities (5kg)

                Simply greeting by name without mentioning any stored context does NOT pass.
                The agent must demonstrate it has read and used the profile facts.
                """,
            )
        )
