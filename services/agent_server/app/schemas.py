from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AttachmentMeta(BaseModel):
    name: str
    mime_type: str | None = None
    size_bytes: int | None = None


class ConversationTurn(BaseModel):
    role: Literal["customer", "agent"]
    text: str
    timestamp: datetime | None = None


class AgentRequest(BaseModel):
    case_id: str
    customer_message: str
    conversation: list[ConversationTurn] = Field(default_factory=list)
    attachments: list[AttachmentMeta] = Field(default_factory=list)
    order_id: str | None = None
    email: str | None = None
    phone_last4: str | None = Field(default=None, min_length=4, max_length=4)
    reason: Literal[
        "damaged",
        "defective",
        "wrong_item",
        "not_as_described",
        "changed_mind",
        "late_delivery",
    ] | None = None


class ToolTrace(BaseModel):
    tool_name: str
    request: dict
    response: dict | None = None
    status: Literal["ok", "error", "skipped"]
    note: str | None = None


class AgentResponse(BaseModel):
    customer_reply: str
    internal_case_summary: str
    next_action_plan: str
    final_action: Literal[
        "approve_return_and_refund",
        "approve_refund",
        "request_info",
        "deny",
        "escalate",
        "refuse",
    ]
    tool_trace: list[ToolTrace]
