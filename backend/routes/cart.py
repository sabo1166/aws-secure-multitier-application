"""Cart API. Every response is recomputed from the database; the browser is never the source of truth."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..config import Settings
from ..deps import get_db, get_settings
from ..schemas import CartAdd, CartUpdate
from ..security import require_csrf
from ..services import cart as cart_service

router = APIRouter(prefix="/api/cart", tags=["cart"], dependencies=[Depends(require_csrf)])


def view_json(cart: cart_service.CartView) -> dict:
    return {
        "count": cart.count,
        "subtotal": str(cart.subtotal),
        "has_issues": cart.has_issues,
        "items": [
            {
                "item_id": l.item_id,
                "product_id": l.product.id if l.product else None,
                "name": l.product.name if l.product else None,
                "size": l.size,
                "quantity": l.quantity,
                "unit_price": str(l.unit_price),
                "line_total": str(l.line_total),
                "available": l.available,
                "issue": l.issue,
            }
            for l in cart.lines
        ],
    }


@router.get("")
def get_cart(request: Request, db: Session = Depends(get_db)):
    return view_json(cart_service.build_cart(db, request.session))


@router.post("/items", status_code=201)
def add_item(body: CartAdd, request: Request, db: Session = Depends(get_db), s: Settings = Depends(get_settings)):
    item_id = cart_service.add_item(db, request.session, body.product_id, body.size, body.quantity, s.max_qty_per_line, s.max_cart_lines)
    return {"item_id": item_id, **view_json(cart_service.build_cart(db, request.session))}


@router.patch("/items/{item_id}")
def update_item(item_id: str, body: CartUpdate, request: Request, db: Session = Depends(get_db), s: Settings = Depends(get_settings)):
    cart_service.update_item(db, request.session, item_id, body.quantity, s.max_qty_per_line)
    return view_json(cart_service.build_cart(db, request.session))


@router.delete("/items/{item_id}")
def delete_item(item_id: str, request: Request, db: Session = Depends(get_db)):
    cart_service.remove_item(request.session, item_id)
    return view_json(cart_service.build_cart(db, request.session))
