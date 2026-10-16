"""JSON catalogue API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db
from ..schemas import ProductOut
from ..services.catalog import SORTS, get_product_by_slug, list_products

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
def api_list(db: Session = Depends(get_db), q: str = "", category: str = "", sort: str = "featured", new: bool = False):
    if sort not in SORTS:
        raise HTTPException(status_code=422, detail=f"sort must be one of: {', '.join(SORTS)}")
    return list_products(db, q=q, category=category, sort=sort, new_only=new)


@router.get("/{slug}", response_model=ProductOut)
def api_detail(slug: str, db: Session = Depends(get_db)):
    product = get_product_by_slug(db, slug)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
