# Testing

What was run, what passed, what was **not** run. Every number below comes from a recorded run in `evidence/redacted/` (see the register rows E-015 to E-020). Run them yourself (CP8, E-019) before you quote them as yours.

## Summary of runs (executed by Claude on 2026-10-15, local machine, Python 3.13, SQLite)

| Check | Command | Result | Evidence |
|---|---|---|---|
| Automated tests | `pytest` | **91 passed**, 0 failed | [E-015-pytest-output.txt](../evidence/redacted/E-015-pytest-output.txt) |
| Do the tests notice broken code? | `python tools/mutation_check.py` | **6 of 6 deliberate bugs caught**; files restored; 91 passed afterwards | [E-015-mutation-checks.txt](../evidence/redacted/E-015-mutation-checks.txt) |
| Real-browser UI test | `node tools/browser-smoke.mjs http://127.0.0.1:PORT <dir>` | **35 of 35 checks passed** | [E-016-browser-smoke-output.txt](../evidence/redacted/E-016-browser-smoke-output.txt) |
| Local health endpoints | `curl` | `/health` ok, `/health/ready` ok, unknown product 404 | [E-018-local-health.txt](../evidence/redacted/E-018-local-health.txt) |
| Colour contrast | `python tools/check_contrast.py` | **12 of 12** colour pairs meet WCAG AA | [E-020-contrast.txt](../evidence/redacted/E-020-contrast.txt) |
| Documentation checks | `node tools/check-docs.mjs` | see [project/QUALITY_REVIEW.md](project/QUALITY_REVIEW.md) for the final run | n/a |

## Automated test suite (91 tests, `tests/`)

Each test runs on its own temporary SQLite file. No test can touch a real or RDS database: the engine is always built from a path under pytest's temporary directory.

| File | Tests | Covers |
|---|---|---|
| `test_pages_and_catalog.py` | 32 | Home page content and nav; every nav link resolves; shop lists only active products; search (case-insensitive; `%`, `_`, SQL and HTML strings treated as literals; empty state); category and "new" filters; sorting by price and newest; invalid sort/category handled; product page shows disabled sold-out sizes and "Sold out"; unknown and inactive products 404 without internals; static assets; security headers; session cookie flags; no inline script/style in templates; JSON API list, detail, filters, errors |
| `test_cart.py` | 14 | Add, accumulate to the stock limit, update, remove; CSRF required and per-session; invalid quantity, size and extra fields rejected; sold-out and unknown sizes; reprice after database change; items flagged when stock or product disappears; badge count; forged cookie ignored |
| `test_orders.py` | 25 | Successful order totals, stock decrement and price/name snapshots; confirmation visible only to the ordering session; idempotent replay; empty cart; ten invalid-field cases; missing and extra fields (no client prices, no card data); errors never echo submitted values; CSRF; stock changing between bag and order; rollback of all lines on a simulated race; logs contain no customer data; control characters cleaned; HTML escaped on confirmation; two buyers, one pair |
| `test_platform.py` | 20 | Liveness and readiness; database outage returns 503 with no hostname/user/exception text; API error shape; unexpected errors are generic; 405 and JSON 404; orders persist across an app restart; production config validation; API docs hidden in production; MySQL URL built from parts with password escaping and masked in logs; credentials and session secret read from a fake Secrets Manager; MySQL engine created lazily with TLS CA; SQLite foreign keys; database constraints reject bad data; honest newsletter demo; seed inserts once; `init_db` is non-destructive |

## Mutation check

`tools/mutation_check.py` applies six deliberate bugs, one at a time, and requires at least one test to fail for each: stock guard removed, CSRF check disabled, quantity ignored when pricing, price snapshot replaced by zero, inactive products shown, order confirmation visible to anyone. All six were caught. **A weakness noticed along the way:** the stock-guard bug is caught by a single test class, so the oversell path has thinner coverage than the others.

## Browser test (what the 35 checks cover)

**CSS, JavaScript, fonts and images load from `frontend/static` on four pages** (added when the frontend was split from the backend; the unit tests cannot see this); product page requires a size and updates stock text; quantity stepper; add to bag updates the live count; cart quantity change and server-computed totals; demo banner and **no card fields** on checkout; empty and invalid checkout shown as inline errors; a valid order redirects to a confirmation that says no payment was processed; sort select; empty search state; structural accessibility on eight pages (one h1, `lang`, alt text, labelled controls, `<main>`); first Tab focuses the skip link and twelve Tabs reach twelve distinct visible controls; mobile menu hidden then opened with `aria-expanded`; no horizontal overflow at 390 px on home, shop and product pages.

It places a real demo order, so it needs a fresh database each run (it checks and refuses otherwise).

## What is NOT tested (be explicit when you present this)

- **MySQL / RDS.** All database tests run on SQLite. Constraint and transaction behaviour on MySQL is unobserved.
- **Real concurrency.** The oversell tests are sequential or simulate the race. No parallel load test was run.
- **Other browsers and real devices.** One browser (Edge) with device-size emulation.
- **Screen readers and a full accessibility audit.** Only the structural, keyboard and contrast checks above.
- **Visual regression, performance and load.**
- **Dependency vulnerability scanning and penetration testing.**
- **Anything on AWS.** No resource exists yet.

## AWS validation (to run in CP6; every test is PENDING)

Each test needs a recorded result before the matching register row can be VERIFIED.

| Test | Procedure | Expected | Evidence |
|---|---|---|---|
| Site through the ALB | Open the ALB DNS name, browse, add to bag, place a demo order | Confirmation page shown | E-009, E-008 |
| Order reached the database | Query `orders` and `order_items` from an instance as `sole_app` | Row matches the confirmation | E-008 |
| App-to-database health | `curl http://127.0.0.1:8080/health/ready` on an instance | database ok | E-008 |
| **Database not reachable from the internet** | From outside the VPC, connect to the RDS endpoint on 3306 | Times out. Optionally run VPC Reachability Analyzer (check its pricing) from the internet gateway to the DB network interface and record "not reachable" | E-007 |
| **Instances not directly reachable** | Confirm no public IPv4, then try to reach port 8080 on the private address from outside | Fails | E-010 |
| No SSH ingress | Review `mt-app-sg` rules | No rule for 22 | E-005, E-011 |
| Session Manager | Open a shell on an instance | Session opens | E-011 |
| Least-privilege DB user | As `sole_app`, try `CREATE TABLE` and `DROP TABLE` | Both denied | E-008 follow-up |
| Self-healing | Run a request loop, terminate one instance in the console | Requests keep succeeding (brief errors are recorded honestly); ASG launches a replacement | E-012 |
| **Not tested on purpose** | AZ-level failure | Expect an outage (NAT and RDS in AZ a); record it as a known limitation, do not claim resilience | n/a |

Do not claim database security from a healthy target group, or reachability from a configuration screenshot.

## Reproduce locally

See [local-setup.md](local-setup.md): `pytest`, then `node tools/check-docs.mjs`; for the browser test start the app on a throwaway SQLite file first.
