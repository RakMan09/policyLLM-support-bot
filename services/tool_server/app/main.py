import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Callable, TypeVar

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from starlette.responses import JSONResponse

from services.tool_server.app.config import settings
from services.tool_server.app.policy_engine import check_eligibility, compute_refund, get_policy
from services.tool_server.app.repository import Repository, mask_email
from services.tool_server.app.schemas import (
    CheckEligibilityRequest,
    CheckEligibilityResponse,
    ComputeRefundRequest,
    ComputeRefundResponse,
    CreateEscalationRequest,
    CreateEscalationResponse,
    CreateLabelRequest,
    CreateLabelResponse,
    CreateReturnRequest,
    CreateReturnResponse,
    GetPolicyRequest,
    GetPolicyResponse,
    LookupOrderRequest,
    LookupOrderResponse,
    MaskedOrder,
)

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("tool_server")

repo = Repository(settings.database_url)


@asynccontextmanager
async def lifespan(_: FastAPI):
    repo.create_tables()
    yield


app = FastAPI(title="refund-returns-tool-server", lifespan=lifespan)

ReqT = TypeVar("ReqT", bound=BaseModel)
ResT = TypeVar("ResT", bound=BaseModel)


def run_with_logging(tool_name: str, request: BaseModel, fn: Callable[[], ResT]) -> ResT:
    start = time.perf_counter()
    request_payload = request.model_dump(mode="json")
    try:
        response = fn()
        latency_ms = int((time.perf_counter() - start) * 1000)
        repo.log_tool_call(
            tool_name=tool_name,
            request_payload=request_payload,
            response_payload=response.model_dump(mode="json"),
            error_message=None,
            latency_ms=latency_ms,
        )
        logger.info(
            "tool_call_success tool=%s latency_ms=%s request=%s",
            tool_name,
            latency_ms,
            request_payload,
        )
        return response
    except Exception as exc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        repo.log_tool_call(
            tool_name=tool_name,
            request_payload=request_payload,
            response_payload=None,
            error_message=str(exc),
            latency_ms=latency_ms,
        )
        logger.exception("tool_call_error tool=%s latency_ms=%s", tool_name, latency_ms)
        raise


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/tools/lookup_order", response_model=LookupOrderResponse)
def lookup_order(request: LookupOrderRequest) -> LookupOrderResponse:
    def _run() -> LookupOrderResponse:
        row = repo.lookup_order(
            order_id=request.order_id,
            email=request.email,
            phone_last4=request.phone_last4,
        )
        if row is None:
            return LookupOrderResponse(order=None, found=False)

        masked_order = MaskedOrder(
            order_id=row.order_id,
            merchant_id=row.merchant_id,
            customer_email_masked=mask_email(row.customer_email),
            customer_phone_last4=row.customer_phone_last4,
            item_id=row.item_id,
            item_category=row.item_category,
            order_date=row.order_date,
            delivery_date=row.delivery_date,
            item_price=row.item_price,
            shipping_fee=row.shipping_fee,
            status=row.status,
        )
        return LookupOrderResponse(order=masked_order, found=True)

    return run_with_logging("lookup_order", request, _run)


@app.post("/tools/get_policy", response_model=GetPolicyResponse)
def get_policy_endpoint(request: GetPolicyRequest) -> GetPolicyResponse:
    return run_with_logging(
        "get_policy",
        request,
        lambda: get_policy(
            item_category=request.item_category,
            reason=request.reason,
            order_date=request.order_date,
            delivery_date=request.delivery_date,
        ),
    )


@app.post("/tools/check_eligibility", response_model=CheckEligibilityResponse)
def check_eligibility_endpoint(request: CheckEligibilityRequest) -> CheckEligibilityResponse:
    return run_with_logging(
        "check_eligibility",
        request,
        lambda: check_eligibility(order=request.order, policy=request.policy, reason=request.reason),
    )


@app.post("/tools/compute_refund", response_model=ComputeRefundResponse)
def compute_refund_endpoint(request: ComputeRefundRequest) -> ComputeRefundResponse:
    return run_with_logging(
        "compute_refund",
        request,
        lambda: compute_refund(order=request.order, policy=request.policy, reason=request.reason),
    )


@app.post("/tools/create_return", response_model=CreateReturnResponse)
def create_return_endpoint(request: CreateReturnRequest) -> CreateReturnResponse:
    def _run() -> CreateReturnResponse:
        rma_id = repo.create_return(
            order_id=request.order_id,
            item_id=request.item_id,
            method=request.method,
        )
        return CreateReturnResponse(rma_id=rma_id)

    return run_with_logging("create_return", request, _run)


@app.post("/tools/create_label", response_model=CreateLabelResponse)
def create_label_endpoint(request: CreateLabelRequest) -> CreateLabelResponse:
    def _run() -> CreateLabelResponse:
        label_id, url = repo.create_label(rma_id=request.rma_id)
        return CreateLabelResponse(label_id=label_id, url=url)

    return run_with_logging("create_label", request, _run)


@app.post("/tools/create_escalation", response_model=CreateEscalationResponse)
def create_escalation_endpoint(request: CreateEscalationRequest) -> CreateEscalationResponse:
    def _run() -> CreateEscalationResponse:
        ticket_id = repo.create_escalation(
            case_id=request.case_id,
            reason=request.reason,
            evidence=request.evidence,
        )
        return CreateEscalationResponse(ticket_id=ticket_id)

    return run_with_logging("create_escalation", request, _run)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_, exc: Exception) -> Any:
    if isinstance(exc, HTTPException):
        raise exc
    return JSONResponse(status_code=500, content={"detail": "internal_error"})
