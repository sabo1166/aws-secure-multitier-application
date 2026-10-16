"""Environment-based configuration. Nothing secret is hard-coded here."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PLACEHOLDER_SECRETS = {"", "replace-with-a-random-secret", "changeme", "secret"}


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def load_dotenv(path: Path = Path(".env")) -> None:
    """Tiny .env reader for local development. Real environment variables win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    app_env: str = "development"
    database_url: str = ""
    db_host: str = ""
    db_port: int = 3306
    db_name: str = "sole_atelier"
    db_user: str = ""
    db_password: str = ""
    db_secret_arn: str = ""
    aws_region: str = ""
    db_ssl_ca: str = ""
    session_secret: str = ""
    session_secret_arn: str = ""
    session_https_only: bool = False
    store_name: str = "SOLE ATELIER"
    max_qty_per_line: int = 5
    max_cart_lines: int = 20

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @classmethod
    def from_env(cls) -> "Settings":
        e = os.environ
        return cls(
            app_env=e.get("APP_ENV", "development").strip().lower(),
            database_url=e.get("DATABASE_URL", "").strip(),
            db_host=e.get("DB_HOST", "").strip(),
            db_port=int(e.get("DB_PORT", "3306") or 3306),
            db_name=e.get("DB_NAME", "sole_atelier").strip(),
            db_user=e.get("DB_USER", "").strip(),
            db_password=e.get("DB_PASSWORD", ""),
            db_secret_arn=e.get("DB_SECRET_ARN", "").strip(),
            aws_region=e.get("AWS_REGION", e.get("AWS_DEFAULT_REGION", "")).strip(),
            db_ssl_ca=e.get("DB_SSL_CA", "").strip(),
            session_secret=e.get("SESSION_SECRET", ""),
            session_secret_arn=e.get("SESSION_SECRET_ARN", "").strip(),
            session_https_only=_truthy(e.get("SESSION_HTTPS_ONLY")),
        )

    def validate(self) -> None:
        """Fail fast on unsafe production configuration instead of running insecurely."""
        if self.app_env not in {"development", "test", "production"}:
            raise RuntimeError("APP_ENV must be development, test or production")
        if self.is_production:
            if self.session_secret_arn and not self.session_secret:
                pass  # the secret is fetched at startup and re-validated by resolve_session_secret()
            elif self.session_secret in PLACEHOLDER_SECRETS or len(self.session_secret) < 32:
                raise RuntimeError("SESSION_SECRET must be a random value of at least 32 characters in production")
            if not (self.db_host or self.database_url):
                raise RuntimeError("Production requires DB_HOST (RDS) or DATABASE_URL; it never falls back to SQLite")
            if self.database_url.startswith("sqlite"):
                raise RuntimeError("SQLite is for local development only")


def resolve_session_secret(settings: Settings, fetcher=None) -> Settings:
    """If SESSION_SECRET_ARN is set, read {"session_secret": "..."} from Secrets Manager so that every
    instance behind the load balancer signs cookies with the same key, without the key living in
    user data or a launch template. The fetched value is validated like an environment-provided one."""
    if settings.session_secret or not settings.session_secret_arn:
        return settings
    from dataclasses import replace

    from .secrets import fetch_secret_from_aws, read_json_secret

    value = read_json_secret(settings.session_secret_arn, settings.aws_region, fetcher or fetch_secret_from_aws).get("session_secret", "")
    resolved = replace(settings, session_secret=value)
    if settings.is_production and (value in PLACEHOLDER_SECRETS or len(value) < 32):
        raise RuntimeError("The session secret read from Secrets Manager must be at least 32 characters")
    return resolved
