# Local setup (no AWS needed)

Runs the whole storefront on your computer with SQLite. Nothing here touches AWS or costs money. Commands are for Windows PowerShell; on macOS or Linux use `source .venv/bin/activate` instead of `.venv\Scripts\Activate.ps1`.

## 1. Prerequisites

- Python 3.11 or newer should work; **only Python 3.13 has been tested**.
- Node.js 22 or newer (tested on 24; the helper scripts use the built-in `WebSocket` and `fetch`), only for the documentation checker and the browser smoke test (optional).
- Microsoft Edge or Google Chrome, only for the browser smoke test (optional).

## 2. Install

```powershell
cd aws-secure-multitier-application
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

`boto3` in `requirements.txt` is only imported when `DB_SECRET_ARN` or `SESSION_SECRET_ARN` is set, so it is unused locally.

## 3. Configure

```powershell
copy .env.example .env
```

The defaults work: SQLite file `sole_atelier.db` in the project folder and a development-only session key. For anything beyond your own machine generate a key:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

and put it in `.env` as `SESSION_SECRET`. `.env` and `*.db` are git-ignored.

## 4. Run

```powershell
uvicorn backend.main:create_app --factory --reload
```

Open <http://127.0.0.1:8000>. In development with SQLite the app creates the tables and inserts the six fictional demo products on first start (only when the table is empty). Interactive API documentation is at `/docs` in development and disabled when `APP_ENV=production`.

Health checks: `http://127.0.0.1:8000/health` (liveness) and `/health/ready` (checks the database).

To reset the demo data, stop the server and delete `sole_atelier.db`.

## 5. Try the main journeys

Browse, search "noir", sort by price, open a product, choose a size, add to bag, change quantity in the bag, go to the demo checkout, submit a deliberately invalid email (an inline error appears), then submit valid details. You get a "Demo order recorded" page. No payment is taken.

## 6. Test

```powershell
pytest
node tools\check-docs.mjs
```

For the real-browser smoke test, start the app on a **throwaway** database (it places a demo order), then:

```powershell
node tools\browser-smoke.mjs http://127.0.0.1:8000 screenshots-out
```

Details of what is tested: [testing.md](testing.md).

## 7. Switch to MySQL locally (optional)

If you have a MySQL server, set `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` in `.env` and leave `DATABASE_URL` empty, then run `python -m backend.init_db --seed`. Over TLS (the deployment path) PyMySQL needs nothing extra. A local MySQL **without** TLS using MySQL 8's default `caching_sha2_password` login needs the `cryptography` package (`pip install cryptography`); PyMySQL raises an error naming it otherwise (checked in PyMySQL's source). This path is exercised against RDS only after you build it (see [rds-setup-guide.md](rds-setup-guide.md)); the MySQL URL building is unit tested, the live MySQL connection is **not tested yet**.

## Common problems

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: app` | Running from the wrong folder | `cd` into the project root |
| Cart empties after restart or in a new browser | Cart is a browser cookie (by design) | Expected |
| Cart empties after you change `SESSION_SECRET` | Old cookies no longer verify | Expected |
| Port already in use | Another server on 8000 | `--port 8010` |
| `RuntimeError: SESSION_SECRET must be...` | `APP_ENV=production` with a weak secret | Generate a real one |
