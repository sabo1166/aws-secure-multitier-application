# Backend

The Python side of SOLE ATELIER: a FastAPI application that serves the HTML pages, the JSON API and the health checks, and talks to the database. It also renders the [frontend](../frontend/README.md) templates (server-side rendering), so there is one deployable process.

## Run it

From the repository root, with the virtual environment active:

```powershell
uvicorn backend.main:create_app --factory --reload     # http://127.0.0.1:8000
```

It is an application factory (no module-level `app`), so importing it has no side effects. Without a `.env` it uses SQLite and a development-only session key. Full setup: [../docs/local-setup.md](../docs/local-setup.md). Tests: `pytest` from the root.

## Modules

| Path | Responsibility |
|---|---|
| `main.py` | Application factory: middleware, security headers, error handlers, mounts `frontend/static`, loads `frontend/templates` |
| `config.py` | Environment-based settings; refuses weak secrets, SQLite or a missing database in production |
| `database.py` | Engine and sessions: SQLite locally, MySQL (RDS) from `DB_HOST` plus credentials |
| `secrets.py` | Reads Secrets Manager secrets with the instance role (only used when an ARN is set) |
| `models.py` | SQLAlchemy tables: `products`, `product_sizes`, `orders`, `order_items` |
| `schemas.py` | Pydantic validation for every write |
| `security.py` | CSRF token check and the Content-Security-Policy |
| `deps.py` | Request helpers: database session, template rendering |
| `routes/` | `pages.py` (HTML), `products.py` and `cart.py` (JSON API), `misc.py` (orders, newsletter demo, health) |
| `services/` | `catalog.py` (queries), `cart.py` (pricing and limits), `orders.py` (atomic stock reservation, idempotency) |
| `seed.py` | The six fictional demo products |
| `init_db.py` | Creates missing tables only; `--admin-user` for the one-off schema step on RDS |

## Endpoints

| Method and path | Purpose |
|---|---|
| `GET /`, `/shop`, `/products/{slug}`, `/collections`, `/journal`, `/about`, `/policies` | Pages |
| `GET /cart`, `/checkout`, `/orders/{public_id}` | Bag, demo checkout, confirmation (visible only to the ordering session) |
| `GET /api/products`, `/api/products/{slug}` | Catalogue |
| `GET /api/cart`; `POST /api/cart/items`; `PATCH` and `DELETE /api/cart/items/{item_id}` | Bag (CSRF token required on writes) |
| `POST /api/orders` | Demo order: validated, stock reserved atomically, idempotent |
| `POST /api/newsletter` | Demo only: validates, stores nothing |
| `GET /health`, `/health/ready` | Liveness (load balancer) and readiness (checks the database) |

## Configuration

All by environment variables; see [../.env.example](../.env.example). Database selection and secrets handling for AWS: [../docs/rds-setup-guide.md](../docs/rds-setup-guide.md). Security controls and their status: [../docs/security.md](../docs/security.md).

## Dependencies

`requirements.txt` (runtime, pinned) is what an instance installs. `requirements-dev.txt` adds `pytest` and `httpx` for the tests and is deliberately separate so test tooling is not installed on the servers.
