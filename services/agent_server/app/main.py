from __future__ import annotations

import logging

from fastapi import FastAPI

from services.agent_server.app.config import settings
from services.agent_server.app.orchestrator import AgentOrchestrator
from services.agent_server.app.schemas import AgentRequest, AgentResponse
from services.agent_server.app.tool_client import ToolClient

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("agent_server")

app = FastAPI(title="refund-returns-agent-server")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/agent/respond", response_model=AgentResponse)
def respond(request: AgentRequest) -> AgentResponse:
    tools = ToolClient(settings.tool_server_url)
    orchestrator = AgentOrchestrator(tools)
    response = orchestrator.run(request)
    logger.info("agent_decision case_id=%s action=%s", request.case_id, response.final_action)
    return response
