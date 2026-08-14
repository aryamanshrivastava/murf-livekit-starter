import logging
from typing import Any, Optional

from livekit.agents import Agent, RunContext, function_tool, tokenize
from livekit.plugins import murf

try:
    from .db import create_refund_claim_db
    from .specialist_prompt import SPECIALIST_NAME, get_specialist_prompt
except ImportError:
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

        super().__init__(instructions=get_specialist_prompt(), tts=tts)

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
