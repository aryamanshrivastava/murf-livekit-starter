import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from livekit.agents import AgentSession
from livekit.plugins import google

from agent import Assistant
from db import init_db

load_dotenv(".env.local")


def print_run_events(result):
    text_responses = []
    for ev in result.events:
        ev_type = type(ev).__name__
        if "FunctionCallEvent" in ev_type:
            item = getattr(ev, "item", None)
            if item:
                print(
                    f"  [Tool Call]: {getattr(item, 'name', '')}({getattr(item, 'arguments', '')})"
                )
        elif "FunctionCallOutputEvent" in ev_type:
            item = getattr(ev, "item", None)
            if item:
                print(
                    f"  [Tool Output]: {getattr(item, 'name', '')} -> {getattr(item, 'output', '')}"
                )
        elif "MessageEvent" in ev_type:
            item = getattr(ev, "item", None)
            if item:
                raw_content = getattr(item, "content", "")
                if isinstance(raw_content, list):
                    text_str = "".join(
                        str(c)
                        for c in raw_content
                        if not hasattr(c, "type") or c.type == "text"
                    )
                else:
                    text_str = str(raw_content)
                if text_str:
                    text_responses.append(text_str)
    if text_responses:
        print(f"Priya: {' '.join(text_responses)}")


async def run_outbound_demo():
    print("=" * 60)
    print("DEMO CONVERSATION: OUTBOUND LOW-STOCK & RESTOCK REQUEST")
    print("=" * 60)

    init_db()
    llm = google.LLM(model="gemini-3.5-flash-lite")

    async with AgentSession(llm=llm) as session:
        await session.start(Assistant())

        # Step 1: Outbound Call Initial Greeting
        print("\n[Outbound Call Connected]")
        result1 = await session.run(user_input="[Call Picked Up]")
        print_run_events(result1)
        await asyncio.sleep(2)

        # Step 2: Seller Places Restock Request
        print("\nSeller: Place a restock request.")
        result2 = await session.run(user_input="Place a restock request.")
        print_run_events(result2)
        await asyncio.sleep(2)

        # Step 3: Thanks
        print("\nSeller: Thanks.")
        result3 = await session.run(user_input="Thanks.")
        print_run_events(result3)

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(run_outbound_demo())
