import json
from pathlib import Path

from pipelines.build_dataset import load_olist, split_dataset
from pipelines.preprocess_text import clean_text, infer_issue_type


def _write_csv(path: Path, header: str, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


def test_clean_text_and_issue_detection():
    text = "@brand my order is damaged!! see https://x.com/abc"
    cleaned = clean_text(text)
    assert "http" not in cleaned
    assert infer_issue_type(cleaned) == "damaged"


def test_load_olist_join(tmp_path: Path):
    olist = tmp_path / "olist"
    _write_csv(
        olist / "olist_orders_dataset.csv",
        "order_id,customer_id,order_purchase_timestamp,order_delivered_customer_date,order_status",
        ["o1,c1,2018-01-01 10:00:00,2018-01-05 12:00:00,delivered"],
    )
    _write_csv(
        olist / "olist_order_items_dataset.csv",
        "order_id,order_item_id,product_id,seller_id,shipping_limit_date,price,freight_value",
        ["o1,1,p1,s1,2018-01-03 00:00:00,99.90,10.10"],
    )
    _write_csv(
        olist / "olist_customers_dataset.csv",
        "customer_id,customer_unique_id,customer_zip_code_prefix,customer_city,customer_state",
        ["c1,u1,12345,city,SP"],
    )
    _write_csv(
        olist / "olist_order_payments_dataset.csv",
        "order_id,payment_sequential,payment_type,payment_installments,payment_value",
        ["o1,1,credit_card,1,110.0"],
    )

    joined = load_olist(olist)
    assert len(joined) == 1
    order, item, customer = joined[0]
    assert order.order_id == "o1"
    assert item.product_id == "p1"
    assert customer.customer_unique_id == "u1"


def test_split_dataset_small_sample_goes_to_train():
    cases = [{"case_id": "a"}, {"case_id": "b"}]
    train, val, test = split_dataset(cases, seed=42)
    assert len(train) == 2
    assert len(val) == 0
    assert len(test) == 0
