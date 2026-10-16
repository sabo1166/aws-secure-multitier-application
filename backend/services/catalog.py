"""Read-side product queries. All filtering goes through SQLAlchemy expressions (parameterised)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import Product

COLLECTIONS = {
    "essentials": "The Essentials",
    "contemporary-classics": "Contemporary Classics",
    "statement-silhouettes": "Statement Silhouettes",
}
SORTS = {
    "featured": "Featured",
    "newest": "Newest",
    "price_asc": "Price: low to high",
    "price_desc": "Price: high to low",
}
NEW_BADGE = "New Arrival"


def list_products(
    db: Session, q: str = "", category: str = "", sort: str = "featured", new_only: bool = False
) -> list[Product]:
    stmt = select(Product).where(Product.is_active.is_(True)).options(selectinload(Product.sizes))
    q = q.strip()[:80]
    if q:
        stmt = stmt.where(Product.name.icontains(q, autoescape=True))
    if category in COLLECTIONS:
        stmt = stmt.where(Product.category == category)
    if new_only:
        stmt = stmt.where(Product.badge == NEW_BADGE)
    order = {
        "newest": (Product.created_at.desc(), Product.id.desc()),
        "price_asc": (Product.price.asc(), Product.id.asc()),
        "price_desc": (Product.price.desc(), Product.id.asc()),
    }.get(sort, (Product.id.asc(),))
    return list(db.scalars(stmt.order_by(*order)))


def get_product_by_slug(db: Session, slug: str) -> Product | None:
    stmt = select(Product).where(Product.slug == slug, Product.is_active.is_(True)).options(selectinload(Product.sizes))
    return db.scalars(stmt).first()
