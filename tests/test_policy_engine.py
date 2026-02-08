from datetime import date, timedelta
from decimal import Decimal

from services.tool_server.app.policy_engine import check_eligibility, compute_refund, get_policy
from services.tool_server.app.schemas import MaskedOrder


def _order(delivery_delta_days: int = 2, category: str = "fashion") -> MaskedOrder:
    delivery = date.today() - timedelta(days=delivery_delta_days)
    return MaskedOrder(
        order_id="ORD-T",
        merchant_id="M-1",
        customer_email_masked="al***@example.com",
        customer_phone_last4="1234",
        item_id="ITEM-1",
        item_category=category,
        order_date=date.today() - timedelta(days=10),
        delivery_date=delivery,
        item_price=Decimal("100.00"),
        shipping_fee=Decimal("10.00"),
        status="delivered",
    )


def test_get_policy_damaged_refunds_shipping():
    pol = get_policy("fashion", "damaged", date.today(), date.today())
    assert pol.refund_shipping is True


def test_eligibility_non_returnable_category():
    pol = get_policy("personal_care", "changed_mind", date.today(), date.today())
    order = _order(category="personal_care")
    res = check_eligibility(order, pol, "changed_mind")
    assert res.eligible is False


def test_compute_refund_full_for_damaged():
    pol = get_policy("fashion", "damaged", date.today(), date.today())
    order = _order()
    res = compute_refund(order, pol, "damaged")
    assert res.amount == Decimal("110.00")
    assert res.refund_type == "full"
