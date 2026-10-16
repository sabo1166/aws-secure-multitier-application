"""Engine and session handling. SQLite locally, MySQL (Amazon RDS) in AWS, chosen by environment."""
from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings
from .secrets import SecretFetcher, fetch_secret_from_aws, read_json_secret


def resolve_credentials(settings: Settings, fetcher: SecretFetcher = fetch_secret_from_aws) -> tuple[str, str]:
    """Return (username, password): from Secrets Manager if DB_SECRET_ARN is set, else from env."""
    if settings.db_secret_arn:
        data = read_json_secret(settings.db_secret_arn, settings.aws_region, fetcher)
        return data["username"], data["password"]
    return settings.db_user, settings.db_password


def build_database_url(settings: Settings, fetcher: SecretFetcher = fetch_secret_from_aws) -> URL | str:
    """DATABASE_URL wins (used for SQLite). Otherwise build a MySQL URL from parts.

    URL.create() escapes special characters in passwords, so generated passwords are safe.
    """
    if settings.database_url:
        return settings.database_url
    if settings.db_host:
        user, password = resolve_credentials(settings, fetcher)
        return URL.create(
            "mysql+pymysql", username=user, password=password,
            host=settings.db_host, port=settings.db_port, database=settings.db_name,
            query={"charset": "utf8mb4"},
        )
    return "sqlite:///./sole_atelier.db"


def make_engine(url: URL | str, settings: Settings | None = None) -> Engine:
    settings = settings or Settings()
    if str(url).startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False})

        @event.listens_for(engine, "connect")
        def _enable_fk(dbapi_conn, _):  # SQLite ignores foreign keys unless asked
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

        return engine
    connect_args = {"ssl": {"ca": settings.db_ssl_ca}} if settings.db_ssl_ca else {}
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800, connect_args=connect_args)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
