# Security decisions

Each control is labelled by what is actually true today:

- **Implemented and tested locally**: in the code, with an automated test or a browser check that fails if it is removed (several were confirmed by deliberately breaking them, see [testing.md](testing.md)).
- **Implemented, not tested**: in code or design but no test exercises it.
- **Planned (AWS)**: depends on infrastructure you have not built yet. Not a claim.
- **Not implemented**: stated as a limitation.

Nothing here has been reviewed by an external security professional. The role-based reviews in [project/QUALITY_REVIEW.md](project/QUALITY_REVIEW.md) are structured self-reviews.

## Application controls

| Control | Status | Where / how |
|---|---|---|
| Server recalculates prices, totals and stock; the browser only sends ids, size, quantity | Implemented and tested locally | `backend/services/cart.py`, `orders.py`; tests reject client-sent `price`/`total` fields and re-price after DB changes |
| Input validation on every write | Implemented and tested locally | Pydantic models in `backend/schemas.py`; `extra="forbid"`; size, quantity, email, postal-code patterns; control characters stripped |
| SQL injection | Mitigated and tested locally | Only SQLAlchemy expressions with bound parameters; search uses `icontains(autoescape=True)` so `%` and `_` are literal; tests send injection strings |
| XSS | Mitigated and tested locally | Jinja2 autoescape; a test submits `<script>` in an address and checks it is escaped; CSP `script-src 'self'` (no inline scripts) |
| CSRF on state-changing requests | Implemented and tested locally | Token in the signed session, required in `X-CSRF-Token` on every POST/PATCH/DELETE under `/api`; `SameSite=Lax` cookie as a second layer |
| Session cookie | Implemented; partly tested | Signed (`itsdangerous`), `HttpOnly`, `SameSite=Lax`. `Secure` is **off** while the site is HTTP-only (browsers drop Secure cookies over HTTP). Set `SESSION_HTTPS_ONLY=true` once HTTPS exists. A tampered cookie is tested to be ignored |
| Cart holds no sensitive data | Implemented | Only product id, size, quantity |
| Order confirmation visible only to the ordering session | Implemented and tested | Unguessable reference plus session check; another browser gets 404 |
| Double submit and replay | Implemented and tested | Client-generated idempotency key, unique in the database; replay returns the original order and stock is decremented once |
| Overselling | Implemented and tested | Atomic conditional `UPDATE ... WHERE stock >= qty` in one transaction; a simulated race rolls back every line |
| Safe errors | Implemented and tested | Handlers return generic messages; tests assert hostnames, usernames and exception text never appear; validation errors never echo submitted values |
| No customer data in logs | Implemented and tested | Log lines carry order id and counts only; a test checks name, email and address are absent |
| Security headers | Implemented and tested | CSP, `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, `Cache-Control: no-store` on cart, checkout, orders and API |
| No payment data | By design, tested | No card fields exist (browser smoke test), and an unexpected `card_number` field is rejected |
| Fail-fast production config | Implemented and tested | `APP_ENV=production` refuses a placeholder or short secret, SQLite, or a missing database; API docs are disabled in production |
| Secrets not in code or config | Implemented | Credentials from Secrets Manager via the instance role; `.env.example` has placeholders only; `.env` is git-ignored. The Secrets Manager call itself is tested with a fake fetcher, **not against AWS** |
| Dependencies pinned and scanned | Implemented, partly | Direct dependencies have exact versions in `requirements.txt`; transitive versions are resolved at install time (no lockfile). `pip-audit` found no known vulnerabilities on 2026-10-15 (E-021); it is a point-in-time scan and must be re-run before publishing |

## Database controls

| Control | Status |
|---|---|
| Dedicated `sole_app` user with `SELECT, INSERT, UPDATE, DELETE` only, no DDL | **Planned (AWS)**; procedure in [rds-setup-guide.md](rds-setup-guide.md) |
| Admin account used only for schema setup, password typed at a prompt, never stored | Implemented in `backend/init_db.py` (prompt tested only for the non-admin path); live use planned |
| Not publicly accessible, private subnets, no internet route | **Planned (AWS)**: E-006, E-007 |
| Inbound 3306 only from `app-sg` | **Planned (AWS)**: E-005 |
| Encryption at rest | **Planned (AWS)** |
| TLS in transit (`DB_SSL_CA`, `require_secure_transport`, `REQUIRE SSL`) | TLS option wiring implemented (engine creation tested without connecting); enforcement **planned (AWS)** |
| Constraints (non-negative stock and money, positive quantity), foreign keys | Implemented and tested on SQLite; MySQL behaviour not yet observed |

## AWS controls (all planned)

| Control | Evidence it will need |
|---|---|
| Public/private separation by route table | E-003, E-004 |
| Security-group chain, restricted egress | E-005, then behaviour in E-007, E-010 |
| No SSH, Session Manager, IMDSv2 only, no public IPs | E-010, E-011 |
| Instance role limited to two secrets | E-011 |
| Budget alert, root MFA, non-root daily identity | E-001, E-002 |

## Known limitations (state these publicly)

1. **HTTP only** between the browser and the ALB (D-009). Anyone on the path can read or alter traffic and the session cookie is not marked `Secure`.
2. **No rate limiting, bot protection or WAF.** A script can fill the cart, hammer search, or place many demo orders and deplete demo stock.
3. **Demo stock reservation never expires.** Orders are "demo pending" forever; there is no cancellation or restock flow.
4. **No authentication or customer accounts.** Order lookup relies on the browser session.
5. **Personal data:** a demo order stores name, email and address with no retention period, deletion process or consent flow. A real shop would need a data-protection design.
6. **No audit logging, alerting or log shipping.**
7. **No continuous dependency scanning** (one manual `pip-audit` run, E-021) and no external penetration test.
8. **Secrets are not rotated** (the RDS master secret rotates by default; the app user and session key do not).
9. **The app database user is still broad inside its database** (full DML on all tables).
10. **Single NAT and single-AZ database** are availability weaknesses, not security ones, but they affect incident impact.

## What to say in an interview

Be precise: "The application validates input, uses parameterised queries, protects state-changing calls with CSRF tokens, and I tested these locally including by breaking them on purpose. The AWS controls (private database, security-group chaining, no SSH) are designed and documented; I will only claim them once I have my own screenshots and tests." See [interview-qa.md](interview-qa.md).
