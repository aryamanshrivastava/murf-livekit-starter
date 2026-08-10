import json
from pathlib import Path
from typing import Any, Optional, Union

DEFAULT_CATALOGUE_PATH = Path(__file__).parent.parent / "data" / "catalogue.json"


def load_catalogue(catalogue_path: Optional[Path] = None) -> dict[str, Any]:
    """Load products catalogue from JSON file."""
    path = catalogue_path or DEFAULT_CATALOGUE_PATH
    if not path.exists():
        return {"last_updated": "Unknown", "products": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def lookup_product_data(
    product_name: str, catalogue_path: Optional[Path] = None
) -> dict[str, Any]:
    """Look up the latest available stock quantity and price for a product in the catalogue.

    Args:
        product_name: Name of the product to search.
        catalogue_path: Optional path to catalogue.json.
    """
    data = load_catalogue(catalogue_path)
    last_updated = data.get("last_updated", "2026-08-10 09:20")
    products = data.get("products", [])

    query = product_name.strip().lower()
    matched_product = None

    # 1. Exact match (case-insensitive)
    for p in products:
        if p["name"].lower() == query:
            matched_product = p
            break

    # 2. Substring match
    if not matched_product:
        for p in products:
            if query in p["name"].lower() or p["name"].lower() in query:
                matched_product = p
                break

    if not matched_product:
        return {
            "error": f"I'm sorry, I couldn't find '{product_name}' in the latest catalogue.",
            "available": False,
            "last_updated": last_updated,
        }

    return {
        "product": matched_product["name"],
        "price": matched_product["price"],
        "stock": matched_product["stock"],
        "last_updated": last_updated,
    }


def calculate_order_total_data(
    items: Union[list[Any], str], catalogue_path: Optional[Path] = None
) -> dict[str, Any]:
    """Calculate total order value using seller-approved catalogue prices.

    Args:
        items: List of item dicts (e.g. [{"name": "Maggi", "qty": 5}]) or tuples [("Maggi", 5)].
        catalogue_path: Optional path to catalogue.json.
    """
    data = load_catalogue(catalogue_path)
    last_updated = data.get("last_updated", "2026-08-10 09:20")
    products = data.get("products", [])

    parsed_items: list[dict[str, Any]] = []

    if isinstance(items, str):
        try:
            parsed_items = json.loads(items)
        except Exception:
            return {
                "error": "I couldn't parse the order items list.",
                "last_updated": last_updated,
            }
    elif isinstance(items, list):
        for entry in items:
            if isinstance(entry, (list, tuple)) and len(entry) >= 2:
                parsed_items.append({"name": str(entry[0]), "qty": int(entry[1])})
            elif isinstance(entry, dict) and "name" in entry:
                qty = entry.get("qty") or entry.get("quantity") or 1
                parsed_items.append({"name": str(entry["name"]), "qty": int(qty)})

    calculated_items = []
    total = 0
    missing_products = []

    # Map product name -> product dict for fast lookup
    prod_map = {p["name"].lower(): p for p in products}

    for item in parsed_items:
        item_name = item.get("name", "").strip()
        qty = item.get("qty", 1)

        # Match product name
        matched = prod_map.get(item_name.lower())
        if not matched:
            for name_key, p_dict in prod_map.items():
                if item_name.lower() in name_key or name_key in item_name.lower():
                    matched = p_dict
                    break

        if matched:
            subtotal = matched["price"] * qty
            total += subtotal
            calculated_items.append(
                {
                    "name": matched["name"],
                    "qty": qty,
                    "price": matched["price"],
                    "subtotal": subtotal,
                }
            )
        else:
            missing_products.append(item_name)

    if missing_products:
        return {
            "error": f"Could not find pricing for: {', '.join(missing_products)} in catalogue.",
            "last_updated": last_updated,
        }

    return {
        "items": calculated_items,
        "total": total,
        "last_updated": last_updated,
    }
