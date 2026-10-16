# Project summary

**SOLE ATELIER** is a fictional premium sneaker boutique built as a portfolio project: a working Python storefront designed to run in a three-tier AWS architecture that I build by hand in the AWS Console to learn and demonstrate networking, security, deployment and troubleshooting.

## Where things stand

| Area | State | Evidence |
|---|---|---|
| Application (catalogue, search, cart, demo checkout, health checks) | **Implemented. Tested locally on SQLite** | 91 automated tests, 6 of 6 deliberate-bug checks caught, 35 of 35 real-browser checks, local screenshots. See [testing.md](testing.md) |
| Documentation, runbooks, evidence register, review log | Written | `node tools/check-docs.mjs` |
| AWS infrastructure (VPC, security groups, RDS, EC2, ALB, NAT) | **Planned. Nothing created** | none |
| Application on MySQL / RDS | **Not tested** | none |
| Anything deployed or verified in AWS | **No** | none |

The honest one-line summary: *the application works locally and the AWS design and runbooks are ready, but I have not yet built or verified any AWS resource.* This file will change only when evidence arrives.

## What it demonstrates (today)

- A full-stack application with a relational data model, input validation, CSRF protection, server-side pricing, atomic stock reservation, idempotent order creation and safe error handling, with tests that fail when those behaviours are broken.
- A deliberate AWS design with written trade-offs: private subnets, security-group chaining, no SSH, a least-privilege database user, secrets out of code, and honest limitations.
- An evidence discipline: every claim is classed as configuration or behaviour, with a register of what is proven and what is not.

## What it will demonstrate (after you build it)

Practical VPC, subnet and route-table work; security groups and their negative tests; RDS in private subnets; EC2 bootstrap, IAM role and Session Manager; ALB and Auto Scaling health behaviour; cost control and teardown; and your real troubleshooting stories.

## Deliberate scope limits

Manual Console only (no pipelines or infrastructure as code), HTTP only, one Region, one NAT gateway, a single-AZ database, demo checkout without payments. Each is a recorded decision in [project/DECISIONS.md](project/DECISIONS.md) with the production alternative.

## Where to look

[../README.md](../README.md) overview · [architecture.md](architecture.md) · [implementation-guide.md](implementation-guide.md) · [security.md](security.md) · [project/QUALITY_REVIEW.md](project/QUALITY_REVIEW.md) (release decision) · [interview-qa.md](interview-qa.md)
