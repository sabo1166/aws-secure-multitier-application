"""Explicit, non-destructive schema initialisation.

    python -m backend.init_db                       # create missing tables (uses the app's own DB settings)
    python -m backend.init_db --seed                # ...and insert the demo catalogue if the table is empty
    python -m backend.init_db --admin-user admin    # connect as an admin account (prompts for the password)

Why an admin option: the application's database user only has SELECT/INSERT/UPDATE/DELETE. Creating
tables needs more, so you run this once with an admin account, typed at a prompt (never stored), and
the app itself keeps running with the low-privilege account. create_all() only creates tables that do
not exist; it never alters or drops anything.
"""
from __future__ import annotations

import argparse
import getpass

from sqlalchemy.engine import URL

from .config import Settings, load_dotenv
from .database import build_database_url, make_engine, make_session_factory
from .models import Base
from .seed import seed_if_empty


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", action="store_true", help="insert the demo catalogue if no products exist")
    parser.add_argument("--admin-user", help="connect with this MySQL account instead of the app user")
    args = parser.parse_args(argv)

    load_dotenv()
    settings = Settings.from_env()
    if args.admin_user:
        if not settings.db_host:
            parser.error("--admin-user needs DB_HOST (a MySQL deployment)")
        password = getpass.getpass(f"Password for {args.admin_user}@{settings.db_host}: ")
        url: URL | str = URL.create(
            "mysql+pymysql", username=args.admin_user, password=password, host=settings.db_host,
            port=settings.db_port, database=settings.db_name, query={"charset": "utf8mb4"},
        )
    else:
        url = build_database_url(settings)

    engine = make_engine(url, settings)
    Base.metadata.create_all(engine)
    print("Schema is up to date (missing tables created, nothing altered or dropped).")
    if args.seed:
        with make_session_factory(engine)() as db:
            added = seed_if_empty(db)
        print(f"Seeded {added} demonstration products." if added else "Products already exist; nothing seeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
