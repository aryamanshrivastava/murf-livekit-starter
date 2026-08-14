import logging
from typing import Any, Optional

from livekit.agents import Agent, RunContext, function_tool, tokenize
from livekit.plugins import murf

try:
    from .catalogue import lookup_product_data
    from .db import create_refund_claim_db
    from .specialist_prompt import SPECIALIST_NAME, get_specialist_prompt
except ImportError:
    from catalogue import lookup_product_data
    from db import create_refund_claim_db
    from specialist_prompt import SPECIALIST_NAME, get_specialist_prompt

logger = logging.getLogger("agent.specialist")


class RefundSpecialist(Agent):
    """Karan - Returns & Refunds Specialist Agent."""

    def __init__(
        self,
        seller_id: Optional[str] = None,
        product_name: Optional[str] = None,
        issue_details: Optional[str] = None,
        chat_ctx: Optional[Any] = None,
        tts: Optional[Any] = None,
    ) -> None:
        self.name = SPECIALIST_NAME
        self.seller_id = seller_id
        self.product_name = product_name
        self.issue_details = issue_details
        self.seller_identified = True
        self.business_action_completed = False

        if tts is None:
            tts = murf.TTS(
                voice="Samar",
                locale="en-IN",
                style="Conversation",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True,
            )

        super().__init__(instructions=get_specialist_prompt(), chat_ctx=chat_ctx, tts=tts)

    async def on_enter(self) -> None:
        """Triggered automatically by LiveKit when Karan takes over the conversation."""
        if hasattr(self, "session") and self.session:
            issue_info = f" ({self.issue_details})" if self.issue_details else ""
            self.session.generate_reply(
                instructions=(
                    f"You are Karan, Returns & Refunds Specialist. "
                    f"You have just taken over the call from Priya for seller {self.seller_id or 'the seller'}{issue_info}. "
                    f"Greet them politely as Karan in Hindi/Hinglish (e.g. 'Namaste! Main Karan hoon, Daily Bazaar ka Returns specialist.'), "
                    f"acknowledge their return/refund issue immediately based on conversation context, "
                    "and ask how you can assist them."
                )
            )

    @function_tool
    async def lookup_product(
        self,
        context: RunContext,
        product_name: str,
    ) -> dict[str, Any]:
        """Look up product unit price and available stock in the catalogue to calculate refund or return values accurately.

        Args:
            product_name: Product name to search (e.g. 'Maggi', 'Amul Milk', 'Fortune Oil', 'Aashirvaad Atta').
        """
        return lookup_product_data(product_name)

    @function_tool
    async def handoff_to_main_assistant(
        self,
        context: RunContext,
        reason: str = "",
    ) -> dict[str, Any]:
        """Hand off the conversation back to Priya, Daily Bazaar's main seller assistant.

        MANDATORY: Call this tool whenever:
        - The seller asks about standard product catalogue, prices, order placement, or restock requests.
        - The return/refund claim process is completed and the seller wants to return to standard shopping/inquiries.
        - The seller explicitly asks to speak with Priya or return to the main assistant.

        Args:
            reason: Why the handoff back to Priya is occurring (e.g. 'Seller finished refund claim and wants to place new order').
        """
        try:
            from .agent import Assistant
        except ImportError:
            from agent import Assistant

        logger.info(
            "Handoff back to main assistant (Priya) for %s. Reason: %s",
            self.seller_id or "seller",
            reason or "User query/request",
        )

        seller_id = self.seller_id
        if not seller_id:
            try:
                if hasattr(context, "session") and hasattr(context.session, "state"):
                    seller_state = context.session.state.get("seller", {})
                    if isinstance(seller_state, dict):
                        seller_id = seller_state.get("name") or seller_state.get("user_id", "")
            except Exception:
                pass

        assistant = Assistant(
            seller_name=seller_id,
            seller_identified=True,
            chat_ctx=self.chat_ctx,
            is_handoff_return=True,
        )

        if hasattr(context, "session") and hasattr(context.session, "update_agent"):
            context.session.update_agent(assistant)
            if hasattr(context.session, "generate_reply"):
                import asyncio

                async def _priya_speak_greeting():
                    await asyncio.sleep(0.15)
                    try:
                        context.session.generate_reply(
                            instructions=(
                                f"You are Priya, Daily Bazaar's main seller assistant. "
                                f"You have just taken the call back from Karan for seller {seller_id or 'the seller'}. "
                                f"The seller is ALREADY identified as {seller_id or 'the seller'}. "
                                "Do NOT ask for their shop name again under any circumstances! "
                                "Welcome the seller back warmly, acknowledge that Karan handled their return/refund claim, "
                                "and ask how you can help them with their catalogue, new orders, or kirana store business."
                            )
                        )
                    except Exception as err:
                        logger.warning("Unable to trigger automatic speech greeting for Priya: %s", err)

                _task = asyncio.create_task(_priya_speak_greeting())  # noqa: RUF006

        return {
            "success": True,
            "handoff": True,
            "agent": "Priya",
            "seller_id": seller_id or "",
            "announcement": "Main aapko wapas Priya se connect kar raha hoon.",
            "message": "Transferred back to Priya, Daily Bazaar Main Assistant.",
        }

    @function_tool
    async def process_refund_claim(
        self,
        context: RunContext,
        seller_id: str,
        product_name: str,
        issue_type: str,
        refund_amount: float = 0.0,
        claim_reason: str = "",
    ) -> dict[str, Any]:
        """Process a product return claim and issue a refund or credit voucher for a seller.

        Use this tool when a seller confirms damaged stock, expired goods, or missing items
        and requests a refund or store credit.

        Args:
            seller_id: Shop name or seller ID (e.g. 'Ramesh Kirana').
            product_name: Name of product damaged or returned (e.g. 'Maggi').
            issue_type: Category of issue ('damaged_goods', 'expired_stock', 'incorrect_billing', or 'missing_items').
            refund_amount: Amount in INR to be refunded or credited (e.g. 250.0).
            claim_reason: Summary description of claim reason.
        """
        # Fallback to cached seller ID if empty
        if not seller_id and hasattr(self, "seller_id") and self.seller_id:
            seller_id = self.seller_id

        if not seller_id:
            try:
                if hasattr(context, "session") and hasattr(context.session, "state"):
                    seller_state = context.session.state.get("seller", {})
                    if isinstance(seller_state, dict):
                        seller_id = seller_state.get("name") or seller_state.get("user_id", "")
            except Exception:
                pass

        if not seller_id:
            seller_id = "General Seller"

        logger.info(
            "Processing refund claim for %s: %s (%s - ₹%.2f)",
            seller_id,
            product_name,
            issue_type,
            refund_amount,
        )

        try:
            claim = create_refund_claim_db(
                seller_id=seller_id,
                product_name=product_name,
                issue_type=issue_type,
                refund_amount=refund_amount,
                claim_reason=claim_reason or f"Return claim for {product_name}",
            )

            self.business_action_completed = True

            return {
                "success": True,
                "claim_id": claim["claim_id"],
                "status": "APPROVED",
                "seller_id": seller_id,
                "product_name": product_name,
                "refund_amount": claim["refund_amount"],
                "message": f"Refund claim approved with Reference ID: {claim['claim_id']}.",
            }
        except Exception as e:
            logger.exception("Failed to process refund claim: %s", e)
            return {
                "success": False,
                "message": "Unable to process refund claim. Please try again in a few moments.",
            }
