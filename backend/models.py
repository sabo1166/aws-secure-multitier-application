"""Database schema (SQLAlchemy 2.0). Works on SQLite and MySQL 8.

Money uses Numeric(10, 2) (decimal-safe, never float). Sizes are normalised into their own table so
stock is tracked per size, which is what a customer actually buys.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_products_price_nonneg"),
        Index("ix_products_category", "category"),
        Index("ix_products_active_created", "is_active", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    details: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    category: Mapped[str] = mapped_column(String(40))
    color: Mapped[str] = mapped_column(String(60))
    silhouette: Mapped[str] = mapped_column(String(40), default="")
    image: Mapped[str] = mapped_column(String(255))
    badge: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    sizes: Mapped[list["ProductSize"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="ProductSize.sort_key"
    )

    @property
    def total_stock(self) -> int:
        return sum(s.stock for s in self.sizes)

    @property
    def in_stock(self) -> bool:
        return self.is_active and self.total_stock > 0


class ProductSize(Base):
    __tablename__ = "product_sizes"
    __table_args__ = (CheckConstraint("stock >= 0", name="ck_product_sizes_stock_nonneg"),)

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    size: Mapped[str] = mapped_column(String(8), primary_key=True)
    sort_key: Mapped[int] = mapped_column(Integer, default=0)  # size x 10, keeps 8.5 after 8
    stock: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped[Product] = relationship(back_populates="sizes")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("subtotal >= 0 AND total >= 0", name="ck_orders_amounts_nonneg"),
        Index("ix_orders_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True)  # unguessable reference shown to customers
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)
    customer_name: Mapped[str] = mapped_column(String(120))
    customer_email: Mapped[str] = mapped_column(String(254))
    shipping_line1: Mapped[str] = mapped_column(String(160))
    shipping_line2: Mapped[str] = mapped_column(String(160), default="")
    shipping_city: Mapped[str] = mapped_column(String(80))
    shipping_postal_code: Mapped[str] = mapped_column(String(20))
    shipping_country: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20), default="demo_pending")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_qty_positive"),
        Index("ix_order_items_order", "order_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    product_name: Mapped[str] = mapped_column(String(120))  # snapshot: survives later renames
    size: Mapped[str] = mapped_column(String(8))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # snapshot at order time
    line_total: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    order: Mapped[Order] = relationship(back_populates="items")
