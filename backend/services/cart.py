"""Cart logic. The cart lives in the signed session cookie as {item_id: {product_id, size, qty}}.

Only identifiers and quantities are stored. Names, prices and stock are always re-read from the
database, so a tampered or stale cookie can never change what a customer is charged.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import Product

ITEM_ID = re.compile(r"^[0-9]{1,9}_[0-9]{1,2}(\.5)?$")
CENT = Decimal("0.01")


class CartError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


@dataclass
class CartLine:
    item_id: str
    product: Product | None
    size: str
    quantity: int
    unit_price: Decimal = Decimal("0.00")
    line_total: Decimal = Decimal("0.00")
    available: int = 0
    issue: str = ""


@dataclass
class CartView:
    lines: list[CartLine] = field(default_factory=list)
    subtotal: Decimal = Decimal("0.00")

    @property
    def count(self) -> int:
        return sum(l.quantity for l in self.lines)

    @property
    def has_issues(self) -> bool:
        return any(l.issue for l in self.lines)

    @property
    def is_empty(self) -> bool:
        return not self.lines


def item_id_for(product_id: int, size: str) -> str:
    return f"{product_id}_{size}"


def _raw(session: dict) -> dict:
    cart = session.get("cart")
    return cart if isinstance(cart, dict) else {}


def raw_count(session: dict) -> int:
    """Badge count without touching the database."""
    total = 0
    for entry in _raw(session).values():
        try:
            total += int(entry.get("qty", 0))
        except (AttributeError, TypeError, ValueError):
            continue
    return total


def build_cart(db: Session, session: dict) -> CartView:
    entries: dict[str, tuple[int, str, int]] = {}
    for item_id, entry in _raw(session).items():
        try:
            if not ITEM_ID.match(item_id):
                continue
            entries[item_id] = (int(entry["product_id"]), str(entry["size"]), int(entry["qty"]))
        except (KeyError, TypeError, ValueError):
            continue  # ignore malformed entries instead of failing the page
    ids = {pid for pid, _, _ in entries.values()}
    products = {}
    if ids:
        stmt = select(Product).where(Product.id.in_(ids)).options(selectinload(Product.sizes))
        products = {p.id: p for p in db.scalars(stmt)}

    view = CartView()
    for item_id, (pid, size, qty) in entries.items():
        product = products.get(pid)
        line = CartLine(item_id=item_id, product=product, size=size, quantity=qty)
        if product is None or not product.is_active:
            line.issue = "No longer available"
        else:
            stock = {s.size: s.stock for s in product.sizes}.get(size)
            line.unit_price = product.price.quantize(CENT)
            line.available = stock or 0
            if stock is None:
                line.issue = "This size is not offered"
            elif stock == 0:
                line.issue = "Sold out in this size"
            elif qty > stock:
                line.issue = f"Only {stock} left in this size"
            else:
                line.line_total = (line.unit_price * qty).quantize(CENT)
        view.lines.append(line)
    view.subtotal = sum((l.line_total for l in view.lines if not l.issue), Decimal("0.00"))
    return view


def _find_size_stock(db: Session, product_id: int, size: str) -> tuple[Product, int]:
    stmt = select(Product).where(Product.id == product_id).options(selectinload(Product.sizes))
    product = db.scalars(stmt).first()
    if product is None or not product.is_active:
        raise CartError("product_unavailable", "That product is not available", 404)
    stock = {s.size: s.stock for s in product.sizes}.get(size)
    if stock is None:
        raise CartError("invalid_size", "That size is not offered for this product", 422)
    if stock == 0:
        raise CartError("sold_out", "That size is sold out", 409)
    return product, stock


def add_item(db: Session, session: dict, product_id: int, size: str, quantity: int, max_per_line: int, max_lines: int) -> str:
    _, stock = _find_size_stock(db, product_id, size)
    cart = dict(_raw(session))
    item_id = item_id_for(product_id, size)
    if item_id not in cart and len(cart) >= max_lines:
        raise CartError("cart_full", "Your bag is full", 409)
    current = int(cart.get(item_id, {}).get("qty", 0))
    wanted = current + quantity
    limit = min(stock, max_per_line)
    if wanted > limit:
        raise CartError("quantity_limit", f"You can add at most {limit} of this size", 409)
    cart[item_id] = {"product_id": product_id, "size": size, "qty": wanted}
    session["cart"] = cart
    return item_id


def update_item(db: Session, session: dict, item_id: str, quantity: int, max_per_line: int) -> None:
    cart = dict(_raw(session))
    if not ITEM_ID.match(item_id) or item_id not in cart:
        raise CartError("not_in_cart", "That item is not in your bag", 404)
    pid, size = item_id.split("_", 1)
    current = int(cart[item_id].get("qty", 0))
    if quantity <= current:
        # A reduction never needs stock. Without this, a line whose stock fell below its quantity
        # could not be lowered one step at a time, although the bag tells the customer to "update or remove".
        cart[item_id] = {"product_id": int(pid), "size": size, "qty": quantity}
        session["cart"] = cart
        return
    _, stock = _find_size_stock(db, int(pid), size)
    limit = min(stock, max_per_line)
    if quantity > limit:
        raise CartError("quantity_limit", f"You can have at most {limit} of this size", 409)
    cart[item_id] = {"product_id": int(pid), "size": size, "qty": quantity}
    session["cart"] = cart


def remove_item(session: dict, item_id: str) -> None:
    cart = dict(_raw(session))
    if item_id not in cart:
        raise CartError("not_in_cart", "That item is not in your bag", 404)
    del cart[item_id]
    session["cart"] = cart


def clear(session: dict) -> None:
    session.pop("cart", None)
