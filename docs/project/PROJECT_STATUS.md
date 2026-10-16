# PROJECT_STATUS

Single source of truth for progress. Last updated: 2026-10-15.

**Project:** SOLE ATELIER, a secure three-tier sneaker storefront (FastAPI, Jinja2, SQLAlchemy) designed for AWS and built manually in the Console.
**Phase:** the application is built and tested locally on SQLite. **No AWS resource has been created or reported yet.**
**Active checkpoint:** CP8 (re-run locally yourself, E-019), then CP0.

Statuses: `PLANNED`, `IN PROGRESS`, `IMPLEMENTED` (exists, configuration shown), `VERIFIED` (behavior observed, evidence recorded), `FAILED`, `BLOCKED`.

## Checkpoints

| CP | Name | Status | Evidence IDs | Exit gate |
|---|---|---|---|---|
| CP0 | Account guardrails: budget alert, root MFA, non-root admin identity, region chosen | PLANNED | E-001, E-002 | Budget alert and MFA screenshots reviewed |
| CP1 | VPC, six subnets, internet gateway, route tables | PLANNED | E-003, E-004 | Route tables show only public subnets reach the IGW |
| CP2 | Security groups (alb-sg, app-sg, db-sg) | PLANNED | E-005 | Rules match the chain in the architecture file |
| CP3 | RDS MySQL in private subnets with managed secret | PLANNED | E-006 | Not publicly accessible; secrets exist |
| CP4 | IAM role, launch template, app bootstrap (adds NAT Gateway) | PLANNED | E-011, E-013 | Instance reachable only through Session Manager; no secret in user data |
| CP5 | ALB, target group, Auto Scaling group | PLANNED | E-009 | Both targets healthy |
| CP6 | End-to-end and negative tests | PLANNED | E-007, E-008, E-010, E-012 | Every test has recorded observed output |
| CP7 | Teardown and cost check | PLANNED | E-014 | Resource inventory empty; billing reviewed |
| CP8 | Application built and tested locally (SQLite) | IMPLEMENTED | E-015, E-016, E-017, E-018, E-019, E-020, E-021, E-022, E-023 | You re-run the tests and the app yourself (E-019) and can explain them |

CP8 is IMPLEMENTED, not VERIFIED, because the evidence (E-015 to E-018, E-020 to E-023) comes from runs Claude performed; E-019 (your own run) is still planned.

## What is true about the application today

| Capability | Implemented in code | Tested locally (SQLite) | Tested with MySQL | Deployed to AWS | Verified in AWS |
|---|---|---|---|---|---|
| Catalogue, search, filter, sort | Yes | Yes | No | No | No |
| Product page with per-size stock | Yes | Yes | No | No | No |
| Cart (signed cookie, server pricing) | Yes | Yes | No | No | No |
| Demo checkout, idempotent orders, atomic stock | Yes | Yes (sequential and simulated race) | No | No | No |
| Health checks (liveness, readiness) | Yes | Yes | No | No | No |
| Secrets Manager credential loading | Yes | Fake client only | No | No | No |
| Schema init script for an admin account | Yes | SQLite only | No | No | No |
| VPC, SGs, RDS, EC2, ALB, NAT | n/a | n/a | n/a | No | No |

## Runbooks and guides

- Local build: [CP8](../checkpoints/CP8-application-local.md), [../local-setup.md](../local-setup.md), [../testing.md](../testing.md)
- AWS checkpoints: [CP0](../checkpoints/CP0-account-guardrails.md), [CP1](../checkpoints/CP1-vpc-and-subnets.md), [CP2](../checkpoints/CP2-security-groups.md), [../rds-setup-guide.md](../rds-setup-guide.md) (CP3), [../deployment-guide.md](../deployment-guide.md) (CP4 and CP5), testing.md "AWS validation" (CP6), [../cost-analysis.md](../cost-analysis.md) (CP7)
- Order of work: [../implementation-guide.md](../implementation-guide.md)

## Open questions

- Which AWS Region? See D-002 and D-012 in [DECISIONS.md](DECISIONS.md).
- Does the account have free-tier credit? Check Billing before CP3.
- Which licence (if any) for the repository? Not chosen; do not add one without deciding.
- Is the name SOLE ATELIER free to use publicly? Not checked.

## Checks performed on this workspace

See [QUALITY_REVIEW.md](QUALITY_REVIEW.md) for results, the release decision, and the checks that could not be performed.
