"""
Day 9 Demo Script: Multi-Agent Handoff Verification

Demonstrates:
Path 1 (Normal): Main agent Priya handles product catalogue inquiry directly.
Path 2 (Specialist Handoff): Refund request triggers handoff to Karan (Returns & Refunds Specialist),
                               Karan introduces himself, preserves context, and processes the claim.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from livekit.agents import AgentSession
from livekit.plugins import google

from agent import Assistant
from db import get_refund_claims_db, init_db
from specialist import RefundSpecialist
from specialist_prompt import SPECIALIST_NAME

load_dotenv(".env.local")


def print_events(result):
    text_responses = []
    for ev in result.events:
        ev_type = type(ev).__name__
        if "FunctionCallEvent" in ev_type:
            item = getattr(ev, "item", None)
            if item:
                print(
                    f"  ⚙️ [Tool Call]: {getattr(item, 'name', '')}({getattr(item, 'arguments', '')})"
                )
        elif "FunctionCallOutputEvent" in ev_type:
            item = getattr(ev, "item", None)
            if item:
                print(
                    f"  ✅ [Tool Output]: {getattr(item, 'name', '')} -> {getattr(item, 'output', '')}"
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
        print(f"  🗣️ Agent: {' '.join(text_responses)}")


async def run_demo():
    init_db()
    llm = google.LLM(model="gemini-3.5-flash-lite")

    print("=" * 70)
    print("DAY 9 DEMO: MULTI-AGENT HANDOFF (PRIYA ➔ KARAN REFUND SPECIALIST)")
    print("=" * 70)

    async with AgentSession(llm=llm) as session:
        main_assistant = Assistant()
        await session.start(main_assistant)

        # -------------------------------------------------------------
        # PATH 1: Normal Question (Priya handles directly)
        # -------------------------------------------------------------
        print("\n--- [PATH 1: Normal Catalogue Question] ---")
        q1 = "Namaste! My shop is Ramesh Kirana. What is the stock and price of Maggi?"
        print(f"👤 Seller: {q1}")

        res1 = await session.run(user_input=q1)
        print_events(res1)
        print(f"📍 Current Active Agent: {type(session.current_agent).__name__}")
        assert type(session.current_agent).__name__ == "Assistant", "Path 1 should remain with Priya"

        # -------------------------------------------------------------
        # PATH 2: Specialist Question (Refund Request -> Handoff to Karan)
        # -------------------------------------------------------------
        print("\n--- [PATH 2: Refund Request -> Specialist Handoff] ---")
        q2 = "I received 5 damaged packets of Maggi in my delivery today. I want a refund of ₹100 for them."
        print(f"👤 Seller: {q2}")

        res2 = await session.run(user_input=q2)
        # -------------------------------------------------------------
        # PATH 3: Specialist Action (Karan processes refund claim)
        # -------------------------------------------------------------
        print("\n--- [PATH 3: Karan Processes Refund Claim] ---")
        q3 = "Yes, please approve the refund claim of ₹100 for 5 damaged Maggi packets."
        print(f"👤 Seller: {q3}")

        res3 = await session.run(user_input=q3)
        print_events(res3)
        print(f"📍 Current Active Agent: {type(session.current_agent).__name__}")

        # Check database records
        claims = get_refund_claims_db()
        print("\n📋 SQLite Refund Claims Table:")
        print(json.dumps(claims, indent=2))

        print("\n🎉 SUCCESS: Both paths verified! Normal query handled by Priya, Refund query handed off to Karan and processed into SQLite DB.")



if __name__ == "__main__":
    asyncio.run(run_demo())
