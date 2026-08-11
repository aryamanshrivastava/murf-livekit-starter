import datetime
import uuid
from pathlib import Path
from typing import Any, Optional

try:
    from .catalogue import load_catalogue
    from .db import DEFAULT_DB_PATH, get_db
except ImportError:
    from catalogue import load_catalogue
    from db import DEFAULT_DB_PATH, get_db

# Default daily sales velocity for products (units / day)
LOW_STOCK_THRESHOLD_DAYS = 1.0
DEFAULT_SALES_VELOCITY = {
    "maggi": 20.0,
    "amul milk": 40.0,
    "fortune oil": 15.0,
    "aashirvaad atta": 10.0,
}


def get_inventory_status(
    catalogue_path: Optional[Path] = None,
) -> list[dict[str, Any]]:
    """Calculate stock, daily sales rate, and coverage days for products."""
    cat = load_catalogue(catalogue_path)
    products = cat.get("products", [])
    results = []

    for p in products:
        name = p.get("name", "").strip()
        stock = p.get("stock", 0)
        daily_sales = DEFAULT_SALES_VELOCITY.get(name.lower(), 10.0)
        coverage_days = round(stock / daily_sales, 2) if daily_sales > 0 else 999.0

        results.append(
            {
                "seller_id": p.get("seller_id", "Instacart"),
                "product": name,
                "stock": stock,
                "daily_sales_rate": daily_sales,
                "coverage_days": coverage_days,
                "is_low_stock": coverage_days < LOW_STOCK_THRESHOLD_DAYS,
            }
        )
    return results


def check_low_stock_triggers(
    threshold_days: float = LOW_STOCK_THRESHOLD_DAYS,
    catalogue_path: Optional[Path] = None,
) -> list[dict[str, Any]]:
    """Identify products with inventory coverage below threshold_days."""
    status = get_inventory_status(catalogue_path)
    return [item for item in status if item["coverage_days"] < threshold_days]


def init_restock_table(db_path: Optional[Path] = None) -> None:
    """Initialize the restock_requests table in SQLite."""
    with get_db(db_path) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS restock_requests (
                request_id TEXT PRIMARY KEY,
                seller_id TEXT NOT NULL,
                product TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def create_restock_request_db(
    product_name: str,
    seller_id: str,
    quantity: int = 100,
    db_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Save a new restock request to SQLite database."""
    target_path = db_path or DEFAULT_DB_PATH
    init_restock_table(target_path)

    product_name = product_name.strip()
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    now = datetime.datetime.now(datetime.timezone.utc)
    now_iso = now.isoformat()
    status = "PENDING"

    date_str = now.strftime("%Y%m%d")
    req_id = f"REQ-{date_str}-{uuid.uuid4().hex[:8].upper()}"

    with get_db(target_path) as conn, conn:
        conn.execute(
            """
            INSERT INTO restock_requests (request_id, seller_id, product, quantity, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (req_id, seller_id, product_name, quantity, status, now_iso),
        )

    return {
        "request_id": req_id,
        "seller_id": seller_id,
        "product": product_name,
        "quantity": quantity,
        "status": status,
        "created_at": now_iso,
    }
