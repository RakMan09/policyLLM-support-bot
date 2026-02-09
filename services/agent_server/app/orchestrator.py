from __future__ import annotations

import logging
from typing import Any

from services.agent_server.app.guardrails import looks_like_fraud_or_exfil, looks_like_injection, mask_text
from services.agent_server.app.llm_agent import LLMAdvisor
from services.agent_server.app.schemas import AgentRequest, AgentResponse, ToolTrace
from services.agent_server.app.tool_client import ToolClient

logger = logging.getLogger("agent_server")


def _infer_reason(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["damaged", "broken", "cracked"]):
        return "damaged"
    if any(k in t for k in ["defective", "not working", "won't turn on"]):
        return "defective"
    if "wrong item" in t:
        return "wrong_item"
    if "not as described" in t:
        return "not_as_described"
    if any(k in t for k in ["late", "delayed", "where is my order"]):
        return "late_delivery"
    return "changed_mind"


def _identifier_payload(req: AgentRequest) -> dict[str, Any] | None:
    if req.order_id:
        return {"order_id": req.order_id}
    if req.email:
        return {"email": req.email}
    if req.phone_last4:
        return {"phone_last4": req.phone_last4}
    return None


class AgentOrchestrator:
    def __init__(self, tools: ToolClient, llm: LLMAdvisor | None = None):
        self.tools = tools
        self.llm = llm or LLMAdvisor()

    def run(self, req: AgentRequest) -> AgentResponse:
        trace: list[ToolTrace] = []
        message = req.customer_message
        masked_msg = mask_text(message)

        if looks_like_fraud_or_exfil(message):
            return AgentResponse(
                customer_reply=(
                    "I can't help with requests that bypass policy, expose sensitive data, "
                    "or involve fraud. I can assist with a legitimate refund/return request."
                ),
                internal_case_summary=f"Fraud/exfiltration pattern detected. message={masked_msg}",
                next_action_plan="Refuse request and keep case for manual review if repeated.",
                final_action="refuse",
                tool_trace=trace,
            )

        if looks_like_injection(message):
            # Restrict tool use to none for safety and request clear, policy-relevant details.
            return AgentResponse(
                customer_reply=(
                    "I can help with your refund/return, but I need a normal request format. "
                    "Please share your order ID (or account email) and the issue with the item."
                ),
                internal_case_summary=f"Prompt-injection pattern detected. message={masked_msg}",
                next_action_plan="Restrict to read-only path on next turn; request clean details.",
                final_action="request_info",
                tool_trace=trace,
            )

        identifier = _identifier_payload(req)
        if identifier is None:
            return AgentResponse(
                customer_reply=(
                    "Please share your order ID, account email, or phone last 4 digits so I can "
                    "check eligibility."
                ),
                internal_case_summary="Missing order identifier; cannot proceed with tool lookup.",
                next_action_plan="Ask customer for one valid identifier.",
                final_action="request_info",
                tool_trace=trace,
            )

        reason = req.reason
        if reason is None:
            reason = self.llm.extract_reason(
                message,
                [
                    "damaged",
                    "defective",
                    "wrong_item",
                    "not_as_described",
                    "changed_mind",
                    "late_delivery",
                ],
            )
        reason = reason or _infer_reason(message)

        lookup = self.tools.lookup_order(identifier)
        trace.append(ToolTrace(tool_name="lookup_order", request=identifier, response=lookup, status="ok"))
        if not lookup.get("found") or not lookup.get("order"):
            return AgentResponse(
                customer_reply="I couldn't find the order with those details. Please confirm the identifier.",
                internal_case_summary="Order lookup returned not found.",
                next_action_plan="Request corrected order identifier.",
                final_action="request_info",
                tool_trace=trace,
            )

        order = lookup["order"]
        policy_req = {
            "merchant_id": order["merchant_id"],
            "item_category": order["item_category"],
            "reason": reason,
            "order_date": order["order_date"],
            "delivery_date": order.get("delivery_date"),
        }
        policy = self.tools.get_policy(policy_req)
        trace.append(ToolTrace(tool_name="get_policy", request=policy_req, response=policy, status="ok"))

        eligibility_req = {
            "order": order,
            "policy": policy,
            "reason": reason,
        }
        eligibility = self.tools.check_eligibility(eligibility_req)
        trace.append(
            ToolTrace(
                tool_name="check_eligibility",
                request={"reason": reason},
                response=eligibility,
                status="ok",
            )
        )

        refund_req = {
            "order": order,
            "policy": policy,
            "reason": reason,
        }
        refund = self.tools.compute_refund(refund_req)
        trace.append(ToolTrace(tool_name="compute_refund", request={"reason": reason}, response=refund, status="ok"))

        if not eligibility.get("eligible", False):
            customer_reply = (
                "Thanks for your request. Based on policy, this case is not eligible for refund/return: "
                f"{eligibility.get('decision_reason', 'Not eligible')}."
            )
            drafted = self.llm.draft_reply(
                "deny_refund",
                {
                    "reason": reason,
                    "decision_reason": eligibility.get("decision_reason", "Not eligible"),
                },
            )
            if drafted:
                customer_reply = drafted
            return AgentResponse(
                customer_reply=customer_reply,
                internal_case_summary=(
                    "Policy-authoritative deny. "
                    f"order_id={order['order_id']} reason={reason} decision={eligibility.get('decision_reason')}"
                ),
                next_action_plan="Deny automatically; offer escalation if customer disputes.",
                final_action="deny",
                tool_trace=trace,
            )

        missing = eligibility.get("missing_info", [])
        if missing:
            customer_reply = (
                    "I can continue, but I still need the following information/evidence: "
                    + ", ".join(missing)
                    + "."
                )
            drafted = self.llm.draft_reply(
                "request_missing_info",
                {"reason": reason, "missing_info": missing},
            )
            if drafted:
                customer_reply = drafted
            return AgentResponse(
                customer_reply=customer_reply,
                internal_case_summary=(
                    f"Eligible conditionally; waiting for required evidence. missing={missing} order={order['order_id']}"
                ),
                next_action_plan="Collect missing evidence before any write tools.",
                final_action="request_info",
                tool_trace=trace,
            )

        # Policy-eligible path: create return + label (if return needed), then final approval.
        create_return_req = {
            "order_id": order["order_id"],
            "item_id": order["item_id"],
            "method": "dropoff",
        }
        ret = self.tools.create_return(create_return_req)
        trace.append(
            ToolTrace(tool_name="create_return", request=create_return_req, response=ret, status="ok")
        )

        label_req = {"rma_id": ret["rma_id"]}
        label = self.tools.create_label(label_req)
        trace.append(ToolTrace(tool_name="create_label", request=label_req, response=label, status="ok"))

        customer_reply = (
            "Your return/refund is approved under policy. "
            f"Refund amount: {refund['amount']}. "
            f"RMA: {ret['rma_id']}. Label: {label['url']}"
        )
        drafted = self.llm.draft_reply(
            "approve_return_and_refund",
            {
                "reason": reason,
                "refund_amount": refund["amount"],
                "rma_id": ret["rma_id"],
                "label_url": label["url"],
            },
        )
        if drafted:
            customer_reply = drafted
        return AgentResponse(
            customer_reply=customer_reply,
            internal_case_summary=(
                "Approved with tool-grounded workflow. "
                f"order_id={order['order_id']} reason={reason} refund={refund['amount']} rma={ret['rma_id']}"
            ),
            next_action_plan="Return created, label issued, refund to be processed.",
            final_action="approve_return_and_refund",
            tool_trace=trace,
        )
