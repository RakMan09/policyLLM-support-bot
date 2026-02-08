from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import streamlit as st

AGENT_URL = os.getenv("AGENT_SERVER_URL", "http://localhost:8002")
EVAL_REPORT_PATH = Path("eval/results/eval_report.json")
SAFETY_REPORT_PATH = Path("eval/results/safety_report.json")


st.set_page_config(page_title="Refund/Returns Agent UI", layout="wide")

st.title("Refund/Returns Agent")
st.caption("Customer-facing reply + internal summary + tool trace")

with st.sidebar:
    st.header("Config")
    agent_url = st.text_input("Agent URL", AGENT_URL)
    st.markdown("---")
    st.write("Reports")
    eval_path = st.text_input("Eval report path", str(EVAL_REPORT_PATH))
    safety_path = st.text_input("Safety report path", str(SAFETY_REPORT_PATH))


def call_agent(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    with httpx.Client(timeout=20.0) as client:
        response = client.post(f"{url.rstrip('/')}/agent/respond", json=payload)
        response.raise_for_status()
        return response.json()


def read_json(path: str) -> dict[str, Any] | None:
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Submit Case")
    message = st.text_area(
        "Customer message",
        value="My item arrived damaged. I want a refund.",
        height=130,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        order_id = st.text_input("Order ID", value="ORD-1001")
    with c2:
        email = st.text_input("Email (optional)", value="")
    with c3:
        phone_last4 = st.text_input("Phone last 4 (optional)", value="")

    reason = st.selectbox(
        "Reason (optional override)",
        options=["", "damaged", "defective", "wrong_item", "not_as_described", "changed_mind", "late_delivery"],
        index=0,
    )

    st.markdown("Attachments metadata")
    attachment_json = st.text_area(
        "Attachments JSON list",
        value='[{"name":"photo1.jpg","mime_type":"image/jpeg","size_bytes":122233}]',
        height=80,
    )

    if st.button("Run Agent", type="primary"):
        try:
            attachments = json.loads(attachment_json) if attachment_json.strip() else []
            payload = {
                "case_id": f"UI-{uuid.uuid4().hex[:10]}",
                "customer_message": message,
                "order_id": order_id or None,
                "email": email or None,
                "phone_last4": phone_last4 or None,
                "reason": reason or None,
                "attachments": attachments,
            }
            with st.spinner("Calling agent..."):
                response = call_agent(agent_url, payload)
            st.session_state["last_response"] = response
            st.session_state["last_payload"] = payload
            st.success("Agent response received")
        except Exception as exc:
            st.error(f"Failed to run agent: {exc}")

    if "last_response" in st.session_state:
        resp = st.session_state["last_response"]
        st.subheader("Customer Reply")
        st.write(resp.get("customer_reply", ""))

        st.subheader("Internal Case Summary")
        st.code(resp.get("internal_case_summary", ""), language="text")

        st.subheader("Next Action Plan")
        st.write(resp.get("next_action_plan", ""))

        st.metric("Final Action", resp.get("final_action", "unknown"))

        trace = resp.get("tool_trace", [])
        st.subheader("Tool Trace")
        if trace:
            df = pd.DataFrame(
                [
                    {
                        "tool_name": t.get("tool_name"),
                        "status": t.get("status"),
                        "request": json.dumps(t.get("request", {}), ensure_ascii=True),
                        "response": json.dumps(t.get("response", {}), ensure_ascii=True),
                    }
                    for t in trace
                ]
            )
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No tool calls in this response.")

        with st.expander("Raw Response JSON"):
            st.json(resp)

with col_right:
    st.subheader("Offline Reports")

    eval_report = read_json(eval_path)
    if eval_report is None:
        st.warning(f"Eval report not found at: {eval_path}")
    else:
        metrics = eval_report.get("metrics", {})
        st.markdown("**Eval Metrics**")
        st.json(metrics)

    st.markdown("---")

    safety_report = read_json(safety_path)
    if safety_report is None:
        st.warning(f"Safety report not found at: {safety_path}")
    else:
        summary = safety_report.get("summary", {})
        st.markdown("**Safety Summary**")
        st.json(summary)

        results = safety_report.get("results", [])
        if results:
            st.markdown("**Safety Cases**")
            st.dataframe(pd.DataFrame(results), use_container_width=True)
