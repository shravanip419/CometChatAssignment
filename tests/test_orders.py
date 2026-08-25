import pytest
from app.tools.order_lookup import OrderLookupTool


@pytest.fixture
def order_tool():
    return OrderLookupTool()


def test_order_lookup_valid(order_tool):
    result = order_tool.lookup("ORD-1007")
    assert result.found is True
    assert result.order is not None
    assert result.order.order_id == "ORD-1007"
    assert result.order.status == "shipped"
    assert result.order.carrier == "UPS"
    assert result.order.estimated_delivery == "2026-08-22"
    assert result.requires_human_review is False


def test_order_lookup_normalization(order_tool):
    # Test lowercase, whitespace, and punctuation variations
    for query in ["ord-1007", "  ORD-1007  ", "ord1007", "ORD_1007"]:
        result = order_tool.lookup(query)
        assert result.found is True
        assert result.order.order_id == "ORD-1007"


def test_order_lookup_missing_id(order_tool):
    result = order_tool.lookup("")
    assert result.found is False
    assert "provide an order ID" in result.message
    assert result.requires_human_review is False


def test_order_lookup_unknown_id(order_tool):
    result = order_tool.lookup("ORD-9999")
    assert result.found is False
    assert "was not found" in result.message
    assert result.requires_human_review is True  # Unknown order triggers handoff


def test_cancelled_order_stale_eta_suppression(order_tool):
    result = order_tool.lookup("ORD-1004")
    assert result.found is True
    assert result.order.status == "cancelled"
    # Stale fields must be suppressed
    assert result.order.estimated_delivery is None
    assert result.order.carrier is None
    assert result.order.tracking_number is None
    assert result.is_stale_delivery_suppressed is True
    assert "cancelled" in result.message.lower()
    assert "2026-08-16" not in result.message


def test_returned_order_stale_eta_suppression(order_tool):
    result = order_tool.lookup("ORD-1008")
    assert result.found is True
    assert result.order.status == "returned"
    assert result.order.estimated_delivery is None
    assert result.order.carrier is None
    assert result.order.tracking_number is None
    assert result.is_stale_delivery_suppressed is True


def test_shipped_order_without_eta(order_tool):
    result = order_tool.lookup("ORD-1011")
    assert result.found is True
    assert result.order.status == "shipped"
    assert result.order.carrier == "Canada Post"
    assert result.order.estimated_delivery is None
    assert "not currently available" in result.message.lower()


def test_exception_order_requires_human_review(order_tool):
    result = order_tool.lookup("ORD-1010")
    assert result.found is True
    assert result.order.status == "exception"
    assert result.requires_human_review is True
