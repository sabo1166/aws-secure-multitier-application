"""Test fixtures. Every test gets its own temporary SQLite file: tests never touch a real database."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.database import make_engine, make_session_factory
from backend.main import create_app
from backend.models import Base, Product, ProductSize

VALID_ORDER = {
    "customer_name": "Ada Example",
    "customer_email": "ada@example.com",
    "shipping_line1": "1 Test Street",
    "shipping_line2": "",
    "shipping_city": "Testville",
    "shipping_postal_code": "AB1 2CD",
    "shipping_country": "Testland",
    "idempotency_key": "0123456789abcdef0123456789abcdef",
}


def make_product(db, slug, name, price, category, sizes, badge=None, active=True, days_ago=0, color="Black"):
    product = Product(
        slug=slug, name=name, description=f"{name} description", details="care", price=Decimal(price),
        category=category, color=color, silhouette="Low", image=f"/static/images/products/{slug}.svg",
        badge=badge, is_active=active, created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )
    product.sizes = [ProductSize(size=s, sort_key=int(float(s) * 10), stock=n) for s, n in sizes.items()]
    db.add(product)
    return product


@pytest.fixture()
def settings():
    return Settings(app_env="test", session_secret="t" * 48)


@pytest.fixture()
def engine(tmp_path, settings):
    eng = make_engine(f"sqlite:///{tmp_path / 'test.db'}", settings)
    Base.metadata.create_all(eng)
    with make_session_factory(eng)() as db:
        make_product(db, "alpha-low", "ALPHA LOW", "100.00", "essentials", {"8": 2, "9": 0, "10": 5}, badge="New Arrival", days_ago=1)
        make_product(db, "beta-high", "BETA HIGH", "250.50", "statement-silhouettes", {"9": 3}, days_ago=10)
        make_product(db, "gamma-low", "GAMMA LOW", "180.00", "essentials", {"8": 4}, days_ago=5)
        make_product(db, "ghost-hidden", "GHOST HIDDEN", "99.00", "essentials", {"8": 5}, active=False)
        make_product(db, "sold-out", "SOLD OUT PAIR", "120.00", "contemporary-classics", {"8": 0, "9": 0})
        db.commit()
    return eng


@pytest.fixture()
def app(settings, engine):
    return create_app(settings, engine)


@pytest.fixture()
def db(app):
    with app.state.session_factory() as session:
        yield session


@pytest.fixture()
def client(app):
    return TestClient(app)


def csrf_headers(client: TestClient) -> dict:
    """Load a page like a browser would and echo the CSRF token from its <meta> tag."""
    html = client.get("/").text
    token = re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)
    return {"X-CSRF-Token": token}


@pytest.fixture()
def hdr(client):
    return csrf_headers(client)


def product_id(db, slug):
    return db.query(Product).filter_by(slug=slug).one().id
