import pytest
from app.tools.order_sanitizer import OrderSanitizer


def test_order_sanitizer_removes_pii_and_internal_fields():
    raw_order = {
        "order_id": "ORD-1007",
        "customer": {
            "name": "Ava Morgan",
            "email": "ava.morgan@example.test",
            "shipping_address": "220 King Street West, Toronto, ON M5V 3M2"
        },
        "membership_tier": "standard",
        "items": [
            {
                "sku": "PACK-ATLAS-BLK",
                "name": "Atlas Weekender",
                "quantity": 1,
                "final_sale": False
            }
        ],
        "placed_at": "2026-08-11T15:05:00Z",
        "status": "shipped",
        "status_updated_at": "2026-08-14T20:40:00Z",
        "shipped_at": "2026-08-14T20:40:00Z",
        "delivered_at": None,
        "carrier": "UPS",
        "tracking_number": "1ZAR100700000007",
        "estimated_delivery": "2026-08-22",
        "customer_safe_message": "In transit",
        "internal": {
            "risk_score": 82,
            "warehouse_note": "Manual fraud review cleared.",
            "support_tags": ["international", "review-cleared"]
        }
    }

    sanitized = OrderSanitizer.sanitize_order(raw_order)
    dumped = sanitized.model_dump()

    # Verify no PII or internal keys
    assert "customer" not in dumped
    assert "name" not in dumped
    assert "email" not in dumped
    assert "shipping_address" not in dumped
    assert "internal" not in dumped
    assert "risk_score" not in dumped
    assert "warehouse_note" not in dumped

    # Verify customer safe fields
    assert sanitized.order_id == "ORD-1007"
    assert sanitized.carrier == "UPS"
    assert sanitized.tracking_number == "1ZAR100700000007"
    assert sanitized.estimated_delivery == "2026-08-22"


def test_order_sanitizer_suppresses_stale_cancelled_order_eta():
    raw_cancelled = {
        "order_id": "ORD-1004",
        "status": "cancelled",
        "status_updated_at": "2026-08-09T13:48:00Z",
        "carrier": "UPS",
        "tracking_number": "1ZAR100400000004",
        "estimated_delivery": "2026-08-16",
        "customer_safe_message": "The order was cancelled."
    }

    sanitized = OrderSanitizer.sanitize_order(raw_cancelled)
    assert sanitized.status == "cancelled"
    assert sanitized.carrier is None
    assert sanitized.tracking_number is None
    assert sanitized.estimated_delivery is None
