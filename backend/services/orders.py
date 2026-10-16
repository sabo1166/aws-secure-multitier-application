"""Demonstration order creation.

What this does: recompute prices from the database, reserve stock with an atomic conditional UPDATE
inside one transaction, snapshot prices on the order lines, and make the request idempotent via a
client-supplied key. What it does not do: take payment, reserve stock with expiry, send email.
"""
from __future__ import annotations

import secrets
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import Order, OrderItem, ProductSize
from ..schemas import OrderCreate
from .cart import CENT, CartError, CartView

STATUS_DEMO = "demo_pending"


def _existing(db: Session, key: str) -> Order | None:
    return db.scalars(select(Order).where(Order.idempotency_key == key)).first()


def create_order(db: Session, cart: CartView, data: OrderCreate) -> tuple[Order, bool]:
    """Return (order, created). A repeated idempotency key returns the original order."""
    previous = _existing(db, data.idempotency_key)
    if previous is not None:
        return previous, False
    if cart.is_empty:
        raise CartError("empty_cart", "Your bag is empty", 409)
    if cart.has_issues:
        raise CartError("cart_issues", "Some items in your bag are unavailable. Review your bag and try again.", 409)

    subtotal = sum((l.line_total for l in cart.lines), Decimal("0.00")).quantize(CENT)
    order = Order(
        public_id=secrets.token_urlsafe(12),
        idempotency_key=data.idempotency_key,
        customer_name=data.customer_name,
        customer_email=str(data.customer_email),
        shipping_line1=data.shipping_line1,
        shipping_line2=data.shipping_line2,
        shipping_city=data.shipping_city,
        shipping_postal_code=data.shipping_postal_code,
        shipping_country=data.shipping_country,
        status=STATUS_DEMO,
        subtotal=subtotal,
        total=subtotal,  # demo shipping is free; no tax model
    )
    try:
        for line in cart.lines:
            # Atomic reservation: succeeds only if enough stock remains at this instant.
            result = db.execute(
                update(ProductSize)
                .where(
                    ProductSize.product_id == line.product.id,
                    ProductSize.size == line.size,
                    ProductSize.stock >= line.quantity,
                )
                .values(stock=ProductSize.stock - line.quantity)
            )
            if result.rowcount != 1:
                raise CartError("insufficient_stock", f"{line.product.name} (size {line.size}) just sold out", 409)
            order.items.append(
                OrderItem(
                    product_id=line.product.id,
                    product_name=line.product.name,
                    size=line.size,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    line_total=line.line_total,
                )
            )
        db.add(order)
        db.commit()
    except CartError:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        previous = _existing(db, data.idempotency_key)  # lost a race with an identical request
        if previous is not None:
            return previous, False
        raise
    except Exception:
        db.rollback()
        raise
    return order, True


def get_order_by_public_id(db: Session, public_id: str) -> Order | None:
    return db.scalars(select(Order).where(Order.public_id == public_id)).first()
