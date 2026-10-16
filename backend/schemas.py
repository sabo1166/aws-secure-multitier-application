"""Request/response validation. The server never trusts prices, totals or stock sent by the browser."""
from __future__ import annotations

import re
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean(value: str) -> str:
    """Trim, collapse inner whitespace runs on one line, and drop control characters."""
    return _CONTROL.sub("", value).strip()


class CartAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: int = Field(gt=0)
    size: str = Field(min_length=1, max_length=8, pattern=r"^[0-9]{1,2}(\.5)?$")
    quantity: int = Field(default=1, ge=1, le=20)


class CartUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quantity: int = Field(ge=1, le=20)


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_name: str = Field(min_length=2, max_length=120)
    customer_email: EmailStr
    shipping_line1: str = Field(min_length=3, max_length=160)
    shipping_line2: str = Field(default="", max_length=160)
    shipping_city: str = Field(min_length=2, max_length=80)
    shipping_postal_code: str = Field(min_length=3, max_length=20, pattern=r"^[A-Za-z0-9][A-Za-z0-9 \-]{1,18}[A-Za-z0-9]$")
    shipping_country: str = Field(min_length=2, max_length=60)
    idempotency_key: str = Field(min_length=16, max_length=64, pattern=r"^[A-Za-z0-9\-]+$")

    @field_validator(
        "customer_name", "shipping_line1", "shipping_line2", "shipping_city", "shipping_country", mode="before"
    )
    @classmethod
    def _clean_text(cls, v):
        return clean(v) if isinstance(v, str) else v


class NewsletterSignup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr


class SizeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    size: str
    stock: int


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name: str
    description: str
    price: Decimal
    category: str
    color: str
    image: str
    badge: str | None
    in_stock: bool
    sizes: list[SizeOut]
