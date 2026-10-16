"""Health checks, failure handling, persistence, configuration and database selection."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from backend.config import Settings
from backend.database import build_database_url, make_engine, make_session_factory, resolve_credentials
from backend.main import create_app
from backend.models import Order
from .conftest import VALID_ORDER, csrf_headers, product_id


# ---- health ----
def test_liveness_does_not_depend_on_database(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_readiness_checks_database(client):
    assert client.get("/health/ready").json() == {"status": "ok", "database": "ok"}


class BrokenSession:
    """Simulates RDS being unreachable. The message contains a fake hostname that must never leak."""
    def _fail(self, *a, **k):
        raise OperationalError("SELECT 1", {}, Exception("connection refused to db.internal.example:3306 user=sole_app"))
    execute = scalars = scalar = commit = rollback = _fail
    def close(self): pass


@pytest.fixture()
def broken_client(app):
    app.state.session_factory = lambda: BrokenSession()
    return TestClient(app)


def test_database_outage_returns_503_without_internals(broken_client):
    for path in ["/shop", "/api/products", "/products/alpha-low", "/collections"]:
        r = broken_client.get(path)
        assert r.status_code == 503, path
        assert "db.internal.example" not in r.text and "sole_app" not in r.text and "OperationalError" not in r.text


def test_api_error_shape_on_outage(broken_client):
    body = broken_client.get("/api/products").json()
    assert body["error"]["code"] == "database_unavailable"


def test_liveness_survives_outage_but_readiness_reports_it(broken_client):
    assert broken_client.get("/health").status_code == 200
    r = broken_client.get("/health/ready")
    assert r.status_code == 503 and "db.internal" not in r.text


def test_unexpected_errors_are_generic(app, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("internal-detail-do-not-leak")
    monkeypatch.setattr("backend.routes.pages.list_products", boom)
    r = TestClient(app, raise_server_exceptions=False).get("/shop")
    assert r.status_code == 500 and "internal-detail-do-not-leak" not in r.text
    assert "Something went wrong" in r.text


def test_method_not_allowed_and_json_404(client):
    assert client.post("/shop").status_code == 405
    assert client.get("/api/nope").json()["error"]["code"] == "http_404"


# ---- persistence ----
def test_orders_persist_across_app_restart(settings, tmp_path):
    url = f"sqlite:///{tmp_path / 'persist.db'}"
    from backend.models import Base
    from tests.conftest import make_product
    engine = make_engine(url, settings)
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as db:
        make_product(db, "p", "P", "10.00", "essentials", {"8": 3}); db.commit()

    first = TestClient(create_app(settings, engine))
    h = csrf_headers(first)
    pid = first.get("/api/products/p").json()["id"]
    first.post("/api/cart/items", json={"product_id": pid, "size": "8", "quantity": 2}, headers=h)
    ref = first.post("/api/orders", json=VALID_ORDER, headers=h).json()["order_ref"]
    engine.dispose()

    engine2 = make_engine(url, settings)                     # "restart": brand-new engine, same file
    with make_session_factory(engine2)() as db:
        saved = db.query(Order).filter_by(public_id=ref).one()
        assert str(saved.total) == "20.00" and saved.items[0].quantity == 2
    assert TestClient(create_app(settings, engine2)).get("/api/products/p").json()["sizes"][0]["stock"] == 1


# ---- configuration ----
def test_production_requires_strong_secret_and_real_database():
    base = dict(app_env="production", session_secret="s" * 40, db_host="rds.example")
    Settings(**base).validate()
    with pytest.raises(RuntimeError, match="SESSION_SECRET"):
        Settings(**{**base, "session_secret": "replace-with-a-random-secret"}).validate()
    with pytest.raises(RuntimeError, match="SESSION_SECRET"):
        Settings(**{**base, "session_secret": "short"}).validate()
    with pytest.raises(RuntimeError, match="never falls back"):
        Settings(app_env="production", session_secret="s" * 40).validate()
    with pytest.raises(RuntimeError, match="SQLite"):
        Settings(app_env="production", session_secret="s" * 40, database_url="sqlite:///x.db").validate()
    with pytest.raises(RuntimeError, match="APP_ENV"):
        Settings(app_env="staging").validate()


def test_production_hides_api_docs(tmp_path):
    s = Settings(app_env="production", session_secret="s" * 40, db_host="127.0.0.1")
    eng = make_engine(f"sqlite:///{tmp_path / 'p.db'}", s)
    assert TestClient(create_app(s, eng)).get("/docs").status_code == 404


def test_database_url_takes_precedence_for_sqlite():
    assert build_database_url(Settings(database_url="sqlite:///./x.db", db_host="ignored")) == "sqlite:///./x.db"


def test_mysql_url_is_built_from_parts_and_escapes_password():
    s = Settings(db_host="rds.example", db_name="shop", db_user="sole_app", db_password="p@ss/w:rd#1")
    url = build_database_url(s)
    assert url.drivername == "mysql+pymysql" and url.host == "rds.example" and url.database == "shop"
    assert url.password == "p@ss/w:rd#1"                       # stored raw ...
    assert "p%40ss%2Fw%3Ard%231" in url.render_as_string(hide_password=False)   # ... escaped when rendered
    assert "p@ss" not in repr(url) and "***" in repr(url)       # never printed in logs


def test_credentials_come_from_secrets_manager_when_arn_set():
    calls = []

    def fake_fetch(arn, region):
        calls.append((arn, region))
        return '{"username": "sole_app", "password": "from-secret"}'

    s = Settings(db_host="rds.example", db_secret_arn="arn:aws:secretsmanager:eu-west-1:000000000000:secret:x", aws_region="eu-west-1", db_password="ignored")
    assert resolve_credentials(s, fake_fetch) == ("sole_app", "from-secret")
    assert calls == [(s.db_secret_arn, "eu-west-1")]
    assert build_database_url(s, fake_fetch).password == "from-secret"


def test_mysql_engine_created_lazily_with_tls_ca(tmp_path):
    s = Settings(db_host="rds.example", db_user="u", db_password="p", db_ssl_ca="/opt/ca.pem")
    engine = make_engine(build_database_url(s), s)             # must not try to connect
    assert engine.dialect.name == "mysql" and engine.pool._pre_ping is True


def test_sqlite_enforces_foreign_keys(engine):
    from sqlalchemy import text
    with engine.connect() as c:
        assert c.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_database_constraints_reject_bad_data(db):
    from sqlalchemy.exc import IntegrityError
    from backend.models import ProductSize
    pid = product_id(db, "alpha-low")
    db.add(ProductSize(product_id=pid, size="12", stock=-1))
    with pytest.raises(IntegrityError):
        db.commit()


# ---- newsletter demo ----
def test_newsletter_is_honest_demo(client, hdr):
    r = client.post("/api/newsletter", json={"email": "a@example.com"}, headers=hdr)
    assert r.status_code == 200 and r.json()["stored"] is False and "not stored" in r.json()["message"]
    assert client.post("/api/newsletter", json={"email": "nope"}, headers=hdr).status_code == 422
    assert client.post("/api/newsletter", json={"email": "a@example.com"}).status_code == 403


# ---- seed / init ----
def test_seed_inserts_demo_catalogue_once(tmp_path, settings):
    from backend.seed import seed_if_empty
    from backend.models import Base, Product
    eng = make_engine(f"sqlite:///{tmp_path / 's.db'}", settings)
    Base.metadata.create_all(eng)
    with make_session_factory(eng)() as db:
        assert seed_if_empty(db) == 6
        assert seed_if_empty(db) == 0
        assert db.query(Product).count() == 6


def test_init_db_is_non_destructive(tmp_path, monkeypatch, capsys):
    from backend import init_db
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'i.db'}")
    monkeypatch.chdir(tmp_path)
    assert init_db.main(["--seed"]) == 0
    assert init_db.main(["--seed"]) == 0
    out = capsys.readouterr().out
    assert "Seeded 6" in out and "nothing seeded" in out


def test_session_secret_can_come_from_secrets_manager():
    from backend.config import resolve_session_secret
    s = Settings(app_env="production", db_host="rds.example", session_secret_arn="arn:aws:secretsmanager:eu-west-1:000000000000:secret:s", aws_region="eu-west-1")
    s.validate()                                                    # allowed: secret is fetched at startup
    got = resolve_session_secret(s, lambda arn, region: '{"session_secret": "' + "k" * 48 + '"}')
    assert got.session_secret == "k" * 48
    with pytest.raises(RuntimeError, match="32 characters"):
        resolve_session_secret(s, lambda arn, region: '{"session_secret": "short"}')
    assert resolve_session_secret(Settings(session_secret="already-set")).session_secret == "already-set"
