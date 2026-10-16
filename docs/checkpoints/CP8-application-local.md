# CP8 Application, local

Status: **IMPLEMENTED**. Evidence: E-015 to E-023 (see [../project/EVIDENCE_REGISTER.md](../project/EVIDENCE_REGISTER.md)). No AWS account or cost involved.

The application was built and tested by Claude in the working session; E-015 to E-018 and E-020 to E-023 record those runs. The checkpoint is not VERIFIED until **you** run it yourself and understand it (E-019).

## 1. Objective and why it matters

Prove the application works before any AWS cost exists, so that later AWS failures can be attributed to infrastructure and not to the code. It also gives you something concrete to explain: what the tiers carry, which checks the server enforces, and what the tests prove.

## 2. Console navigation

None. This checkpoint is local: a terminal, a browser, and [../local-setup.md](../local-setup.md).

## 3. Configuration values and rationale

| Setting | Value | Rationale |
|---|---|---|
| `APP_ENV` | `development` | Allows SQLite and auto-creating tables for convenience |
| `DATABASE_URL` | `sqlite:///./sole_atelier.db` | No database server needed |
| `SESSION_SECRET` | any random string locally | Signs the cart cookie; production requires a strong value (the app refuses to start otherwise) |
| Python | 3.13 (the only tested version) | Matches what the tests ran on |

## 4. Security and cost implications

- Cost: none.
- Security: `.env` and `*.db` are git-ignored; `.env.example` holds placeholders only. Do not type real personal data into the demo checkout; it is stored in the local database file.

## 5. Expected result

`pytest` reports all tests passing; the site runs at <http://127.0.0.1:8000>; browsing, cart and demo checkout work; the confirmation page says no payment was processed.

## 6. Verification procedure

1. `pytest` and record the summary line.
2. Start the app and walk the journeys in [../local-setup.md](../local-setup.md) section 5.
3. `curl http://127.0.0.1:8000/health` and `/health/ready`.
4. Break something on purpose and confirm a test fails (for example, comment out the stock guard in `backend/services/orders.py` and run `pytest`), then restore it. Passing tests only mean something if they can fail.
5. **Predict first:** before step 4, write down which test you expect to fail and why.

## 7. Evidence to capture

Save your own, redacted, under `screenshots/06-application/` and `evidence/redacted/`:

- `01-homepage-desktop.png`, `02-product-detail-desktop.png`, `03-shop-desktop.png`, `04-cart-desktop.png`, `05-checkout-validation-desktop.png`, `06-order-confirmation-desktop.png`, `07-mobile-menu.png`
- `E-019-my-pytest-run.txt` (your terminal output)
- `E-019-my-health-check.txt`

The first seven names already exist as Claude-captured screenshots from the local build ([../../screenshots/README.md](../../screenshots/README.md) explains the labelling). Replace them with your own when you re-run; the register shows which are whose.

What these prove: the application behaves as shown on SQLite on one machine. They do not prove anything about MySQL, AWS, the load balancer, or behaviour under real concurrency.

## 8. Common failures and diagnostics

| Symptom | Likely cause | Check |
|---|---|---|
| `pytest` cannot import `app` | Wrong directory or venv not active | Run from the project root with `.venv` active |
| Page shows no styling | Static files not found | The app serves `/static` from `frontend/static`; check the working directory |
| Cart seems empty | Cookies blocked or `SESSION_SECRET` changed | Browser cookie settings |
| Browser smoke test says database is not fresh | Earlier run sold out the stock it uses | Restart on a new SQLite file |

## 9. Gate to move forward

You have re-run the tests and the app yourself (E-019), can explain in your own words how the server prevents a tampered price and an oversell, and can say what the tests do **not** cover. Then start CP0.

## Interview prep

How does the cart avoid trusting the browser? What happens if two buyers want the last pair? Why does `/health` not check the database? What would you have to add before real payments?
