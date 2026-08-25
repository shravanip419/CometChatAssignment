import json
import re
from pathlib import Path
from typing import Optional, Dict, Any
from app.models.schemas import OrderLookupResult, CustomerOrder
from app.tools.order_sanitizer import OrderSanitizer
from app.config import ORDERS_FILE


class OrderLookupTool:
    """
    Dedicated tool for loading, indexing, normalizing, and retrieving order records.
    Delegates privacy sanitization and stale operational data suppression to OrderSanitizer.
    """
    def __init__(self, orders_file: Optional[Path] = None, sanitizer: Optional[OrderSanitizer] = None):
        self.orders_file = orders_file or ORDERS_FILE
        self.sanitizer = sanitizer or OrderSanitizer()
        self.orders_data: Dict[str, Any] = {}
        self.snapshot_at: str = "2026-08-15T12:00:00Z"
        self._load_orders()

    def _load_orders(self):
        """Loads and indexes orders from orders.json by uppercase order_id."""
        if not self.orders_file.exists():
            self.orders_data = {}
            return
            
        with open(self.orders_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            
        self.snapshot_at = raw_data.get("snapshot_at", "2026-08-15T12:00:00Z")
        orders_list = raw_data.get("orders", [])
        self.orders_data = {order["order_id"].upper(): order for order in orders_list}

    @staticmethod
    def normalize_order_id(raw_id: Optional[str]) -> Optional[str]:
        """
        Normalizes order ID by stripping whitespace, standardizing separators, and uppercasing.
        Converts 'ord-1007', 'ord 1007', 'ORD_1007', 'ord1007' -> 'ORD-1007'.
        """
        if not raw_id:
            return None
        cleaned = raw_id.strip().upper()
        match = re.search(r"ORD\D*(\d+)", cleaned)
        if match:
            digits = match.group(1)
            return f"ORD-{digits}"
        return cleaned if cleaned else None

    def find_raw_order(self, normalized_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Searches internal order storage for the given normalized order ID.
        Returns the raw order dictionary or None.
        """
        if not normalized_id:
            return None
        return self.orders_data.get(normalized_id)

    def lookup(self, order_id_input: Optional[str]) -> OrderLookupResult:
        """
        Normalizes order ID input, finds the raw order, and returns a sanitized,
        customer-safe OrderLookupResult.
        """
        normalized_id = self.normalize_order_id(order_id_input)
        raw_order = self.find_raw_order(normalized_id)
        return self.sanitizer.build_safe_lookup_result(normalized_id, raw_order)
