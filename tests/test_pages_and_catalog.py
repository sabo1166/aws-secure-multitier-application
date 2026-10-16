"""Storefront pages, catalogue API, search, filtering and sorting."""
import re

import pytest


def names(html: str) -> list[str]:
    return re.findall(r'<h3><a href="/products/[^"]+">([^<]+)</a></h3>', html)


def test_homepage_renders_brand_and_nav(client):
    r = client.get("/")
    assert r.status_code == 200
    for text in ["SOLE", "Built Different.", "Worn Rare.", "Explore the Collection", "Discover the Atelier", "The Journal", "New Arrivals"]:
        assert text in r.text
    assert 'data-cart-count>0<' in r.text


def test_homepage_featured_excludes_inactive(client):
    assert "GHOST HIDDEN" not in client.get("/").text


def test_shop_lists_only_active_products(client):
    found = names(client.get("/shop").text)
    assert "ALPHA LOW" in found and "GHOST HIDDEN" not in found
    assert len(found) == 4


def test_search_by_name_is_case_insensitive(client):
    assert names(client.get("/shop?q=alpha").text) == ["ALPHA LOW"]


@pytest.mark.parametrize("q", ["%", "_", "' OR 1=1 --", "<script>alert(1)</script>"])
def test_search_special_characters_are_literal_not_wildcards(client, q):
    r = client.get("/shop", params={"q": q})
    assert r.status_code == 200
    assert names(r.text) == []
    assert "<script>alert(1)</script>" not in r.text  # echoed query is escaped


def test_search_no_results_shows_empty_state(client):
    r = client.get("/shop?q=zzzz")
    assert "Nothing matches" in r.text and "Clear filters" in r.text


def test_category_filter(client):
    assert sorted(names(client.get("/shop?category=essentials").text)) == ["ALPHA LOW", "GAMMA LOW"]


def test_unknown_category_is_ignored(client):
    assert len(names(client.get("/shop?category=bogus").text)) == 4


def test_new_arrivals_uses_badge_data(client):
    assert names(client.get("/shop?new=true").text) == ["ALPHA LOW"]


def test_sort_price_ascending_and_descending(client):
    asc = names(client.get("/shop?sort=price_asc").text)
    desc = names(client.get("/shop?sort=price_desc").text)
    assert asc == list(reversed(desc))
    assert asc[0] == "ALPHA LOW" and asc[-1] == "BETA HIGH"


def test_sort_newest_first(client):
    assert names(client.get("/shop?sort=newest").text)[0] == "SOLD OUT PAIR"  # created now, newest


def test_invalid_sort_falls_back_to_featured(client):
    assert client.get("/shop?sort=hacked").status_code == 200


def test_product_detail_shows_sizes_and_stock_state(client):
    html = client.get("/products/alpha-low").text
    assert "ALPHA LOW" in html and "$100.00" in html
    assert re.search(r'id="size-9"[^>]*disabled', html)           # size 9 has stock 0
    assert not re.search(r'id="size-8"[^>]*disabled', html)
    assert "In stock" in html


def test_sold_out_product_is_not_shown_as_in_stock(client):
    html = client.get("/products/sold-out").text
    assert "Sold out" in html and "Add to bag" not in html


def test_unknown_and_inactive_products_404_without_internals(client):
    for slug in ["does-not-exist", "ghost-hidden"]:
        r = client.get(f"/products/{slug}")
        assert r.status_code == 404
        assert "Traceback" not in r.text and "sqlalchemy" not in r.text.lower()


@pytest.mark.parametrize("path", ["/collections", "/journal", "/about", "/policies", "/cart", "/checkout"])
def test_secondary_pages_render(client, path):
    assert client.get(path).status_code == 200


def test_nav_links_all_resolve(client):
    html = client.get("/").text
    for href in set(re.findall(r'<a [^>]*href="(/[^"#]*)"', html)):
        assert client.get(href).status_code == 200, href


def test_static_assets_served(client):
    assert client.get("/static/css/site.css").status_code == 200
    assert client.get("/static/images/hero.svg").status_code == 200
    assert client.get("/static/fonts/inter-latin-400-normal.woff2").status_code == 200


def test_security_headers(client):
    h = client.get("/").headers
    assert "script-src 'self'" in h["content-security-policy"]
    assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY"
    assert client.get("/api/products").headers["cache-control"] == "no-store"


# ---- JSON API ----
def test_api_list_and_detail(client):
    data = client.get("/api/products").json()
    assert {p["slug"] for p in data} == {"alpha-low", "beta-high", "gamma-low", "sold-out"}
    one = client.get("/api/products/alpha-low").json()
    assert one["price"] == "100.00" and one["in_stock"] is True
    assert {"size": "9", "stock": 0} in one["sizes"]


def test_api_filters_and_errors(client):
    assert [p["slug"] for p in client.get("/api/products?q=beta").json()] == ["beta-high"]
    assert client.get("/api/products/nope").status_code == 404
    assert client.get("/api/products/nope").json()["error"]["code"] == "http_404"
    assert client.get("/api/products?sort=bad").status_code == 422
    assert client.get("/api/products/ghost-hidden").status_code == 404


def test_session_cookie_flags_and_sensitive_pages_not_cached(client):
    cookie = client.get("/").headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert "secure" not in cookie.replace("samesite", "")          # off by default: site is HTTP-only (documented)
    for path in ["/cart", "/checkout", "/api/cart"]:
        assert client.get(path).headers["cache-control"] == "no-store"


def test_secure_cookie_flag_when_https_enabled(settings, engine):
    from dataclasses import replace
    from fastapi.testclient import TestClient
    from backend.main import create_app
    app = create_app(replace(settings, session_https_only=True), engine)
    assert "secure" in TestClient(app, base_url="https://testserver").get("/").headers["set-cookie"].lower()


def test_templates_use_no_inline_script_or_style():
    """The CSP forbids inline script/style; guard the templates so a regression is caught early."""
    import pathlib
    for f in pathlib.Path("frontend/templates").glob("*.html"):
        text = f.read_text(encoding="utf-8")
        assert "<script>" not in text and " style=" not in text and "onclick=" not in text, f.name
