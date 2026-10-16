"""Demo checkout: validation, atomic stock reservation, idempotency, price snapshots, privacy."""
import logging
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from backend.models import Order, OrderItem, Product, ProductSize
from .conftest import VALID_ORDER, csrf_headers, product_id


def add(client, hdr, pid, size="8", quantity=1):
    r = client.post("/api/cart/items", json={"product_id": pid, "size": size, "quantity": quantity}, headers=hdr)
    assert r.status_code == 201, r.text


def order(client, hdr, **override):
    return client.post("/api/orders", json={**VALID_ORDER, **override}, headers=hdr)


def stock(db, slug, size):
    db.expire_all()
    pid = product_id(db, slug)
    return db.get(ProductSize, (pid, size)).stock


def test_order_success_totals_stock_and_snapshots(client, hdr, db):
    add(client, hdr, product_id(db, "alpha-low"), "8", 2)
    add(client, hdr, product_id(db, "beta-high"), "9", 1)
    r = order(client, hdr)
    assert r.status_code == 201
    body = r.json()
    assert body["demo"] is True and body["status"] == "demo_pending" and body["total"] == "450.50"

    saved = db.query(Order).one()
    assert saved.subtotal == Decimal("450.50") and saved.total == Decimal("450.50")
    lines = {(i.product_name, i.size): (i.quantity, i.unit_price, i.line_total) for i in saved.items}
    assert lines[("ALPHA LOW", "8")] == (2, Decimal("100.00"), Decimal("200.00"))
    assert stock(db, "alpha-low", "8") == 0 and stock(db, "beta-high", "9") == 2
    assert client.get("/api/cart").json()["count"] == 0       # cart cleared after success


def test_price_snapshot_survives_later_price_change(client, hdr, db):
    add(client, hdr, product_id(db, "alpha-low"), "8", 1)
    order(client, hdr)
    db.query(Product).filter_by(slug="alpha-low").update({"price": Decimal("999.00"), "name": "RENAMED"})
    db.commit()
    db.expire_all()
    item = db.query(OrderItem).one()
    assert item.unit_price == Decimal("100.00") and item.product_name == "ALPHA LOW"
    assert db.query(Order).one().total == Decimal("100.00")


def test_confirmation_page_only_visible_to_the_ordering_session(app, client, hdr, db):
    add(client, hdr, product_id(db, "alpha-low"))
    ref = order(client, hdr).json()["order_ref"]
    page = client.get(f"/orders/{ref}")
    assert page.status_code == 200 and "Demo order recorded" in page.text and "No payment was processed" in page.text
    assert TestClient(app).get(f"/orders/{ref}").status_code == 404
    assert client.get("/orders/not-a-real-ref").status_code == 404


def test_replayed_request_is_idempotent(client, hdr, db):
    add(client, hdr, product_id(db, "alpha-low"), "8", 1)
    first = order(client, hdr)
    second = order(client, hdr)                       # e.g. double click or retry
    assert first.status_code == 201 and second.status_code == 200
    assert first.json()["order_ref"] == second.json()["order_ref"]
    assert db.query(Order).count() == 1
    assert stock(db, "alpha-low", "8") == 1           # decremented once, not twice


def test_empty_cart_cannot_check_out(client, hdr, db):
    r = order(client, hdr)
    assert r.status_code == 409 and r.json()["error"]["code"] == "empty_cart"
    assert db.query(Order).count() == 0


@pytest.mark.parametrize("override", [
    {"customer_email": "not-an-email"},
    {"customer_name": ""},
    {"customer_name": "A"},
    {"shipping_line1": ""},
    {"shipping_city": ""},
    {"shipping_postal_code": "!!"},
    {"shipping_country": ""},
    {"idempotency_key": "short"},
    {"idempotency_key": "has spaces and symbols!!!!!!!"},
    {"customer_name": "x" * 500},
])
def test_invalid_checkout_fields_are_rejected_and_nothing_is_stored(client, hdr, db, override):
    add(client, hdr, product_id(db, "alpha-low"))
    r = order(client, hdr, **override)
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    assert r.json()["error"]["details"]
    assert db.query(Order).count() == 0 and stock(db, "alpha-low", "8") == 2


def test_missing_and_extra_fields_rejected(client, hdr, db):
    add(client, hdr, product_id(db, "alpha-low"))
    body = dict(VALID_ORDER); del body["customer_email"]
    assert client.post("/api/orders", json=body, headers=hdr).status_code == 422
    assert order(client, hdr, total="0.01", unit_price="0.01").status_code == 422   # browser cannot set prices


def test_card_data_is_never_accepted(client, hdr, db):
    add(client, hdr, product_id(db, "alpha-low"))
    assert order(client, hdr, card_number="4242424242424242").status_code == 422


def test_validation_errors_do_not_echo_submitted_values(client, hdr, db):
    add(client, hdr, product_id(db, "alpha-low"))
    r = order(client, hdr, customer_email="secret-value-not-an-email")
    assert "secret-value-not-an-email" not in r.text


def test_checkout_requires_csrf(client, db):
    assert client.post("/api/orders", json=VALID_ORDER).status_code == 403


def test_stock_sold_elsewhere_between_cart_and_order_blocks_checkout(client, hdr, db):
    pid = product_id(db, "alpha-low")
    add(client, hdr, pid, "8", 2)
    db.query(ProductSize).filter_by(product_id=pid, size="8").update({"stock": 1})  # someone else bought one
    db.commit()
    r = order(client, hdr)
    assert r.status_code == 409
    assert db.query(Order).count() == 0 and stock(db, "alpha-low", "8") == 1


def test_race_on_stock_rolls_back_every_line(client, hdr, db, monkeypatch):
    """Cart passed validation, then stock for the *second* line vanishes before the UPDATE."""
    from backend.services import orders as svc
    a, b = product_id(db, "alpha-low"), product_id(db, "beta-high")
    add(client, hdr, a, "8", 1)
    add(client, hdr, b, "9", 1)
    real_execute = db.__class__.execute
    state = {"n": 0}

    def drain_second(self, stmt, *args, **kwargs):
        if getattr(stmt, "is_update", False):
            state["n"] += 1
        if state["n"] == 2 and getattr(stmt, "is_update", False):  # just before the 2nd reservation, another buyer takes the last pairs
            state["n"] += 1
            real_execute(self, ProductSize.__table__.update().where(ProductSize.product_id == b).values(stock=0))
        return real_execute(self, stmt, *args, **kwargs)

    monkeypatch.setattr(db.__class__, "execute", drain_second)
    r = order(client, hdr)
    monkeypatch.undo()
    assert r.status_code == 409
    assert db.query(Order).count() == 0
    assert stock(db, "alpha-low", "8") == 2          # first line's decrement was rolled back


def test_logs_do_not_contain_customer_data(client, hdr, db, caplog):
    add(client, hdr, product_id(db, "alpha-low"))
    with caplog.at_level(logging.DEBUG):
        order(client, hdr)
    text = caplog.text
    assert "order_recorded" in text
    for private in ["ada@example.com", "Ada Example", "1 Test Street"]:
        assert private not in text


def test_whitespace_and_control_characters_are_cleaned(client, hdr, db):
    add(client, hdr, product_id(db, "alpha-low"))
    order(client, hdr, customer_name="  Ada\x00 Example  ")
    assert db.query(Order).one().customer_name == "Ada Example"


def test_html_in_fields_is_escaped_on_confirmation(client, hdr, db):
    add(client, hdr, product_id(db, "alpha-low"))
    ref = order(client, hdr, shipping_line1="<script>alert(1)</script>").json()["order_ref"]
    html = client.get(f"/orders/{ref}").text
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html


def test_two_buyers_cannot_oversell_last_pair(app, db):
    """Sequential stand-in for concurrency: the second buyer must lose cleanly."""
    pid = product_id(db, "beta-high")
    db.query(ProductSize).filter_by(product_id=pid, size="9").update({"stock": 1})
    db.commit()
    buyers = []
    for i in range(2):
        c = TestClient(app)
        h = csrf_headers(c)
        add(c, h, pid, "9", 1)
        buyers.append((c, h, i))
    results = [order(c, h, idempotency_key=f"{i}" * 32).status_code for c, h, i in buyers]
    assert sorted(results) == [201, 409]
    assert stock(db, "beta-high", "9") == 0
