"""Fictional demonstration catalogue. None of these products exist; images are original illustrations."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Product, ProductSize

CARE = "Spot-clean with a soft cloth and dry naturally away from direct heat. Demonstration product: no real materials or care data."

# (slug, name, description, price, category, color, silhouette, badge, stock-by-size)
SAMPLE = [
    ("noir-01", "NOIR / 01",
     "A near-black low profile with a restrained champagne accent. The pared-back lines let the silhouette do the talking.",
     "245.00", "essentials", "Noir / Champagne", "Low", "New Arrival",
     {"7": 3, "8": 5, "8.5": 4, "9": 6, "9.5": 2, "10": 5, "11": 3, "12": 0}),
    ("chrome-runner", "CHROME RUNNER",
     "A sculpted runner in brushed silver with a single electric-blue line. Built to be noticed from across the street.",
     "289.00", "statement-silhouettes", "Chrome / Electric Blue", "Runner", "Limited Release",
     {"7": 0, "8": 2, "9": 3, "10": 2, "11": 1}),
    ("atelier-low", "ATELIER LOW",
     "The house low-top in warm ivory. Quiet, versatile and easy to wear every day.",
     "225.00", "essentials", "Ivory / Champagne", "Low", None,
     {"6": 4, "7": 6, "8": 8, "9": 8, "10": 6, "11": 4}),
    ("monolith-high", "MONOLITH HIGH",
     "A tall, architectural high-top in charcoal with an ivory sole. Presence without ornament.",
     "310.00", "contemporary-classics", "Charcoal / Ivory", "High", "Limited Release",
     {"8": 2, "9": 2, "10": 3, "11": 2}),
    ("velocity-form", "VELOCITY FORM",
     "Forward-leaning runner lines in charcoal and ivory, with a blue sole detail for pace.",
     "265.00", "statement-silhouettes", "Charcoal / Ivory / Blue", "Runner", "New Arrival",
     {"7": 3, "8": 4, "9": 5, "10": 4, "11": 2}),
    ("studio-04", "STUDIO 04",
     "A soft stone low-top for the studio and the street. A neutral that goes with everything.",
     "235.00", "contemporary-classics", "Stone / Ivory", "Low", None,
     {"7": 3, "8": 5, "9": 5, "10": 4, "11": 3}),
]


def seed_if_empty(db: Session) -> int:
    """Insert the sample catalogue only when the products table is empty. Never deletes anything."""
    if db.scalar(select(func.count(Product.id))):
        return 0
    base = datetime.now(timezone.utc) - timedelta(days=30)
    for i, (slug, name, desc, price, cat, color, sil, badge, stock) in enumerate(SAMPLE):
        product = Product(
            slug=slug, name=name, description=desc, details=CARE, price=Decimal(price), category=cat,
            color=color, silhouette=sil, image=f"/static/images/products/{slug}.svg", badge=badge,
            is_active=True, created_at=base + timedelta(days=i * 5),
        )
        product.sizes = [ProductSize(size=s, sort_key=int(float(s) * 10), stock=n) for s, n in stock.items()]
        db.add(product)
    db.commit()
    return len(SAMPLE)
