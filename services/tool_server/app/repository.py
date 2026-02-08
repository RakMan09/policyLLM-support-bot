from datetime import datetime, timezone
from hashlib import sha256

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from services.tool_server.app.models import (
    Base,
    EscalationRecord,
    LabelRecord,
    Order,
    ReturnRecord,
    ToolCallLog,
)


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Repository:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, future=True)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def create_tables(self) -> None:
        Base.metadata.create_all(self.engine)
        self._seed_orders_if_empty()

    def _seed_orders_if_empty(self) -> None:
        with self.session_factory() as session:
            existing = session.scalar(select(Order.order_id).limit(1))
            if existing:
                return
            session.add_all(
                [
                    Order(
                        order_id="ORD-1001",
                        merchant_id="M-001",
                        customer_email="alice@example.com",
                        customer_phone_last4="1234",
                        item_id="ITEM-1",
                        item_category="electronics",
                        order_date=datetime(2025, 12, 1).date(),
                        delivery_date=datetime(2025, 12, 5).date(),
                        item_price="120.00",
                        shipping_fee="10.00",
                        status="delivered",
                    ),
                    Order(
                        order_id="ORD-1002",
                        merchant_id="M-001",
                        customer_email="bob@example.com",
                        customer_phone_last4="5678",
                        item_id="ITEM-2",
                        item_category="fashion",
                        order_date=datetime(2025, 11, 10).date(),
                        delivery_date=datetime(2025, 11, 14).date(),
                        item_price="55.00",
                        shipping_fee="5.00",
                        status="delivered",
                    ),
                ]
            )
            session.commit()

    def lookup_order(self, *, order_id: str | None, email: str | None, phone_last4: str | None) -> Order | None:
        with self.session_factory() as session:
            query = select(Order)
            if order_id is not None:
                query = query.where(Order.order_id == order_id)
            elif email is not None:
                query = query.where(Order.customer_email == email)
            else:
                query = query.where(Order.customer_phone_last4 == phone_last4)
            return session.scalar(query.limit(1))

    def create_return(self, order_id: str, item_id: str, method: str) -> str:
        key = f"{order_id}:{item_id}:{method}"
        with self.session_factory() as session:
            existing = session.scalar(
                select(ReturnRecord).where(ReturnRecord.idempotency_key == key).limit(1)
            )
            if existing:
                return existing.rma_id

            digest = sha256(key.encode("utf-8")).hexdigest()[:12]
            rma_id = f"RMA-{digest.upper()}"
            record = ReturnRecord(
                rma_id=rma_id,
                idempotency_key=key,
                order_id=order_id,
                item_id=item_id,
                method=method,
                created_at=_utcnow_naive(),
            )
            session.add(record)
            session.commit()
            return rma_id

    def create_label(self, rma_id: str) -> tuple[str, str]:
        with self.session_factory() as session:
            existing = session.scalar(select(LabelRecord).where(LabelRecord.rma_id == rma_id).limit(1))
            if existing:
                return existing.label_id, existing.label_url

            digest = sha256(rma_id.encode("utf-8")).hexdigest()[:12]
            label_id = f"LBL-{digest.upper()}"
            url = f"https://labels.local/{label_id}.pdf"
            record = LabelRecord(
                label_id=label_id,
                rma_id=rma_id,
                label_url=url,
                created_at=_utcnow_naive(),
            )
            session.add(record)
            session.commit()
            return label_id, url

    def create_escalation(self, case_id: str, reason: str, evidence: dict) -> str:
        key = f"{case_id}:{reason}"
        with self.session_factory() as session:
            existing = session.scalar(
                select(EscalationRecord).where(EscalationRecord.idempotency_key == key).limit(1)
            )
            if existing:
                return existing.ticket_id

            digest = sha256(key.encode("utf-8")).hexdigest()[:12]
            ticket_id = f"ESC-{digest.upper()}"
            record = EscalationRecord(
                ticket_id=ticket_id,
                idempotency_key=key,
                case_id=case_id,
                reason=reason,
                evidence=evidence,
                created_at=_utcnow_naive(),
            )
            session.add(record)
            session.commit()
            return ticket_id

    def log_tool_call(
        self,
        *,
        tool_name: str,
        request_payload: dict,
        response_payload: dict | None,
        error_message: str | None,
        latency_ms: int,
    ) -> None:
        with self.session_factory() as session:
            log = ToolCallLog(
                tool_name=tool_name,
                request_payload=request_payload,
                response_payload=response_payload,
                error_message=error_message,
                latency_ms=latency_ms,
                created_at=_utcnow_naive(),
            )
            session.add(log)
            session.commit()


def mask_email(email: str) -> str:
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        local_masked = local[0] + "*"
    else:
        local_masked = local[:2] + "*" * (len(local) - 2)
    return f"{local_masked}@{domain}"
