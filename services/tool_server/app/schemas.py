from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator


class LookupOrderRequest(BaseModel):
    order_id: str | None = None
    email: EmailStr | None = None
    phone_last4: str | None = Field(default=None, min_length=4, max_length=4)

    @model_validator(mode="after")
    def validate_identifier_present(self) -> "LookupOrderRequest":
        provided = [self.order_id, self.email, self.phone_last4]
        if sum(v is not None for v in provided) != 1:
            raise ValueError("Provide exactly one identifier: order_id OR email OR phone_last4")
        return self


class MaskedOrder(BaseModel):
    order_id: str
    merchant_id: str
    customer_email_masked: str
    customer_phone_last4: str
    item_id: str
    item_category: str
    order_date: date
    delivery_date: date | None
    item_price: Decimal
    shipping_fee: Decimal
    status: str


class LookupOrderResponse(BaseModel):
    order: MaskedOrder | None
    found: bool


class GetPolicyRequest(BaseModel):
    merchant_id: str
    item_category: str
    reason: Literal[
        "damaged",
        "defective",
        "wrong_item",
        "not_as_described",
        "changed_mind",
        "late_delivery",
    ]
    order_date: date
    delivery_date: date | None


class GetPolicyResponse(BaseModel):
    return_window_days: int
    refund_shipping: bool
    requires_evidence_for: list[str]
    non_returnable_categories: list[str]


class CheckEligibilityRequest(BaseModel):
    order: MaskedOrder
    policy: GetPolicyResponse
    reason: str


class CheckEligibilityResponse(BaseModel):
    eligible: bool
    missing_info: list[str]
    required_evidence: list[str]
    decision_reason: str


class ComputeRefundRequest(BaseModel):
    order: MaskedOrder
    policy: GetPolicyResponse
    reason: str


class ComputeRefundResponse(BaseModel):
    amount: Decimal
    breakdown: dict[str, Decimal]
    refund_type: Literal["full", "partial", "none"]


class CreateReturnRequest(BaseModel):
    order_id: str
    item_id: str
    method: Literal["dropoff", "pickup"]


class CreateReturnResponse(BaseModel):
    rma_id: str


class CreateLabelRequest(BaseModel):
    rma_id: str


class CreateLabelResponse(BaseModel):
    label_id: str
    url: str


class CreateEscalationRequest(BaseModel):
    case_id: str
    reason: str
    evidence: dict


class CreateEscalationResponse(BaseModel):
    ticket_id: str
