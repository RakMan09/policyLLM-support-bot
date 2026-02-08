from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

REASONS = [
    "damaged",
    "defective",
    "wrong_item",
    "not_as_described",
    "changed_mind",
    "late_delivery",
]

TEMPLATES = {
    "damaged": "Hi, order {order_id} arrived damaged. I need a refund for item {item_id}.",
    "defective": "My item {item_id} from order {order_id} is defective and not working.",
    "wrong_item": "I received the wrong item for order {order_id}. Please help with return.",
    "not_as_described": "Order {order_id} item {item_id} is not as described. Requesting refund.",
    "changed_mind": "I changed my mind about item {item_id} in order {order_id}.",
    "late_delivery": "Order {order_id} was delivered late. I want compensation/refund.",
}


@dataclass
class OlistOrder:
    order_id: str
    customer_id: str
    order_purchase_date: date
    order_delivered_customer_date: date | None
    order_status: str


@dataclass
class OlistCustomer:
    customer_id: str
    customer_unique_id: str


@dataclass
class OlistItem:
    order_id: str
    product_id: str
    seller_id: str
    freight_value: Decimal
    price: Decimal


def local_get_policy(*, item_category: str, reason: str, delivery_date: date | None) -> dict:
    policy = {
        "return_window_days": 30,
        "refund_shipping": False,
        "requires_evidence_for": ["damaged", "defective", "wrong_item"],
        "non_returnable_categories": ["perishable", "personal_care"],
    }
    if item_category == "electronics":
        policy["return_window_days"] = 15
    if reason in {"damaged", "defective", "wrong_item"}:
        policy["refund_shipping"] = True
    if delivery_date is None and reason != "late_delivery":
        policy["return_window_days"] = 0
    return policy


def local_check_eligibility(*, order: dict, policy: dict, reason: str) -> dict:
    delivery_date = order["delivery_date"]
    if delivery_date is None and reason != "late_delivery":
        return {
            "eligible": False,
            "missing_info": ["delivery_date"],
            "required_evidence": [],
            "decision_reason": "Order not delivered yet",
        }
    if order["item_category"] in policy["non_returnable_categories"]:
        return {
            "eligible": False,
            "missing_info": [],
            "required_evidence": [],
            "decision_reason": "Category is non-returnable",
        }
    if delivery_date is not None:
        days_since_delivery = (date.today() - delivery_date).days
        if days_since_delivery > policy["return_window_days"] and reason != "damaged":
            return {
                "eligible": False,
                "missing_info": [],
                "required_evidence": [],
                "decision_reason": "Outside return window",
            }
    missing_info: list[str] = []
    required_evidence: list[str] = []
    if reason in policy["requires_evidence_for"]:
        missing_info = ["photo_proof"]
        required_evidence = ["photo_proof"]
    return {
        "eligible": True,
        "missing_info": missing_info,
        "required_evidence": required_evidence,
        "decision_reason": "Eligible under policy",
    }


def local_compute_refund(*, order: dict, policy: dict, reason: str) -> dict:
    item_price = Decimal(str(order["item_price"]))
    shipping_fee = Decimal(str(order["shipping_fee"]))
    if reason == "changed_mind":
        amount = item_price
        breakdown = {"item": item_price, "shipping": Decimal("0.00")}
        refund_type = "partial"
    elif reason in {"damaged", "defective", "wrong_item", "not_as_described"}:
        shipping = shipping_fee if policy["refund_shipping"] else Decimal("0.00")
        amount = item_price + shipping
        breakdown = {"item": item_price, "shipping": shipping}
        refund_type = "full" if shipping > 0 else "partial"
    else:
        amount = item_price
        breakdown = {"item": item_price, "shipping": Decimal("0.00")}
        refund_type = "partial"
    return {"amount": amount, "breakdown": breakdown, "refund_type": refund_type}


def _parse_date(raw: str) -> date | None:
    if not raw:
        return None
    # Olist has datetime strings like "2018-01-01 00:00:00".
    return datetime.fromisoformat(raw.replace(" ", "T")).date()


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_olist(olist_dir: Path) -> list[tuple[OlistOrder, OlistItem, OlistCustomer]]:
    orders_path = olist_dir / "olist_orders_dataset.csv"
    items_path = olist_dir / "olist_order_items_dataset.csv"
    customers_path = olist_dir / "olist_customers_dataset.csv"
    payments_path = olist_dir / "olist_order_payments_dataset.csv"

    required = [orders_path, items_path, customers_path, payments_path]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing required Olist files: {missing}. "
            "Place Kaggle CSVs under data/raw/olist/."
        )

    order_rows = _read_csv_rows(orders_path)
    item_rows = _read_csv_rows(items_path)
    customer_rows = _read_csv_rows(customers_path)

    orders: dict[str, OlistOrder] = {}
    customers: dict[str, OlistCustomer] = {}
    items_by_order: dict[str, list[OlistItem]] = {}

    for row in order_rows:
        order_id = row["order_id"]
        purchase = _parse_date(row.get("order_purchase_timestamp", "")) or date(2018, 1, 1)
        delivered = _parse_date(row.get("order_delivered_customer_date", ""))
        orders[order_id] = OlistOrder(
            order_id=order_id,
            customer_id=row["customer_id"],
            order_purchase_date=purchase,
            order_delivered_customer_date=delivered,
            order_status=row.get("order_status", "delivered"),
        )

    for row in customer_rows:
        cid = row["customer_id"]
        customers[cid] = OlistCustomer(
            customer_id=cid,
            customer_unique_id=row.get("customer_unique_id", cid),
        )

    for row in item_rows:
        order_id = row["order_id"]
        items_by_order.setdefault(order_id, []).append(
            OlistItem(
                order_id=order_id,
                product_id=row.get("product_id", "unknown-product"),
                seller_id=row.get("seller_id", "unknown-merchant"),
                freight_value=Decimal(row.get("freight_value", "0") or "0"),
                price=Decimal(row.get("price", "0") or "0"),
            )
        )

    joined: list[tuple[OlistOrder, OlistItem, OlistCustomer]] = []
    for order_id, order in orders.items():
        customer = customers.get(order.customer_id)
        if customer is None:
            continue
        for item in items_by_order.get(order_id, []):
            joined.append((order, item, customer))

    return joined


def load_text_pool(processed_dir: Path) -> list[dict[str, str]]:
    path = processed_dir / "twitter_support_texts.jsonl"
    if not path.exists():
        return []
    pool: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("text"):
                pool.append({"text": row["text"], "issue_type_hint": row.get("issue_type_hint", "")})
    return pool


def _reason_from_hint(hint: str, rng: random.Random) -> str:
    if hint in REASONS:
        return hint
    return rng.choice(REASONS)


def build_case(
    *,
    order: OlistOrder,
    item: OlistItem,
    customer: OlistCustomer,
    reason: str,
    customer_message: str,
) -> dict:
    category = "electronics" if "a" <= item.product_id[:1] <= "m" else "fashion"
    policy = local_get_policy(
        item_category=category,
        reason=reason,
        delivery_date=order.order_delivered_customer_date,
    )
    masked = {
        "order_id": order.order_id,
        "merchant_id": item.seller_id,
        "customer_email_masked": f"{customer.customer_unique_id[:2]}***@example.com",
        "customer_phone_last4": "0000",
        "item_id": item.product_id,
        "item_category": category,
        "order_date": order.order_purchase_date,
        "delivery_date": order.order_delivered_customer_date,
        "item_price": item.price,
        "shipping_fee": item.freight_value,
        "status": order.order_status,
    }
    eligibility = local_check_eligibility(order=masked, policy=policy, reason=reason)
    refund = local_compute_refund(order=masked, policy=policy, reason=reason)

    action = "approve_refund" if eligibility["eligible"] and not eligibility["missing_info"] else "request_info"
    if not eligibility["eligible"]:
        action = "deny"
    if reason in {"wrong_item", "defective"} and eligibility["eligible"]:
        action = "approve_return_and_refund"

    return {
        "case_id": f"CASE-{order.order_id}-{item.product_id[:8]}-{reason}",
        "customer_message": customer_message,
        "issue_type": reason,
        "extracted_fields": {
            "order_id": order.order_id,
            "customer_id": customer.customer_unique_id,
            "item_id": item.product_id,
            "merchant_id": item.seller_id,
            "order_date": order.order_purchase_date.isoformat(),
            "delivery_date": (
                order.order_delivered_customer_date.isoformat()
                if order.order_delivered_customer_date
                else None
            ),
            "requested_action": "refund_or_return",
        },
        "tool_targets": {
            "lookup_order": {"order_id": order.order_id},
            "get_policy": {
                "merchant_id": item.seller_id,
                "item_category": category,
                "reason": reason,
                "order_date": order.order_purchase_date.isoformat(),
                "delivery_date": (
                    order.order_delivered_customer_date.isoformat()
                    if order.order_delivered_customer_date
                    else None
                ),
            },
            "check_eligibility": {
                "reason": reason,
            },
            "compute_refund": {
                "reason": reason,
            },
        },
        "policy_decision": {
            "eligible": eligibility["eligible"],
            "missing_info": eligibility["missing_info"],
            "required_evidence": eligibility["required_evidence"],
            "decision_reason": eligibility["decision_reason"],
            "refund_amount": str(refund["amount"]),
            "refund_type": refund["refund_type"],
            "breakdown": {k: str(v) for k, v in refund["breakdown"].items()},
            "next_action": action,
        },
    }


def split_dataset(cases: list[dict], seed: int) -> tuple[list[dict], list[dict], list[dict]]:
    rng = random.Random(seed)
    shuffled = list(cases)
    rng.shuffle(shuffled)
    n = len(shuffled)
    if n == 0:
        return [], [], []
    if n < 10:
        return shuffled, [], []
    n_train = int(n * 0.8)
    n_val = int(n * 0.1)
    train = shuffled[:n_train]
    val = shuffled[n_train : n_train + n_val]
    test = shuffled[n_train + n_val :]
    return train, val, test


def to_dpo_pairs(cases: list[dict]) -> list[dict]:
    pairs: list[dict] = []
    for case in cases:
        decision = case["policy_decision"]
        good = {
            "action": decision["next_action"],
            "refund_amount": decision["refund_amount"],
            "reason": decision["decision_reason"],
        }
        bad = {
            "action": "approve_refund",
            "refund_amount": str(Decimal(decision["refund_amount"]) + Decimal("15.00")),
            "reason": "Ignored policy constraints.",
        }
        if decision["eligible"]:
            bad["action"] = "deny"
            bad["refund_amount"] = "0.00"
            bad["reason"] = "Denied despite eligibility."
        pairs.append(
            {
                "case_id": case["case_id"],
                "prompt": case["customer_message"],
                "chosen": good,
                "rejected": bad,
            }
        )
    return pairs


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=True) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build synthetic refund/return cases with deterministic labels.")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--max-cases", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)

    joined = load_olist(args.raw_dir / "olist")
    text_pool = load_text_pool(args.processed_dir)
    if not text_pool:
        text_pool = [{"text": TEMPLATES[r], "issue_type_hint": r} for r in REASONS]

    cases: list[dict] = []
    idx = 0
    for order, item, customer in joined:
        if len(cases) >= args.max_cases:
            break
        prompt = text_pool[idx % len(text_pool)]
        reason = _reason_from_hint(prompt.get("issue_type_hint", ""), rng)
        default_msg = TEMPLATES[reason].format(order_id=order.order_id, item_id=item.product_id)
        customer_message = prompt.get("text", default_msg)
        if "{order_id}" in customer_message or "{item_id}" in customer_message:
            customer_message = customer_message.format(order_id=order.order_id, item_id=item.product_id)
        case = build_case(
            order=order,
            item=item,
            customer=customer,
            reason=reason,
            customer_message=customer_message,
        )
        cases.append(case)
        idx += 1

    train, val, test = split_dataset(cases, seed=args.seed)
    dpo_pairs = to_dpo_pairs(train)

    write_jsonl(args.processed_dir / "synthetic_cases_train.jsonl", train)
    write_jsonl(args.processed_dir / "synthetic_cases_val.jsonl", val)
    write_jsonl(args.processed_dir / "synthetic_cases_test.jsonl", test)
    write_jsonl(args.processed_dir / "dpo_pairs_train.jsonl", dpo_pairs)

    print(
        json.dumps(
            {
                "cases_total": len(cases),
                "train": len(train),
                "val": len(val),
                "test": len(test),
                "dpo_pairs_train": len(dpo_pairs),
                "outputs": {
                    "train": str(args.processed_dir / "synthetic_cases_train.jsonl"),
                    "val": str(args.processed_dir / "synthetic_cases_val.jsonl"),
                    "test": str(args.processed_dir / "synthetic_cases_test.jsonl"),
                    "dpo_pairs": str(args.processed_dir / "dpo_pairs_train.jsonl"),
                },
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
