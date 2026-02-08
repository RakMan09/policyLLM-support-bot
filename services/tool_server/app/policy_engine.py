from datetime import date
from decimal import Decimal

from services.tool_server.app.schemas import (
    CheckEligibilityResponse,
    ComputeRefundResponse,
    GetPolicyResponse,
    MaskedOrder,
)


BASE_POLICY = {
    "return_window_days": 30,
    "refund_shipping": False,
    "requires_evidence_for": ["damaged", "defective", "wrong_item"],
    "non_returnable_categories": ["perishable", "personal_care"],
}


def get_policy(item_category: str, reason: str, order_date: date, delivery_date: date | None) -> GetPolicyResponse:
    policy = dict(BASE_POLICY)

    if item_category == "electronics":
        policy["return_window_days"] = 15

    if reason in {"damaged", "defective", "wrong_item"}:
        policy["refund_shipping"] = True

    if delivery_date is None and reason != "late_delivery":
        policy["return_window_days"] = 0

    return GetPolicyResponse(**policy)


def check_eligibility(order: MaskedOrder, policy: GetPolicyResponse, reason: str) -> CheckEligibilityResponse:
    missing_info: list[str] = []
    required_evidence: list[str] = []

    if order.delivery_date is None and reason != "late_delivery":
        return CheckEligibilityResponse(
            eligible=False,
            missing_info=["delivery_date"],
            required_evidence=[],
            decision_reason="Order not delivered yet",
        )

    if order.item_category in policy.non_returnable_categories:
        return CheckEligibilityResponse(
            eligible=False,
            missing_info=[],
            required_evidence=[],
            decision_reason="Category is non-returnable",
        )

    if order.delivery_date is not None:
        days_since_delivery = (date.today() - order.delivery_date).days
        if days_since_delivery > policy.return_window_days and reason != "damaged":
            return CheckEligibilityResponse(
                eligible=False,
                missing_info=[],
                required_evidence=[],
                decision_reason="Outside return window",
            )

    if reason in policy.requires_evidence_for:
        required_evidence = ["photo_proof"]
        missing_info = ["photo_proof"]

    return CheckEligibilityResponse(
        eligible=True,
        missing_info=missing_info,
        required_evidence=required_evidence,
        decision_reason="Eligible under policy",
    )


def compute_refund(order: MaskedOrder, policy: GetPolicyResponse, reason: str) -> ComputeRefundResponse:
    item_price = Decimal(order.item_price)
    shipping_fee = Decimal(order.shipping_fee)

    if reason == "changed_mind":
        amount = item_price
        breakdown = {"item": item_price, "shipping": Decimal("0.00")}
        refund_type = "partial"
    elif reason in {"damaged", "defective", "wrong_item", "not_as_described"}:
        shipping = shipping_fee if policy.refund_shipping else Decimal("0.00")
        amount = item_price + shipping
        breakdown = {"item": item_price, "shipping": shipping}
        refund_type = "full" if shipping > 0 else "partial"
    else:
        amount = item_price
        breakdown = {"item": item_price, "shipping": Decimal("0.00")}
        refund_type = "partial"

    return ComputeRefundResponse(amount=amount, breakdown=breakdown, refund_type=refund_type)
