import json
import logging

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
    tokenize,
)

try:
    from .agent_prompt import AGENT_NAME, get_system_prompt
    from .catalogue import calculate_order_total_data, lookup_product_data
    from .db import init_db, lookup_seller_db, save_seller_db
except ImportError:
    from agent_prompt import AGENT_NAME, get_system_prompt
    from catalogue import calculate_order_total_data, lookup_product_data
    from db import init_db, lookup_seller_db, save_seller_db

from livekit.plugins import deepgram, google, murf, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=get_system_prompt())

    @function_tool
    async def lookup_seller(self, context: RunContext, name_or_id: str) -> str:
        """Look up a returning seller's profile and saved facts in the database by their name or user ID.

        Use this tool when a seller starts a conversation or introduces themselves by name or ID.

        Args:
            name_or_id: The seller's name or user ID to search for.
        """
        logger.info(f"Looking up seller: {name_or_id}")
        record = lookup_seller_db(name_or_id)
        if not record:
            return f"No seller record found for '{name_or_id}'."
        return json.dumps(record, indent=2)

    @function_tool
    async def save_seller(
        self,
        context: RunContext,
        user_id: str,
        name: str,
        language_preference: str = "Hinglish",
        facts: str = "{}",
    ) -> str:
        """Save or update seller profile and learned facts to the SQLite database.

        MANDATORY: When a seller provides useful information, ask permission BEFORE calling this tool. If permission is granted, call this tool. If permission is denied, NEVER call this tool.

        Args:
            user_id: Unique identifier for the seller (e.g. seller ID, phone number, or name slug).
            name: Seller's name.
            language_preference: Preferred language (e.g. Hindi, English, Hinglish).
            facts: JSON string or text summary of facts (e.g. past_orders, usual_quantities, preferred_delivery_slot).
        """
        logger.info(f"Saving seller info for {name} ({user_id})")
        saved = save_seller_db(
            user_id=user_id,
            name=name,
            language_preference=language_preference,
            facts=facts,
        )
        return f"Successfully saved record for {saved['name']} (ID: {saved['user_id']}). Facts: {saved['facts']}"

    @function_tool
    async def lookup_product(self, context: RunContext, product_name: str) -> str:
        """Look up the latest available stock quantity and seller-approved price for a product in the Daily Bazaar catalogue.

        Use this tool whenever the seller or caller asks about product stock, availability, price, or inventory.

        Args:
            product_name: The name of the product to look up (e.g. 'Maggi', 'Amul Milk').
        """
        logger.info(f"Looking up product: {product_name}")
        res = lookup_product_data(product_name)
        return json.dumps(res, indent=2)

    @function_tool
    async def calculate_order_total(self, context: RunContext, items: str) -> str:
        """Calculate the total order value using seller-approved catalogue prices.

        Use this tool whenever the seller or caller asks for total bill, total amount, order value, or invoice amount.

        Args:
            items: JSON list of item objects or tuples e.g. '[{"name": "Maggi", "qty": 5}, {"name": "Amul Milk", "qty": 2}]' or '[["Maggi", 5], ["Amul Milk", 2]]'.
        """
        logger.info(f"Calculating order total for items: {items}")
        res = calculate_order_total_data(items)
        return json.dumps(res, indent=2)


server = AgentServer()


def prewarm(proc: JobProcess):
    init_db()
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name=AGENT_NAME)
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    logger.info(">>> before ctx.connect")
    try:
        await ctx.connect()
        logger.info(">>> ctx.connect succeeded")
    except Exception:
        logger.exception(">>> ctx.connect failed")
        raise

    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=google.LLM(model="gemini-3.5-flash-lite"),
        tts=murf.TTS(
            voice="Pooja",
            locale="en-IN",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    await session.start(
        agent=Assistant(),
        room=ctx.room,
    )


if __name__ == "__main__":
    cli.run_app(server)
