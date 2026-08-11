import functools
import json
import logging
import time
from typing import Any, Optional

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
    from .inventory import create_restock_request_db
except ImportError:
    from agent_prompt import AGENT_NAME, get_system_prompt
    from catalogue import calculate_order_total_data, lookup_product_data
    from db import init_db, lookup_seller_db, save_seller_db
    from inventory import create_restock_request_db

from livekit.plugins import deepgram, google, murf, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# Shared Error Message Constants
ERR_SYSTEM_FAILURE = "Unable to complete request due to a system error. Please try again in a few moments."
ERR_MISSING_SHOP = "Seller profile is not available. Please identify the shop first."


def tool_error(
    message: str = ERR_SYSTEM_FAILURE, *, retryable: bool = True
) -> dict[str, Any]:
    """Return a consistent error payload for tool failures."""
    return {
        "success": False,
        "retryable": retryable,
        "message": message,
    }


def log_execution_time(func: Any) -> Any:
    """Decorator to measure and log tool execution time cleanly."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        try:
            return await func(*args, **kwargs)
        finally:
            elapsed_ms = (time.time() - start_time) * 1000
            # Exclude self (args[0]) and context (args[1] if present) for clean entity log output
            clean_args = args[2:] if len(args) >= 2 else ()
            log_args = [f"{a!r}" for a in clean_args] + [
                f"{k}={v!r}" for k, v in kwargs.items()
            ]
            arg_str = ", ".join(log_args)
            logger.info(
                "%s(%s) completed in %.2f ms", func.__name__, arg_str, elapsed_ms
            )

    return wrapper


def _cache_seller(context: RunContext, record: dict[str, Any]) -> None:
    """Cache the seller profile in session state for downstream tool access."""
    try:
        if hasattr(context, "session") and hasattr(context.session, "state"):
            context.session.state["seller"] = record
            context.session.state["seller_loaded"] = True
    except Exception as e:
        logger.warning("Unable to cache seller profile in session state: %s", e)


class Assistant(Agent):
    def __init__(
        self,
        outbound: bool = False,
        seller_name: Optional[str] = None,
        seller_phone: Optional[str] = None,
        product: Optional[str] = None,
        coverage_days: Optional[float] = None,
    ) -> None:
        self.outbound = outbound
        self.seller_name = seller_name
        self.seller_phone = seller_phone
        self.product = product
        self.coverage_days = coverage_days

        super().__init__(instructions=get_system_prompt())

    @function_tool
    @log_execution_time
    async def lookup_seller(
        self,
        context: RunContext,
        name_or_id: str,
    ) -> dict[str, Any]:
        """Retrieve a seller profile.
        Use this whenever the seller provides their shop name or seller ID.
        Never assume a seller exists without calling this tool.
        """
        logger.info("Looking up seller: %s", name_or_id)

        try:
            record = lookup_seller_db(name_or_id)

            if not record:
                return {
                    "success": True,
                    "found": False,
                    "profile_loaded": False,
                    "is_returning_seller": False,
                    "seller": None,
                }

            _cache_seller(context, record)

            return {
                "success": True,
                "found": True,
                "profile_loaded": True,
                "is_returning_seller": True,
                "seller": record,
                "facts": record.get("facts", {}) if isinstance(record, dict) else {},
            }
        except Exception:
            logger.exception(
                "Failed to lookup seller profile", extra={"name_or_id": name_or_id}
            )
            return {"found": False, **tool_error()}

    @function_tool
    @log_execution_time
    async def save_seller(
        self,
        context: RunContext,
        user_id: str,
        name: str,
        language_preference: str = "Hinglish",
        facts: str = "{}",
    ) -> dict[str, Any]:
        """Save or update seller profile and learned facts to the SQLite database.

        MANDATORY: When a seller provides useful information, ask permission BEFORE calling this tool. If permission is granted, call this tool. If permission is denied, NEVER call this tool.

        Args:
            user_id: Unique identifier for the seller (e.g. seller ID, phone number, or name slug).
            name: Seller's name.
            language_preference: Preferred language (e.g. Hindi, English, Hinglish).
            facts: JSON string representing key-value facts (e.g. '{"past_orders": "rice", "preferred_delivery_slot": "morning"}').
        """
        logger.info("Saving seller info for %s (%s)", name, user_id)
        try:
            facts_val: Any = facts or {}
            if isinstance(facts_val, str):
                try:
                    facts_val = json.loads(facts_val)
                except Exception:
                    facts_val = {"notes": facts_val}

            saved = save_seller_db(
                user_id=user_id,
                name=name,
                language_preference=language_preference,
                facts=facts_val,
            )

            if not saved or not isinstance(saved, dict):
                return {
                    "success": False,
                    "message": "Seller information could not be saved.",
                }

            _cache_seller(context, saved)

            return {
                "success": True,
                "message": f"Successfully saved record for {saved.get('name', name)} (ID: {saved.get('user_id', user_id)}).",
                "seller": saved,
            }
        except Exception:
            logger.exception(
                "Failed to save seller information",
                extra={"user_id": user_id, "name": name},
            )
            return tool_error()

    @function_tool
    @log_execution_time
    async def lookup_product(
        self, context: RunContext, product_name: str
    ) -> dict[str, Any]:
        """Look up the latest available stock quantity and seller-approved price for a product in the Daily Bazaar catalogue.

        Use this tool whenever the seller or caller asks about product stock, availability, price, or inventory.

        Args:
            product_name: The name of the product to look up (e.g. 'Maggi', 'Amul Milk').
        """
        logger.info(
            "Looking up product: %s", product_name, extra={"product": product_name}
        )
        try:
            res = lookup_product_data(product_name)

            if not res or not isinstance(res, dict):
                return {
                    "found": False,
                    **tool_error(
                        f"Unable to lookup product '{product_name}'. Please try again in a few moments."
                    ),
                }

            if res.get("available") is False or "error" in res:
                return {
                    "success": True,
                    "found": False,
                    "message": res.get(
                        "error", f"Product '{product_name}' not found in catalogue."
                    ),
                    **res,
                }

            return {
                "success": True,
                "found": True,
                "product": res["product"],
                "price": res["price"],
                "stock": res["stock"],
                "last_updated": res["last_updated"],
            }
        except Exception:
            logger.exception(
                "Failed to lookup product", extra={"product": product_name}
            )
            return {
                "found": False,
                **tool_error(
                    f"Unable to lookup product '{product_name}'. Please try again in a few moments."
                ),
            }

    @function_tool
    @log_execution_time
    async def calculate_order_total(
        self, context: RunContext, items: str
    ) -> dict[str, Any]:
        """Calculate the total order value using seller-approved catalogue prices.

        Use this tool whenever the seller or caller asks for total bill, total amount, order value, or invoice amount.

        Args:
            items: JSON list of item objects or tuples e.g. '[{"name": "Maggi", "qty": 5}, {"name": "Amul Milk", "qty": 2}]' or '[["Maggi", 5], ["Amul Milk", 2]]'.
        """
        logger.info(
            "Calculating order total for items: %s", items, extra={"items": items}
        )
        try:
            res = calculate_order_total_data(items)

            if not res or not isinstance(res, dict):
                return tool_error("Unable to calculate order total.")
            return {
                "success": True,
                **res,
            }
        except Exception:
            logger.exception("Failed to calculate order total", extra={"items": items})
            return tool_error()

    @function_tool
    @log_execution_time
    async def create_restock_request(
        self,
        context: RunContext,
        seller_id: str,
        product_name: str,
        quantity: int = 100,
    ) -> dict[str, Any]:
        """Record a restock request for a product with a specified quantity.

        Use this tool when a seller asks to place a restock request or reorder low-stock inventory.

        Args:
            seller_id: Seller ID or shop name placing the restock request (obtained from lookup_seller or conversation).
            product_name: Name of the product to restock (e.g. 'Maggi').
            quantity: Quantity/packets requested (e.g. 100).
        """
        # Fallback to session state seller_id if empty
        if not seller_id:
            try:
                if hasattr(context, "session") and hasattr(context.session, "state"):
                    seller_state = context.session.state.get("seller", {})
                    seller_id = seller_state.get("user_id") or seller_state.get(
                        "name", ""
                    )
            except Exception as e:
                logger.warning("Unable to retrieve cached seller profile: %s", e)

        if not seller_id:
            return {
                "success": False,
                "message": ERR_MISSING_SHOP,
            }

        logger.info(
            "Creating restock request for %s x %s for %s",
            product_name,
            quantity,
            seller_id,
            extra={"product": product_name, "seller": seller_id, "quantity": quantity},
        )
        try:
            res = create_restock_request_db(
                product_name=product_name,
                quantity=quantity,
                seller_id=seller_id,
            )

            if not res or not isinstance(res, dict):
                return tool_error(
                    f"Unable to create restock request for '{product_name}'.",
                    retryable=False,
                )
            return {
                "success": True,
                **res,
            }
        except Exception:
            logger.exception(
                "Failed to create restock request",
                extra={"product": product_name, "seller": seller_id},
            )
            return tool_error(
                f"Unable to create restock request for '{product_name}'. Please try again in a few moments."
            )


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

    logger.info(
        "Connecting to LiveKit room %s",
        ctx.room.name,
        extra={"room": ctx.room.name},
    )
    try:
        await ctx.connect()
        logger.info(
            "Connected to LiveKit room %s",
            ctx.room.name,
            extra={"room": ctx.room.name},
        )
    except Exception:
        logger.exception(
            "Failed to connect to LiveKit room %s",
            ctx.room.name,
            extra={"room": ctx.room.name},
        )
        raise

    # Extract room/job metadata if provided
    metadata: dict[str, Any] = {}
    if getattr(ctx.room, "metadata", None):
        try:
            metadata = json.loads(ctx.room.metadata)
        except Exception as e:
            logger.warning("Could not parse room metadata: %s", e)
    elif getattr(ctx, "job", None) and getattr(ctx.job, "metadata", None):
        try:
            metadata = json.loads(ctx.job.metadata)
        except Exception as e:
            logger.warning("Could not parse job metadata: %s", e)

    assistant = Assistant(
        outbound=metadata.get("outbound", False),
        seller_name=metadata.get("seller_name"),
        seller_phone=metadata.get("seller_phone"),
        product=metadata.get("product"),
        coverage_days=metadata.get("coverage_days"),
    )

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
        agent=assistant,
        room=ctx.room,
    )

    if assistant.outbound:
        seller_str = assistant.seller_name or "there"
        prod_str = assistant.product or "your inventory item"
        await session.generate_reply(
            instructions=f"""
Start immediately.

Say:

Hello {seller_str}.

This is Priya from Daily Bazaar.

Your stock of {prod_str} is running low.

Would you like me to place a restock request?
"""
        )
    else:
        await session.generate_reply(
            instructions="""
Say exactly:

Namaste! Main Priya hoon, Daily Bazaar ki seller assistant.

Before we get started, could you please tell me your shop name so I can access your business profile?
"""
        )

    logger.info(
        "Voice session started successfully for room %s",
        ctx.room.name,
        extra={"room": ctx.room.name},
    )


if __name__ == "__main__":
    cli.run_app(server)
