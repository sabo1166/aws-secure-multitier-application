"""Server-rendered storefront pages."""
from __future__ import annotations

import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import engineering
from ..deps import get_db, render
from ..services import cart as cart_service
from ..services.catalog import COLLECTIONS, SORTS, get_product_by_slug, list_products
from ..services.orders import get_order_by_public_id

router = APIRouter()

JOURNAL = [
    ("On the quiet silhouette", "Why the best low-tops disappear on the foot and stay in the memory.",
     "A restrained shape asks more of its proportions. When there is no ornament to hide behind, the curve of the toe box, the height of the collar and the weight of the sole all have to be right. We look for sneakers where they are."),
    ("Colour in small doses", "One accent, placed with intent.",
     "Champagne on black. Electric blue on silver. A single considered accent makes a neutral pair feel designed rather than default, and keeps it wearable for years."),
    ("Curating, not collecting", "How a short list becomes a point of view.",
     "A boutique is defined by what it leaves out. Our shelves are short on purpose: every pair earns its place by being distinctive, well proportioned and genuinely wearable."),
]


@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    products = list_products(db)
    return render(request, "home.html", featured=products[:4], total=len(products))


@router.get("/shop")
def shop(request: Request, db: Session = Depends(get_db), q: str = "", category: str = "", sort: str = "featured", new: bool = False):
    if sort not in SORTS:
        sort = "featured"
    if category and category not in COLLECTIONS:
        category = ""
    products = list_products(db, q=q, category=category, sort=sort, new_only=new)

    def href(**params) -> str:
        keep = {"q": q.strip()[:80], "sort": sort if sort != "featured" else "", **params}
        query = urlencode({k: v for k, v in keep.items() if v})
        return "/shop" + (f"?{query}" if query else "")

    chips = [("All", href(), not category and not new)]
    chips += [(label, href(category=slug), category == slug and not new) for slug, label in COLLECTIONS.items()]
    chips.append(("New Arrivals", href(new="true"), new))
    return render(request, "shop.html", products=products, q=q.strip()[:80], category=category, sort=sort, sorts=SORTS, new=new, chips=chips)


@router.get("/products/{slug}")
def product_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    product = get_product_by_slug(db, slug)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    related = [p for p in list_products(db, category=product.category) if p.id != product.id][:3]
    return render(request, "product.html", product=product, related=related)


@router.get("/collections")
def collections_page(request: Request, db: Session = Depends(get_db)):
    counts = {slug: len(list_products(db, category=slug)) for slug in COLLECTIONS}
    new_count = len(list_products(db, new_only=True))
    return render(request, "collections.html", counts=counts, new_count=new_count)


@router.get("/roadmap")
def roadmap_page(request: Request):
    return render(request, "roadmap.html", roadmap=engineering.roadmap())


@router.get("/architecture")
def architecture_page(request: Request):
    return render(request, "architecture.html", arch=engineering.architecture())


@router.get("/journal")
def journal(request: Request):
    return render(request, "journal.html", entries=JOURNAL)


@router.get("/about")
def about(request: Request):
    return render(request, "about.html")


@router.get("/policies")
def policies(request: Request):
    return render(request, "policies.html")


@router.get("/cart")
def cart_page(request: Request, db: Session = Depends(get_db)):
    cart = cart_service.build_cart(db, request.session)
    return render(request, "cart.html", cart=cart)


@router.get("/checkout")
def checkout_page(request: Request, db: Session = Depends(get_db)):
    cart =cart_service.build_cart(db, request.session)
    return render(request, "checkout.html", cart=cart, idempotency_key=secrets.token_hex(16))


@router.get("/orders/{public_id}")
def order_confirmation(public_id: str, request: Request, db: Session = Depends(get_db)):
    # Only the browser session that placed the order may view it (no account system exists).
    if public_id not in request.session.get("orders", []):
        raise HTTPException(status_code=404, detail="Order not found")
    order = get_order_by_public_id(db, public_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return render(request, "order.html", order=order)
