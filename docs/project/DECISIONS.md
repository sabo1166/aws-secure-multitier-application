# DECISIONS

Each entry: context, decision, alternatives, trade-offs, and an interview question you should be able to answer. Status values: PROPOSED (my recommendation, awaiting your agreement), ACCEPTED (you agreed), OPEN (needs your input), SUPERSEDED.

## D-001 Manual Console first, no IaC yet — ACCEPTED (by your brief)

- **Why:** You learn what each setting does and what breaks when it is wrong. Terraform later only automates something you can already explain.
- **Alternatives:** Terraform or CloudFormation from day one (faster to repeat, but hides the reasoning).
- **Trade-off:** Console work is slow and not reproducible. Mitigation: record every value in the checkpoint runbooks.
- **Interview question:** "Why didn't you use Terraform?"

## D-002 Region — OPEN

- **Needed from you:** one Region, used for everything. Pick one close to you with the services needed (ALB, RDS, NAT, Secrets Manager, SSM are available in all major Regions).
- **Why it matters:** the Console shows only one Region at a time, and forgotten resources in another Region are the classic cost leak. Every runbook says "confirm the Region selector".

## D-003 Two AZs, three tiers, six subnets — PROPOSED

- **Decision:** public (ALB), private app (EC2), private db (RDS) subnets, one of each per AZ.
- **Alternatives:** single AZ (cheaper, but cannot demonstrate availability); three AZs (more cost, no new concept).
- **Trade-off:** six subnets is more to manage; it is the minimum that shows both isolation and AZ redundancy.
- **Interview question:** "What actually happens to your app if AZ a fails?" (Answer must include: single NAT and single-AZ database are still single points of failure; see D-006 and D-007.)

## D-004 Security groups reference security groups — PROPOSED

- **Decision:** db-sg allows 3306 only from app-sg; app-sg allows 8080 only from alb-sg. Outbound rules are restricted rather than left at the default allow-all.
- **Alternatives:** CIDR-based rules (break when addressing changes, and allow anything in the range); NACLs as the main control (stateless, more error-prone).
- **Trade-off:** restricted egress can break package installs or AWS API calls in confusing ways; the runbook includes diagnostics.
- **Interview question:** "Security groups are stateful. What does that mean for the return traffic of an allowed request?"

## D-005 No SSH, no key pair; Session Manager for access — PROPOSED

- **Decision:** no inbound port 22, instances get an IAM role with the SSM managed policy.
- **Alternatives:** bastion host (extra instance and attack surface), SSH from my IP (my IP changes, port stays exposed).
- **Trade-off:** needs outbound 443 to SSM (via NAT here) and an IAM role. Access is logged to your account, not to a key file.
- **Interview question:** "How do you get a shell on a private instance without opening a port?"

## D-006 One NAT Gateway, added late and removed first — PROPOSED

- **Decision:** a single NAT Gateway in public-a, created only in CP4 when instances need outbound internet, deleted in CP7 before anything else.
- **Alternatives:** NAT per AZ (resilient, doubles the hourly charge); VPC endpoints for SSM, Secrets Manager and S3 (no internet path, but several endpoints, each with its own hourly cost, and package installs still need a source); put instances in public subnets (cheapest, breaks the isolation story).
- **Trade-off:** NAT is a single point of failure for private egress, and it is a metered resource that bills while it exists. This is a deliberate lab cost-versus-resilience choice, stated in the README later.
- **Cost action:** check the current NAT Gateway pricing page and note the date in the CP4 runbook before creating it.
- **Interview question:** "Your NAT Gateway's AZ fails. What breaks and what keeps working?"

## D-007 RDS MySQL, single-AZ, not publicly accessible — PROPOSED

- **Decision:** MySQL 8.4 (8.0 is already in paid Extended Support per AWS docs checked 2026-10-15), smallest burstable instance class, encrypted at rest, public access No, in a DB subnet group of the two db subnets.
- **Alternatives:** Multi-AZ (the real production answer, roughly doubles database cost, adds failover test); Aurora (more cost and complexity than the lesson needs); DynamoDB (removes the relational tier).
- **Trade-off:** DB AZ failure means downtime. Documented honestly rather than hidden.
- **Interview question:** "What would you change to make the database production-ready?"

## D-008 Database credentials: managed admin secret, separate low-privilege app user — PROPOSED (revised 2026-10-15)

- **Decision:** RDS creates and rotates the **master (admin) password** in Secrets Manager; the application never uses it. A dedicated MySQL user `sole_app` (SELECT, INSERT, UPDATE, DELETE on the app database, TLS required) has its own secret `sole-atelier/db-app`; a second secret `sole-atelier/session` holds the cookie-signing key. The instance role may read only those two secrets. Schema creation is a separate admin step (`python -m backend.init_db --admin-user admin`, password typed at a prompt).
- **Supersedes:** the earlier version of this decision, in which the app would have used the master user. That conflicted with least privilege and is removed.
- **Alternatives:** hard-coded password (unacceptable); SSM Parameter Store SecureString (cheaper, no built-in rotation); IAM database authentication (stronger, more setup, left as a production step).
- **Trade-off:** small recurring secret cost; the app user's password and the session key are **not rotated**; `sole_app` still has write access to all app tables. Disclosed in [../security.md](../security.md).
- **Interview question:** "Where is the database password, and who can read it?"

## D-009 HTTP only on the ALB — PROPOSED

- **Decision:** listener on port 80, no custom domain, no TLS.
- **Alternatives:** ACM certificate plus Route 53 domain (needs a domain, extra cost, real production requirement).
- **Trade-off:** traffic from the user to the ALB is unencrypted. The README must say this plainly.
- **Interview question:** "Is this production-ready? What is the first thing you'd add?"

## D-010 Auto Scaling group: one instance while debugging, then two — PROPOSED

- **Decision:** launch template plus ASG: one instance while debugging (CP4), then desired 2 across two AZs with ELB health checks (CP5). A single instance is an acceptable cheaper fallback if documented; the cart cookie is signed with a shared key so two instances need no sticky sessions (D-016).
- **Alternatives:** two hand-made instances (simpler, but cannot show self-healing).
- **Trade-off:** one extra concept (launch template). It earns the self-healing test E-012.
- **Interview question:** "What is the difference between EC2 and ELB health checks in an ASG?"

## D-011 Evidence discipline — ACCEPTED (by your brief)

- **Decision:** nothing is `VERIFIED` without an evidence file and an observed result. See `docs/project/EVIDENCE_REGISTER.md`.

## D-012 Daily-work identity — OPEN

- **Needed from you:** IAM Identity Center user, or an IAM user with MFA. Referenced by CP0. Either is acceptable for a personal lab; record which and why. Administrator permissions are a documented lab limitation (see QUALITY_REVIEW S-1).

## D-013 Liveness and readiness health checks are separate — PROPOSED (implemented)

- **Decision:** `GET /health` returns 200 without touching the database and is what the ALB checks. `GET /health/ready` also runs `SELECT 1` and returns 503 when the database is down, for humans and diagnostics.
- **Alternatives:** one check that includes the database (an RDS blip would mark all targets unhealthy and take the whole site down); no database check at all (a broken connection would go unnoticed).
- **Trade-off:** the ALB will keep sending traffic to instances that cannot reach the database; they return 503 on data pages. That is intentional and tested locally. AWS behaviour is unobserved.
- **Interview question:** "Why does your health check not check the database?"

## D-014 Delivering the app to instances: pinned Git commit via user data — PROPOSED

- **Decision:** the launch template's user data clones the public repository at a reviewed commit SHA and installs pinned requirements from PyPI. No artifact bucket, no pipeline.
- **Alternatives:** S3 zip read by the instance role (extra service and permission, works for a private repo); baking an AMI (more steps); CodeDeploy or CI/CD (excluded by the manual-only rule).
- **Trade-off:** depends on GitHub and PyPI being reachable through the NAT at boot; requires the repository to be public (or another method); updates are manual (new template version and instance refresh). The user-data script is untested.
- **Interview question:** "How does new code reach production, and what would you automate first?"

## D-015 No migration tool; explicit, non-destructive schema creation — PROPOSED (implemented)

- **Decision:** `python -m backend.init_db` runs `create_all`, which only creates missing tables. In production the schema is created once by an admin account; the app user has no DDL rights and the app never creates tables when `APP_ENV=production`.
- **Alternatives:** Alembic (right for real change over time, more machinery than a demo needs); auto-create at startup (needs DDL rights on the app user, rejected).
- **Trade-off:** schema changes after launch are manual. Listed as a limitation.

## D-016 Cart in a signed cookie, session key shared via Secrets Manager — PROPOSED (implemented)

- **Decision:** the cart stores product id, size and quantity only, in a signed, HttpOnly, SameSite=Lax cookie. Prices and stock are always re-read. Both instances read the same signing key from Secrets Manager, so any instance can serve any request.
- **Alternatives:** server-side cart table (more schema, needs a session id anyway); sticky sessions on the ALB (couples users to instances); ElastiCache (extra service and cost).
- **Trade-off:** per-browser cart, lost when cookies clear, size-limited, and the key must be protected. Rotating the key logs everyone out.
- **Interview question:** "Why didn't you store the cart in the database?"

## D-017 Application stack — ACCEPTED (by your brief)

- **Decision:** Python and FastAPI, Jinja2 server-rendered pages, vanilla JavaScript, SQLAlchemy; SQLite locally and MySQL on RDS chosen by environment variables.
- **Why:** smallest stack that shows a real frontend, backend and relational database without a build system.

## D-018 Illustrated assets instead of photography — PROPOSED

- **Decision:** original vector illustrations generated by `scripts/generate_product_art.py` stand in for product photos, and are labelled as illustrations.
- **Alternatives:** download third-party photos (licensing and trademark risk); AI-generated photos (cannot be presented as real products; none was available).
- **Trade-off:** less visual realism. Replacement steps are in [../assets.md](../assets.md).

