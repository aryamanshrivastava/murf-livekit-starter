import argparse
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from dotenv import load_dotenv

try:
    from .db import lookup_seller_db
    from .inventory import check_low_stock_triggers
except ImportError:
    from db import lookup_seller_db
    from inventory import check_low_stock_triggers

logger = logging.getLogger("outbound_trigger")
load_dotenv(".env.local")


def launch_livekit_outbound(
    seller_phone: str,
    seller_name: str,
    product: str,
    coverage_days: float,
) -> dict[str, Any]:
    """Launch or queue a LiveKit outbound voice agent room with seller & product metadata.

    Note: In a telephony production system, a SIP/PSTN trunk or client app bridges the seller into this room.
    """
    url = os.getenv("LIVEKIT_URL", "").strip()
    api_key = os.getenv("LIVEKIT_API_KEY", "").strip()
    api_secret = os.getenv("LIVEKIT_API_SECRET", "").strip()

    payload = {
        "status": "queued",
        "seller_name": seller_name,
        "seller_phone": seller_phone,
        "product": product,
        "coverage_days": coverage_days,
    }

    if url and api_key and api_secret and not url.startswith("dummy"):
        try:
            import asyncio
            import time
            import uuid

            from livekit import api

            metadata = {
                "outbound": True,
                "seller_name": seller_name,
                "seller_phone": seller_phone,
                "product": product,
                "coverage_days": coverage_days,
            }

            async def _create_room_and_dispatch():
                lk_api = api.LiveKitAPI(url, api_key, api_secret)
                try:
                    room_name = f"outbound-{int(time.time())}-{uuid.uuid4().hex[:6]}"
                    metadata_str = json.dumps(metadata)

                    # 1. Create LiveKit Room
                    await lk_api.room.create_room(
                        api.CreateRoomRequest(
                            name=room_name,
                            metadata=metadata_str,
                        )
                    )
                    logger.info("Created room %s", room_name)

                    # 2. Dispatch Priya Agent
                    try:
                        await lk_api.agent_dispatch.create_dispatch(
                            api.CreateAgentDispatchRequest(
                                room=room_name,
                                agent_name="Priya",
                                metadata=metadata_str,
                            )
                        )
                        logger.info("Priya dispatched to %s", room_name)
                    except Exception as dispatch_err:
                        logger.warning(
                            "Agent dispatch notice for %s: %s", room_name, dispatch_err
                        )

                    return room_name
                finally:
                    await lk_api.aclose()

            try:
                asyncio.get_running_loop()
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    room_name = pool.submit(
                        asyncio.run, _create_room_and_dispatch()
                    ).result()
            except RuntimeError:
                room_name = asyncio.run(_create_room_and_dispatch())

            payload.update(
                {
                    "status": "calling",
                    "caller": "Priya",
                    "caller_id": "Daily Bazaar",
                    "provider": "livekit",
                    "call_id": room_name,
                    "room_name": room_name,
                    "seller_name": seller_name,
                    "seller_phone": seller_phone,
                    "product": product,
                    "coverage_days": coverage_days,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            logger.info(
                "📞 Incoming call from Priya (Daily Bazaar) for seller %s | Product: %s | Room: %s",
                seller_name,
                product,
                room_name,
            )
        except Exception:
            logger.exception("LiveKit room creation and dispatch failed")
            raise

    return payload


def run_inventory_scan_and_trigger(
    threshold_days: float = 1.0,
    fallback_phone: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Scan inventory coverage and trigger outbound LiveKit agent calls for low-stock items.

    Phone numbers are read from the seller database (phone column).
    If no phone is stored for a seller, falls back to fallback_phone if provided,
    otherwise skips the call and logs a warning.
    """
    low_stock_items = check_low_stock_triggers(threshold_days=threshold_days)
    results = []

    if not low_stock_items:
        logger.info("No products found with coverage < %s days.", threshold_days)
        return results

    for item in low_stock_items:
        prod = item["product"]
        coverage = item["coverage_days"]

        # Seller lookup uses seller_id if available in catalogue/inventory item, default to Instacart.
        seller_id = item.get("seller_id", "Instacart")
        seller_record = lookup_seller_db(seller_id)

        seller_phone = (
            seller_record["phone"]
            if seller_record and seller_record.get("phone")
            else fallback_phone
        )

        seller_name = seller_record["name"] if seller_record else "there"

        logger.info(
            "LOW STOCK ALERT",
            extra={
                "seller": seller_name,
                "product": prod,
                "coverage_days": coverage,
            },
        )

        if not seller_phone:
            logger.warning(
                "No phone number available for product '%s'. Skipping outbound call.",
                prod,
                extra={"product": prod},
            )
            results.append(
                {
                    "item": item,
                    "call_result": {
                        "status": "skipped",
                        "reason": "No phone number available for this seller.",
                        "product": prod,
                    },
                }
            )
            continue

        try:
            call_res = launch_livekit_outbound(
                seller_phone=seller_phone,
                seller_name=seller_name,
                product=prod,
                coverage_days=coverage,
            )
        except Exception as e:
            logger.error("Error triggering outbound call: %s", e)
            call_res = {
                "status": "failed",
                "reason": str(e),
                "product": prod,
            }

        results.append({"item": item, "call_result": call_res})

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(
        description="Daily Bazaar Outbound Low-Stock Call Trigger"
    )
    parser.add_argument(
        "--phone",
        type=str,
        default=None,
        help="Fallback seller phone number (used if DB has no phone for the seller)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=1.0,
        help="Low stock coverage threshold in days (default: 1.0)",
    )
    args = parser.parse_args()

    logger.info(
        "Inventory scan started",
        extra={
            "started_at": datetime.now(timezone.utc).isoformat(),
            "threshold_days": args.threshold,
        },
    )
    res = run_inventory_scan_and_trigger(
        threshold_days=args.threshold,
        fallback_phone=args.phone,
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))
