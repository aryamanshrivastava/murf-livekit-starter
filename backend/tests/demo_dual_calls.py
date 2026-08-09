import asyncio

from livekit.agents import AgentSession, inference, llm

from agent import Assistant
from db import DEFAULT_DB_PATH, init_db, lookup_caller_db


def _llm() -> llm.LLM:
    return inference.LLM(model="openai/gpt-4.1-mini")


def print_result_events(result):
    for event in result.events:
        event_type = type(event).__name__
        if event_type == "FunctionCallEvent":
            print(
                f"  [Tool Call]: {getattr(event.item, 'name', '')}({getattr(event.item, 'arguments', '')})"
            )
        elif event_type == "FunctionCallOutputEvent":
            print(
                f"  [Tool Output]: {getattr(event.item, 'name', '')} -> {getattr(event.item, 'output', '')}"
            )
        elif event_type == "ChatMessageEvent":
            role = getattr(event.item, "role", "")
            if role == "assistant":
                content = getattr(event.item, "content", "")
                if isinstance(content, list):
                    content = "".join(content)
                print(f"Agent: {content}\n")


async def run_demo():
    # 1. Clean previous database state
    if DEFAULT_DB_PATH.exists():
        DEFAULT_DB_PATH.unlink()
    init_db()

    print("==================================================")
    print("DEMO: DAY 4 CALLER MEMORY & EXPLICIT CONSENT FLOW")
    print("==================================================\n")

    # --------------------------------------------------
    # CALL 1: NEW CALLER (Ramesh)
    # --------------------------------------------------
    print("--- CALL 1 START: New Caller (Ramesh) ---")
    async with _llm() as llm_inst, AgentSession(llm=llm_inst) as session:
        await session.start(Assistant())

        # Step 1: User introduces themselves with order & delivery slot preference
        user_msg = "Namaste! My name is Ramesh. I want to order 10kg Rice and I prefer morning delivery."
        print(f"User: {user_msg}")

        result1 = await session.run(user_input=user_msg)
        print_result_events(result1)

        # Step 2: User consents to saving details
        consent_msg = (
            "Yes, please save my name and morning delivery preference for next time."
        )
        print(f"User: {consent_msg}")

        result2 = await session.run(user_input=consent_msg)
        print_result_events(result2)

    print("--- CALL 1 END ---\n")

    # Verify DB content after Call 1
    db_record = lookup_caller_db("Ramesh")
    print("--------------------------------------------------")
    print(f"DB Record in SQLite after Call 1:\n{db_record}")
    print("--------------------------------------------------\n")

    # --------------------------------------------------
    # CALL 2: RETURNING CALLER (Ramesh)
    # --------------------------------------------------
    print("--- CALL 2 START: Returning Caller (Ramesh) ---")
    async with _llm() as llm_inst, AgentSession(llm=llm_inst) as session:
        await session.start(Assistant())

        # Step 1: Returning user connects and greets
        user_msg2 = "Namaste, this is Ramesh again!"
        print(f"User: {user_msg2}")

        result3 = await session.run(user_input=user_msg2)
        print_result_events(result3)

    print("--- CALL 2 END ---")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(run_demo())
