import tempfile
from pathlib import Path

import pytest
from livekit.agents import AgentSession, inference, llm

from agent import Assistant
from db import DEFAULT_DB_PATH, init_db, lookup_caller_db, save_caller_db


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
        assert lookup_caller_db("ramesh_123", db_path=db_path) is None

        # Save record
        saved = save_caller_db(
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
        res_by_id = lookup_caller_db("ramesh_123", db_path=db_path)
        assert res_by_id is not None
        assert res_by_id["name"] == "Ramesh"
        assert res_by_id["facts"]["usual_quantities"] == "10kg"

        # Lookup by name
        res_by_name = lookup_caller_db("Ramesh", db_path=db_path)
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
            user_input="Hi, my name is Suresh and my preferred delivery slot is morning."
        )

        # Handle lookup tool invocation then evaluate assistant's consent response
        result.expect.next_event().is_function_call()
        result.expect.next_event().is_function_call_output()
        await (
            result.expect.next_event()
            .is_message(role="assistant")
            .judge(
                llm_inst,
                intent="""
                The response must ask for explicit permission/consent to save or remember the user's name/delivery preference (e.g. 'Kya main yeh details save kar doon?').
                It should NOT claim to have saved the data without asking first.
                """,
            )
        )


@pytest.mark.asyncio
async def test_returning_caller_greeting():
    """Evaluation verifying returning caller greeting and context continuation."""
    # Pre-populate database with Ramesh's profile
    save_caller_db(
        user_id="ramesh_123",
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

        result = await session.run(user_input="Hello, this is Ramesh again.")

        # Handle lookup tool invocation then evaluate assistant's greeting
        result.expect.next_event().is_function_call()
        result.expect.next_event().is_function_call_output()
        await (
            result.expect.next_event()
            .is_message(role="assistant")
            .judge(
                llm_inst,
                intent="""
                Greets Ramesh by name (e.g. 'Namaste Ramesh' or 'Welcome back Ramesh') and references past context such as past orders (cotton seeds), delivery slot (morning), or asks how to assist today.
                """,
            )
        )
