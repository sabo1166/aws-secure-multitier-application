"""Orders, newsletter demo and health checks."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..deps import get_db
from ..schemas import NewsletterSignup, OrderCreate
from ..security import require_csrf
from ..services import cart as cart_service
from ..services.orders import create_order

log = logging.getLogger("sole_atelier")

api = APIRouter(prefix="/api", dependencies=[Depends(require_csrf)])
health = APIRouter()


@api.post("/orders")
def post_order(body: OrderCreate, request: Request, db: Session = Depends(get_db)):
    cart = cart_service.build_cart(db, request.session)
    order, created = create_order(db, cart, body)
    if created:
        cart_service.clear(request.session)
    orders = list(request.session.get("orders", []))
    if order.public_id not in orders:
        orders.append(order.public_id)
        request.session["orders"] = orders[-10:]
    # Log the event, never the customer's name, email or address.
    log.info("order_recorded id=%s items=%d created=%s", order.id, len(order.items), created)
    return JSONResponse(
        {"order_ref": order.public_id, "status": order.status, "total": str(order.total), "demo": True,
         "redirect": f"/orders/{order.public_id}"},
        status_code=201 if created else 200,
    )


@api.post("/newsletter")
def newsletter(body: NewsletterSignup):
    # Demonstration only: nothing is stored and no email is sent. The response says so.
    return {"stored": False, "demo": True, "message": "Demo only: your address was not stored and no email will be sent."}


@health.get("/health", tags=["health"])
def liveness():
    """Liveness for the load balancer. Deliberately does not touch the database, so a database blip
    does not make the load balancer pull every instance out of service."""
    return {"status": "ok"}


@health.get("/health/ready", tags=["health"])
def readiness(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        log.exception("readiness check failed")
        return JSONResponse({"status": "unavailable", "database": "error"}, status_code=503)
    return {"status": "ok", "database": "ok"}
