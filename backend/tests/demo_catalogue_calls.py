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


async def run_demo():
    print("=" * 60)
    print("DEMO CONVERSATION: PRODUCT CATALOGUE & ORDER TOTAL")
    print("=" * 60)

    init_db()
    llm = google.LLM(model="gemini-3.5-flash-lite")

    async with AgentSession(llm=llm) as session:
        await session.start(Assistant())

        # Turn 1: Seller Identification
        print("\nSeller: Instacart")
        result1 = await session.run(user_input="Instacart")
        print_run_events(result1)
        await asyncio.sleep(2)

        # Turn 2: Stock Inquiry
        print("\nSeller: Do we have Maggi in stock?")
        result2 = await session.run(user_input="Do we have Maggi in stock?")
        print_run_events(result2)
        await asyncio.sleep(2)

        # Turn 3: Order Total Calculation
        print("\nSeller: Add 10 packets and 2 litres of Amul Milk. What's the total?")
        result3 = await session.run(
            user_input="Add 10 packets and 2 litres of Amul Milk. What's the total?"
        )
        print_run_events(result3)
        await asyncio.sleep(2)

        # Turn 4: Thanks
        print("\nSeller: Thanks.")
        result4 = await session.run(user_input="Thanks.")
        print_run_events(result4)

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(run_demo())
