from typing import Dict, Any, Optional, List
from app.models.schemas import CustomerOrder, CustomerOrderItem, OrderLookupResult


class OrderSanitizer:
    """
    Handles privacy allowlisting, removal of sensitive/internal fields,
    and suppression of stale operational data (e.g. for cancelled/returned orders).
    """

    @staticmethod
    def sanitize_order(raw_order: Dict[str, Any]) -> CustomerOrder:
        """
        Extracts only customer-safe fields, completely omitting sensitive customer
        PII (email, address, name) and internal operational fields (risk score, warehouse notes, tags).
        Applies status precedence to suppress stale delivery fields.
        """
        status = str(raw_order.get("status", "")).lower()

        # Sanitize item list
        items: List[CustomerOrderItem] = []
        for item in raw_order.get("items", []):
            items.append(
                CustomerOrderItem(
                    name=item.get("name", ""),
                    quantity=int(item.get("quantity", 1)),
                    final_sale=bool(item.get("final_sale", False))
                )
            )

        # Stale operational data suppression:
        # If status is cancelled or returned, operational carrier/ETA fields are stale and must be suppressed
        carrier = raw_order.get("carrier")
        tracking_number = raw_order.get("tracking_number")
        estimated_delivery = raw_order.get("estimated_delivery")

        if status in ("cancelled", "returned"):
            carrier = None
            tracking_number = None
            estimated_delivery = None

        return CustomerOrder(
            order_id=raw_order.get("order_id", ""),
            membership_tier=raw_order.get("membership_tier", "standard"),
            items=items,
            placed_at=raw_order.get("placed_at", ""),
            status=status,
            status_updated_at=raw_order.get("status_updated_at", ""),
            shipped_at=raw_order.get("shipped_at"),
            delivered_at=raw_order.get("delivered_at"),
            carrier=carrier,
            tracking_number=tracking_number,
            estimated_delivery=estimated_delivery,
            customer_safe_message=raw_order.get("customer_safe_message")
        )

    @classmethod
    def build_safe_lookup_result(
        cls,
        normalized_id: Optional[str],
        raw_order: Optional[Dict[str, Any]]
    ) -> OrderLookupResult:
        """
        Builds a safe OrderLookupResult for consumption by the agent and response generator.
        """
        if not normalized_id:
            return OrderLookupResult(
                found=False,
                order_id=None,
                message="Please provide an order ID (for example, ORD-1007) to look up your order status.",
                requires_human_review=False
            )

        if raw_order is None:
            return OrderLookupResult(
                found=False,
                order_id=normalized_id,
                message=f"Order {normalized_id} was not found. Please double-check your order ID or contact customer support for assistance.",
                requires_human_review=True
            )

        sanitized_order = cls.sanitize_order(raw_order)
        status = sanitized_order.status
        is_stale_suppressed = status in ("cancelled", "returned")
        requires_human_review = (status == "exception")

        # Generate standard operational summary message for tool metadata
        if status == "cancelled":
            msg = f"Order {normalized_id} was cancelled on {sanitized_order.status_updated_at} and will not be shipped."
        elif status == "returned":
            msg = f"Order {normalized_id} was returned and processed. {sanitized_order.customer_safe_message or ''}".strip()
        elif status == "exception":
            msg = f"Order {normalized_id} encountered an exception requiring support review. {sanitized_order.customer_safe_message or ''}".strip()
        elif status == "delivered":
            msg = f"Order {normalized_id} was delivered on {sanitized_order.delivered_at} via {sanitized_order.carrier} (Tracking: {sanitized_order.tracking_number})."
        elif status == "shipped":
            if sanitized_order.estimated_delivery:
                msg = f"Order {normalized_id} has shipped via {sanitized_order.carrier} (Tracking: {sanitized_order.tracking_number}) and is estimated to arrive on {sanitized_order.estimated_delivery}."
            else:
                msg = f"Order {normalized_id} has shipped via {sanitized_order.carrier} (Tracking: {sanitized_order.tracking_number}). A delivery estimate is not currently available."
        elif status in ("pending", "processing"):
            if sanitized_order.estimated_delivery:
                msg = f"Order {normalized_id} is currently {status}. Estimated delivery date is {sanitized_order.estimated_delivery}."
            else:
                msg = f"Order {normalized_id} is currently {status}. A delivery estimate is not yet available."
        else:
            msg = f"Order {normalized_id} status is {status}. {sanitized_order.customer_safe_message or ''}".strip()

        return OrderLookupResult(
            found=True,
            order_id=normalized_id,
            order=sanitized_order,
            message=msg,
            requires_human_review=requires_human_review,
            is_stale_delivery_suppressed=is_stale_suppressed
        )
