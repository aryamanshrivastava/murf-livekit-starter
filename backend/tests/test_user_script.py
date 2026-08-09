import asyncio
from livekit.agents import AgentSession, inference, llm
from agent import Assistant
from db import DEFAULT_DB_PATH, init_db, lookup_seller_db


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
                print(f"Priya: {content}\n")


async def run_user_script_test():
    # 1. Clean previous database state
    if DEFAULT_DB_PATH.exists():
        DEFAULT_DB_PATH.unlink()
    init_db()

    print("==================================================")
    print("TESTING USER SCRIPT FOR CALL 1 & CALL 2")
    print("==================================================\n")

    # --------------------------------------------------
    # CALL 1: NEW SELLER (Dialy Bazaar)
    # --------------------------------------------------
    print("--- CALL 1: New Seller ---")
    async with _llm() as llm_inst, AgentSession(llm=llm_inst) as session:
        await session.start(Assistant())

        # Turn 1: Seller says "Hello"
        print("Seller: Hello")
        res1 = await session.run(user_input="Hello")
        print_result_events(res1)

        # Turn 2: Seller provides shop name "Dialy Bazaar"
        print("Seller: Dialy Bazaar")
        res2 = await session.run(user_input="Dialy Bazaar")
        print_result_events(res2)

        # Turn 3: Seller specifies language "Hinglish"
        print("Seller: Hinglish")
        res3 = await session.run(user_input="Hinglish")
        print_result_events(res3)

        # Turn 4: Seller confirms consent "Yes"
        print("Seller: Yes")
        res4 = await session.run(user_input="Yes")
        print_result_events(res4)

    print("--- CALL 1 END ---\n")

    # Inspect SQLite database record
    db_record = lookup_seller_db("Dialy Bazaar")
    print("--------------------------------------------------")
    print(f"DB Record in SQLite after Call 1:\n{db_record}")
    print("--------------------------------------------------\n")

    # --------------------------------------------------
    # CALL 2: RETURNING SELLER (Dialy Bazaar)
    # --------------------------------------------------
    print("--- CALL 2: Returning Seller ---")
    async with _llm() as llm_inst, AgentSession(llm=llm_inst) as session:
        await session.start(Assistant())

        # Turn 1: Returning seller connects and greets
        print("Seller: Hello, this is Dialy Bazaar!")
        res_c2 = await session.run(user_input="Hello, this is Dialy Bazaar!")
        print_result_events(res_c2)

    print("--- CALL 2 END ---")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(run_user_script_test())
