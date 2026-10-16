"""Cart API: validation, stock limits, CSRF, server-side pricing."""
from decimal import Decimal

from .conftest import product_id


def add(client, hdr, pid, size="8", quantity=1):
    return client.post("/api/cart/items", json={"product_id": pid, "size": size, "quantity": quantity}, headers=hdr)


def test_add_item_returns_priced_cart(client, hdr, db):
    r = add(client, hdr, product_id(db, "alpha-low"), "8", 2)
    assert r.status_code == 201
    body = r.json()
    assert body["count"] == 2 and body["subtotal"] == "200.00"
    assert body["items"][0]["unit_price"] == "100.00" and body["items"][0]["line_total"] == "200.00"


def test_adding_same_item_accumulates_up_to_stock(client, hdr, db):
    pid = product_id(db, "alpha-low")
    assert add(client, hdr, pid, "8", 1).status_code == 201
    assert add(client, hdr, pid, "8", 1).json()["count"] == 2
    r = add(client, hdr, pid, "8", 1)  # stock for size 8 is 2
    assert r.status_code == 409 and r.json()["error"]["code"] == "quantity_limit"


def test_state_changing_requests_require_csrf(client, db):
    pid = product_id(db, "alpha-low")
    body = {"product_id": pid, "size": "8", "quantity": 1}
    assert client.post("/api/cart/items", json=body).status_code == 403
    assert client.post("/api/cart/items", json=body, headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert client.delete("/api/cart/items/1_8").status_code == 403
    assert client.get("/api/cart").status_code == 200  # reads need no token


def test_csrf_token_does_not_work_across_sessions(app, db):
    from fastapi.testclient import TestClient
    from .conftest import csrf_headers
    a, b = TestClient(app), TestClient(app)
    token_a = csrf_headers(a)
    r = b.post("/api/cart/items", json={"product_id": product_id(db, "alpha-low"), "size": "8", "quantity": 1}, headers=token_a)
    assert r.status_code == 403


def test_rejects_invalid_input(client, hdr, db):
    pid = product_id(db, "alpha-low")
    bad = [
        {"product_id": pid, "size": "8", "quantity": 0},
        {"product_id": pid, "size": "8", "quantity": -3},
        {"product_id": pid, "size": "8", "quantity": 999},
        {"product_id": pid, "size": "abc", "quantity": 1},
        {"product_id": pid, "size": "8; DROP TABLE products", "quantity": 1},
        {"product_id": "x", "size": "8", "quantity": 1},
        {"product_id": pid, "size": "8", "quantity": 1, "price": "0.01"},  # client-sent price is refused outright
    ]
    for payload in bad:
        r = client.post("/api/cart/items", json=payload, headers=hdr)
        assert r.status_code == 422, payload
        assert r.json()["error"]["code"] == "validation_error"
    assert client.get("/api/cart").json()["count"] == 0


def test_size_not_offered_sold_out_and_unknown_product(client, hdr, db):
    pid = product_id(db, "alpha-low")
    assert add(client, hdr, pid, "11").status_code == 422          # size not offered
    r = add(client, hdr, pid, "9")                                  # stock 0
    assert r.status_code == 409 and r.json()["error"]["code"] == "sold_out"
    assert add(client, hdr, 99999).status_code == 404
    assert add(client, hdr, product_id(db, "ghost-hidden")).status_code == 404  # inactive


def test_update_quantity_and_stock_cap(client, hdr, db):
    pid = product_id(db, "alpha-low")
    item = add(client, hdr, pid, "10", 1).json()["item_id"]
    r = client.patch(f"/api/cart/items/{item}", json={"quantity": 4}, headers=hdr)
    assert r.status_code == 200 and r.json()["subtotal"] == "400.00"
    assert client.patch(f"/api/cart/items/{item}", json={"quantity": 6}, headers=hdr).status_code == 409  # max 5 per line
    assert client.patch(f"/api/cart/items/{item}", json={"quantity": 0}, headers=hdr).status_code == 422
    assert client.patch("/api/cart/items/999_8", json={"quantity": 1}, headers=hdr).status_code == 404
    assert client.patch("/api/cart/items/not-an-id", json={"quantity": 1}, headers=hdr).status_code == 404


def test_update_over_available_stock(client, hdr, db):
    item = add(client, hdr, product_id(db, "alpha-low"), "8", 1).json()["item_id"]
    r = client.patch(f"/api/cart/items/{item}", json={"quantity": 3}, headers=hdr)  # stock is 2
    assert r.status_code == 409


def test_remove_item(client, hdr, db):
    item = add(client, hdr, product_id(db, "alpha-low"), "8", 1).json()["item_id"]
    r = client.delete(f"/api/cart/items/{item}", headers=hdr)
    assert r.status_code == 200 and r.json()["count"] == 0
    assert client.delete(f"/api/cart/items/{item}", headers=hdr).status_code == 404


def test_subtotal_sums_multiple_lines_with_decimal_precision(client, hdr, db):
    add(client, hdr, product_id(db, "alpha-low"), "8", 2)       # 200.00
    add(client, hdr, product_id(db, "beta-high"), "9", 3)       # 751.50
    body = client.get("/api/cart").json()
    assert Decimal(body["subtotal"]) == Decimal("951.50") and body["count"] == 5


def test_server_reprices_when_database_price_changes(client, hdr, db):
    pid = product_id(db, "alpha-low")
    add(client, hdr, pid, "8", 1)
    from backend.models import Product
    db.query(Product).filter_by(id=pid).update({"price": Decimal("123.45")})
    db.commit()
    assert client.get("/api/cart").json()["subtotal"] == "123.45"


def test_cart_flags_items_that_become_unavailable(client, hdr, db):
    from backend.models import Product, ProductSize
    pid = product_id(db, "alpha-low")
    add(client, hdr, pid, "8", 2)
    db.query(ProductSize).filter_by(product_id=pid, size="8").update({"stock": 1})
    db.commit()
    body = client.get("/api/cart").json()
    assert body["has_issues"] and body["items"][0]["issue"] == "Only 1 left in this size"
    assert body["subtotal"] == "0.00"                    # issue lines are never charged
    db.query(Product).filter_by(id=pid).update({"is_active": False})
    db.commit()
    assert client.get("/api/cart").json()["items"][0]["issue"] == "No longer available"


def test_cart_page_and_badge_reflect_session(client, hdr, db):
    assert "Your bag is empty" in client.get("/cart").text
    add(client, hdr, product_id(db, "alpha-low"), "8", 2)
    html = client.get("/cart").text
    assert "ALPHA LOW" in html and "$200.00" in html
    assert 'data-cart-count>2<' in client.get("/").text


def test_tampered_cookie_is_ignored(client, hdr, db):
    add(client, hdr, product_id(db, "alpha-low"), "8", 1)
    client.cookies.set("sole_session", "forged.value.signature")
    assert client.get("/api/cart").json()["count"] == 0
    assert client.get("/cart").status_code == 200


def test_quantity_can_always_be_reduced_even_when_stock_dropped(client, hdr, db):
    """The bag tells the customer to 'update or remove' a line whose stock fell. Reducing must work."""
    from backend.models import ProductSize
    pid = product_id(db, "alpha-low")
    item = add(client, hdr, pid, "10", 3).json()["item_id"]       # size 10 had stock 5
    db.query(ProductSize).filter_by(product_id=pid, size="10").update({"stock": 1})
    db.commit()
    assert client.get("/api/cart").json()["items"][0]["issue"] == "Only 1 left in this size"

    r = client.patch(f"/api/cart/items/{item}", json={"quantity": 2}, headers=hdr)   # one step down, still above stock
    assert r.status_code == 200 and r.json()["items"][0]["quantity"] == 2
    r = client.patch(f"/api/cart/items/{item}", json={"quantity": 1}, headers=hdr)
    assert r.status_code == 200 and r.json()["has_issues"] is False and r.json()["subtotal"] == "100.00"


def test_increasing_still_respects_stock_after_the_fix(client, hdr, db):
    from backend.models import ProductSize
    pid = product_id(db, "alpha-low")
    item = add(client, hdr, pid, "10", 1).json()["item_id"]
    db.query(ProductSize).filter_by(product_id=pid, size="10").update({"stock": 1})
    db.commit()
    assert client.patch(f"/api/cart/items/{item}", json={"quantity": 2}, headers=hdr).status_code == 409


def test_quantity_can_be_reduced_when_product_or_size_is_gone(client, hdr, db):
    from backend.models import Product, ProductSize
    pid = product_id(db, "alpha-low")
    item = add(client, hdr, pid, "10", 3).json()["item_id"]
    db.query(Product).filter_by(id=pid).update({"is_active": False})
    db.commit()
    assert client.patch(f"/api/cart/items/{item}", json={"quantity": 2}, headers=hdr).status_code == 200
    assert client.patch(f"/api/cart/items/{item}", json={"quantity": 3}, headers=hdr).status_code == 404   # cannot grow an unavailable line
    assert client.delete(f"/api/cart/items/{item}", headers=hdr).status_code == 200
