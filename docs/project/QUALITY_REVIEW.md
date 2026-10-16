# QUALITY_REVIEW

Findings from nine review roles, the fixes applied, the re-checks run, the release gates, and the release decision. Review date: 2026-10-15.

**These are structured self-reviews by an AI assistant playing nine roles. No human expert, employer, recruiter or external reviewer has examined this project.** Do not describe them as such.

Finding status: FIXED (changed and re-checked), OPEN (should be fixed), ACCEPTED (known limitation, must be disclosed), WATCH (cannot be judged until more evidence exists).

## Release decision

# READY WITH DOCUMENTED LIMITATIONS

Scope of that statement: the repository can be published as an **honest, in-progress portfolio project**: a locally tested application plus a documented, unbuilt AWS design. It must be presented that way.

What it does **not** yet do: demonstrate hands-on AWS skill. No AWS resource has been created, so the core purpose of the project (networking, security groups, RDS, load balancing, troubleshooting, in your own words and screenshots) is unproven. Publishing now is safe and truthful; publishing it as an AWS showcase would not be. The decision changes only with real AWS evidence.

Blocking conditions already checked: no secrets or private files in the publishable tree (E-023, secret scan), no automation or infrastructure-as-code files, no claim of deployment or production readiness, documentation checker passing (see "Final run" below).

## Review cycle

| Pass | What | Result |
|---|---|---|
| 1 | Planning files and checkers (earlier session) | Two inconsistencies fixed (NAT checkpoint timing, evidence mapping); checker verified with seeded errors |
| 2 | Application, tests, UI, docs by role (below) | 30+ findings, listed per role; fixes applied; tests, browser run, visual render and documentation checks re-run after fixes |
| 3 | Independent challenge (Role I) | Searched for contradictions; found three further problems, all fixed; see Role I |
| 4 | Repository reorganisation (GitHub layout) | `architecture.png` audited against the docs and corrected; project-management files moved into `docs/project/`; docs and screenshot folders renamed; 58 links rewritten by script and re-verified; see "Reorganisation review" |
| 5 | Frontend/backend split | Application inspected (FastAPI backend plus server-rendered Jinja2 frontend, no JS app); `app/` split into `backend/` and `frontend/`; imports, paths, tests, tools and docs updated; see "Frontend and backend split review" |
| Final | All checks re-run on the final tree | See "Final run" |

## Role A: Senior software engineer

| ID | Finding | Status |
|---|---|---|
| A-1 | Module-level `app = create_app()` created a database on import | FIXED (factory) |
| A-2 | Dead code: unused `session_dependency`, `Settings.extra` | FIXED (removed) |
| A-3 | Raw library text in validation messages | FIXED (friendly messages, never echo input) |
| A-4 | `routes/misc.py` mixes orders, newsletter and health | ACCEPTED (small project; rename if it grows) |
| A-5 | Very new library versions pinned (SQLAlchemy 2.1, Starlette 1.8); the test client prints a deprecation warning about `httpx` | WATCH (re-test on upgrade) |
| A-6 | `created_at` is timezone-aware in Python but stored as plain `DATETIME` on MySQL (UTC values) | WATCH (observe on MySQL) |

## Role B: Senior AWS solutions architect

| ID | Finding | Status |
|---|---|---|
| B-1 | NAT timing said CP5 in one file, CP4 elsewhere | FIXED |
| B-2 | RDS guide's `init_db` command would fail for the Session Manager user (env file is `root:soleapp` 640) | FIXED (runs as `soleapp` after loading the env file); still untested |
| B-3 | The early design had the app use the DB admin account | FIXED (dedicated `sole_app` user, D-008) |
| B-4 | `dnf` package names, Python version on Amazon Linux 2023, and the user-data script are untested; delivery depends on a public Git repo and PyPI via NAT | OPEN (first real build will answer; D-014) |
| B-5 | First boot ordering: the app starts before the DB user, secrets and tables exist | ACCEPTED (documented in the deployment guide Part C) |
| B-6 | MySQL behaviour (transaction isolation with the atomic update, constraint errors) not observed | WATCH (E-008 and a test on a real MySQL) |
| B-7 | Single NAT, single-AZ RDS, HTTP only | ACCEPTED (D-006, D-007, D-009; AZ-a failure likely means an outage) |
| B-8 | Session Manager and Secrets Manager reachable only through NAT (no VPC endpoints) | ACCEPTED (D-006) |
| B-9 | Documents cross-checked for agreement (CIDRs, SG rules, ports, names, checkpoint numbers, evidence IDs) | Checked by `check-docs.mjs` and manual read; no remaining disagreement found |

## Role C: Application security engineer

| ID | Finding | Status |
|---|---|---|
| C-1 | Claim "dependencies pinned" was false: `boto3` was unpinned | FIXED (pinned); transitive packages are not locked (ACCEPTED, no lockfile) |
| C-2 | `pip-audit`: no known vulnerabilities on 2026-10-15 | Recorded as E-021; WATCH (point-in-time) |
| C-3 | HTTP only, no rate limiting or WAF, no secret rotation for the app user | ACCEPTED (listed in docs/security.md) |
| C-4 | A replayed idempotency key returns the first order to whoever sends it, even with different data | ACCEPTED (key is 128-bit random and server-issued; standard behaviour; documented here) |
| C-5 | Demo orders store a name, email and address with no retention or deletion process | ACCEPTED (disclosed on the policies page and in docs) |
| C-6 | Screenshots can leak account IDs or emails and no tool scans images | OPEN (manual redaction checklist; reviewer must look at each image) |
| C-7 | Cookie flags verified (`HttpOnly`, `SameSite=Lax`; `Secure` when configured) and now under test; no inline script or style, guarded by a test | FIXED |
| C-8 | No security headers beyond those set (no HSTS, because there is no HTTPS) | ACCEPTED |

## Role D: UI/UX and product designer

| ID | Finding | Status |
|---|---|---|
| D-1 | Hero shoe overlapped the buttons and was clipped | FIXED |
| D-2 | Portrait cards left the shoe small in empty space | FIXED (square art and cards) |
| D-3 | Mobile header wrapped; hero shoe cropped at 390 px; tile labels crowded; summary divider had a gap | FIXED |
| D-4 | Images are illustrations, not photography | ACCEPTED (D-018; replacement steps in docs/assets.md) |
| D-5 | Verified: 12 of 12 colour pairs meet AA; first Tab hits the skip link; 12 Tabs reach 12 visible controls; no horizontal overflow at 390 px on three pages | Evidence E-016, E-020 |
| D-6 | Not tested: screen readers, real devices, other browsers, 200% zoom, high-contrast mode | OPEN |
| D-7 | The product art is stylised; a real brand would need photography to convey material and finish | ACCEPTED |

## Role E: QA and reliability engineer

| ID | Finding | Status |
|---|---|---|
| E-1 | A test that could not fail (`... or True`) | FIXED (removed) |
| E-2 | A test asserted the wrong thing (`/cart` during an outage) | FIXED |
| E-3 | The race test counted internal `execute` calls and was fragile | FIXED (counts UPDATE statements) |
| E-4 | The browser test could not be re-run on the same database | FIXED (pre-flight check refuses and explains) |
| E-5 | Mutation check: 6 of 6 bugs caught; the stock guard is caught by only one test class | WATCH (thin coverage) |
| E-6 | No parallel load test; no MySQL test | OPEN (state this in every claim) |
| E-7 | Tests only on Python 3.13 | OPEN |

## Role F: GitHub repository reviewer

| ID | Finding | Status |
|---|---|---|
| F-1 | `.gitignore` verified by a dry-run with planted `.env`, `.db`, `.pem` and raw evidence (E-023) | Verified |
| F-2 | Line-ending warnings on Windows | FIXED (`.gitattributes`) |
| F-3 | No licence chosen | OPEN (your decision) |
| F-4 | Git repository not initialised (by design; nothing committed or published) | n/a |
| F-5 | README states AI assistance and that the author must edit that section | OPEN (you must edit it truthfully before publishing) |
| F-6 | Clean-room install works from `requirements-dev.txt` (E-022) | Verified |
| F-7 | Structure follows the requested layout where it fits. Deliberate differences: the Python package is `backend/` and the server-rendered UI is `frontend/` (no separate JS app), `.github/` is absent (no CI/CD), `scripts/` and `tools/` are both kept (art generator versus local QA helpers; evidence files record `tools/` command paths), `evidence/` is kept for the private `raw/` folder and redacted text outputs, and `screenshots/05-database` is kept because the architecture has a database tier | ACCEPTED |
| F-8 | Name SOLE ATELIER not checked for trademark conflicts | OPEN |

## Role G: Technical recruiter and hiring manager

- **Strengths an employer can check:** a working application with tests that fail when it is broken; explicit separation of designed, built, tested and verified; a decision log with trade-offs; an evidence register that says what each screenshot does not prove; honest limitations.
- **Weaknesses:** no AWS evidence yet, so the main skill is not shown; the frontend and code were produced with an AI assistant (the README says so, and you must be able to explain every part, see [../interview-qa.md](../interview-qa.md)); one author, no review by a human.
- **Do not claim:** deployed, highly available, production ready, secure without qualification, tested on RDS.
- **What improves it fastest:** CP0 to CP2 with your own screenshots and your own explanations, then the negative tests (E-007, E-010).

## Role H: LinkedIn content strategist

- [../linkedin-ideas.md](../linkedin-ideas.md) gates every idea behind real evidence and labels it (local, deployed, verified). Five ideas are available now and none claims AWS work.
- Open: nothing has been drafted into post text; do that yourself from your own evidence.

## Role I: Independent final reviewer (challenge pass)

I tried to find what the other roles missed. Method: grep for contradictory numbers across all files (91, 35, 6, 12 agree everywhere); grep for unsupported claim words (found only quoted interview questions and "not claimed" statements); re-read the notebook and case study against the register; render every page and read it.

| ID | Finding | Status |
|---|---|---|
| I-1 | The one-page summary tagged CP8 "Verified" while PROJECT_STATUS says IMPLEMENTED | FIXED (tag now "Local") |
| I-2 | The full architecture diagram was unreadably small on A4 pages | FIXED (separate compact diagram, text readable) |
| I-3 | "Dependencies pinned" overclaimed | FIXED (see C-1) |
| I-4 | Rows E-015 to E-018 and E-020 to E-023 are VERIFIED but were produced by Claude, not you | ACCEPTED with labelling: stated in the register, evidence README and CP8; E-019 (your run) stays PLANNED |
| I-5 | Several screenshot-checklist entries and AWS commands are written from memory of the Console | OPEN (menu paths unverified, same as pass 1) |
| I-6 | Could the 91-test result be a tautology? | Checked: mutation tool breaks six behaviours and each is caught |
| I-7 | Unresolved: whether `GET /health` going through the session middleware could set cookies on health checks | Checked: it does not call the renderer, so no cookie is set |

## Reorganisation review (pass 4)

| ID | Finding | Status |
|---|---|---|
| R-1 | `architecture.png` said the instance role reads "one secret" (it reads two: DB credentials and the session key) | FIXED in the SVG source and re-rendered |
| R-2 | Diagram still said "size 2" for the Auto Scaling group; D-010 is one instance while debugging, then two | FIXED |
| R-3 | Diagram footer pointed at the renamed `docs/architecture-overview.md` | FIXED |
| R-4 | My first label edits made the Secrets Manager text overflow its box and the Auto Scaling label spill out of its subnet | FIXED (found by viewing the render; shortened and split) |
| R-5 | `screenshots/01-architecture/00-target-design-diagram.png` was a byte-identical copy of the root `architecture.png` (same MD5) | FIXED (copy removed so the two cannot drift; the README points at the root file) |
| R-6 | After moving files, link targets were right but link text still showed the old paths (for example `../DECISIONS.md` pointing at `project/DECISIONS.md`) | FIXED (43 labels corrected) |
| R-7 | Plain-text path mentions the link checker cannot see (CLAUDE.md, README layout, register evidence paths, visual documents, guides) | FIXED (swept with a grep for every old name; the only remaining old path is inside the recorded E-016 command, left unchanged with an explanatory note appended because evidence records must not be rewritten) |
| R-8 | Screenshot categories: your target had no database folder, but RDS is a real tier | ACCEPTED (kept `05-database`; application is `06`, validation `07`) |
| R-9 | Checker did not enforce a single evidence register, required files, or the new locations | FIXED (new checks, each verified by planting a violation) |

Checks after the move: link and image validation (191 links), 91 tests, three visual documents re-rendered with no broken images, clean-room install plus checker in a fresh copy (E-022), Git dry-run on the new layout (E-023), architecture diagram viewed after each edit.

## Frontend and backend split review (pass 5)

| ID | Finding | Status |
|---|---|---|
| S-1 | Can they be separated safely? FastAPI locates the frontend through three lines in `main.py`, and backend imports are relative, so yes. No separate JavaScript frontend exists, so none was invented | Decision recorded: frontend stays server-rendered (D-017) |
| S-2 | The module docstring in `main.py` said `uvicorn app.main:app`, a command that had not worked since the factory change | FIXED (now `uvicorn backend.main:create_app --factory`) |
| S-3 | After the move the unit tests could not detect broken CSS, font, JS or image paths | FIXED (four static-asset checks added to the browser test; 35 of 35 pass) |
| S-4 | Image directory renamed `img` to `images`, so stored product image paths changed (`/static/images/...`) | ACCEPTED: only affects old local SQLite files (delete them); no production database exists |
| S-5 | Deployment guide cloned the repository into `/opt/sole-atelier/app`, which now reads like the old package name | FIXED (clone directory is `/opt/sole-atelier/repo`; still an untested draft) |
| S-6 | `requirements-dev.txt` could be merged into `requirements.txt` | ACCEPTED as is: it adds `pytest` and `httpx`; merging would install test tooling on the servers |
| S-7 | Evidence files recorded under the old layout | Re-run and replaced (E-015, E-016, E-018, E-020, E-022, E-023) |

## Release gates

| Gate | Result | Basis |
|---|---|---|
| 1 Functionality (local journeys) | PASS | 91 tests, 35 browser checks; browse, detail, size, bag, validation, demo order |
| 2 Engineering quality | PASS with notes | Validated input, safe DB access, tests that catch regressions; gaps A-5, A-6, E-5 to E-7 |
| 3 Security | PARTIAL | App-level controls tested; AWS-level controls (private DB, SG chain, no SSH) are planned only; HTTP only; limitations disclosed |
| 4 User experience | PASS with notes | Real rendered desktop and mobile emulation reviewed, keyboard and contrast checked; no real-device or screen-reader testing |
| 5 AWS readiness | PARTIAL | Guides agree with each other and with the code; user data, `init_db` command and AL2023 packages untested; nothing deployed |
| 6 GitHub readiness | PASS with open decisions | README, `.gitignore` verified, no secrets, no automation files; licence, authorship text and trademark open |
| 7 Recruiter credibility | PASS for honesty, WEAK for evidence | Clear status; no AWS evidence yet |
| 8 Release decision | **READY WITH DOCUMENTED LIMITATIONS** | See top of this file |

## Requirement traceability

| Requirement | Implementation | Verification performed | Result | Remaining limitation |
|---|---|---|---|---|
| Premium responsive storefront | `frontend/templates`, `frontend/static/css/site.css`, illustrated art | Edge at 1440 and 390 px, overflow and keyboard checks, contrast computation, visual review | Pass | Illustrations not photos; no real devices or screen readers |
| Catalogue, search, filter, sort, detail | `routes/pages.py`, `services/catalog.py` | Unit and browser tests | Pass | SQLite only |
| Cart with server-side pricing | `services/cart.py`, `routes/cart.py` | Tests incl. forged cookie, repricing | Pass | Per-browser cookie cart |
| Demo checkout, no payments | `services/orders.py`, `routes/misc.py` | Tests and browser run; no card fields | Pass | No expiry of reservations |
| FastAPI backend, validation, safe errors | `backend/` | Tests incl. no-leak assertions | Pass | No rate limiting |
| SQLite local, RDS MySQL by environment | `config.py`, `database.py`, `secrets.py` | URL building, TLS option, fake Secrets Manager | Partly | **No live MySQL or RDS test** |
| Complete RDS guide | `docs/rds-setup-guide.md` | Facts checked against AWS docs 2026-10-15; cross-read against other docs | Written | Commands untested on AWS |
| Architecture and deployment docs | `docs/architecture.md`, `deployment-guide.md` | Cross-checked; checker | Written | Nothing deployed |
| Tests | `tests/` | Run; mutation check; clean-room install | 91 pass | No MySQL, load or AWS tests |
| Evidence and checkpoint workflow preserved | register, status, runbooks, `tools/check-docs.mjs` | Checker with seeded violations | Pass | Menu paths unverified |
| Three visual documents | `docs/visual/` | Rendered, mechanically inspected, read | Pass | Content mirrors a project with no AWS evidence |
| No automation, no deployment, no cost | n/a | Checker scans for automation files; no AWS call made | Pass | n/a |

## Checks run and not run

**Run (all on 2026-10-15, local machine):** `pytest` (91), mutation tool (6 of 6), real-browser test (35 of 35), contrast (12 of 12), `pip-audit`, clean-room install, Git ignore dry-run, `node tools/check-docs.mjs` including a seeded-violation test (pass 1), visual render inspection of three documents, AWS facts verified against AWS documentation (subnet-group AZ rule, MySQL versions, RDS CA bundle, managed master password).

**Not run:** anything on AWS; MySQL; parallel load; other browsers or real devices; screen reader; Mermaid rendering (no Mermaid diagrams remain; the architecture diagrams are SVG and were viewed rendered); external Console menu-path accuracy; human review; a licence and trademark check.

## Final run

See [../testing.md](../testing.md) for the test run table. The documentation checker's final result for this tree is recorded in the closing report and re-run by `node tools/check-docs.mjs`.

## Next review

After CP0 to CP2 evidence arrives: review each screenshot (configuration versus behaviour), update the register, re-run all checks, and revisit gates 3, 5 and 7.
