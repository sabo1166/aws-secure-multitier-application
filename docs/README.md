# Documentation index

Start with the [project README](../README.md). Everything on AWS is **planned** until evidence says otherwise; each document labels what is implemented, tested, deployed and verified.

## Understand the design

The code is split into [../backend/README.md](../backend/README.md) (FastAPI) and [../frontend/README.md](../frontend/README.md) (server-rendered templates and static files); [../tools/README.md](../tools/README.md) documents the local QA helpers.

| Document | What it answers |
|---|---|
| [architecture.md](architecture.md) | What is being built, the request flow, network plan, security-group chain, services and why, expected failure behaviour |
| [security.md](security.md) | Every security control, its real status, and the known limitations |
| [project-summary.md](project-summary.md) | One honest page: where the project stands |
| [diagrams/architecture.svg](diagrams/architecture.svg), [diagrams/architecture-compact.svg](diagrams/architecture-compact.svg) | Editable diagram sources (`../architecture.png` is rendered from the first) |

## Build it (manual, AWS Console)

| Document | Use it for |
|---|---|
| [implementation-guide.md](implementation-guide.md) | The order of work, how to work any checkpoint, what each step proves |
| [local-setup.md](local-setup.md) | Run and test the application locally with no AWS account |
| [checkpoints/](checkpoints/CP8-application-local.md) | Nine-part runbooks: [CP0](checkpoints/CP0-account-guardrails.md), [CP1](checkpoints/CP1-vpc-and-subnets.md), [CP2](checkpoints/CP2-security-groups.md), [CP8](checkpoints/CP8-application-local.md) |
| [rds-setup-guide.md](rds-setup-guide.md) | RDS MySQL end to end (CP3), including the application database user |
| [deployment-guide.md](deployment-guide.md) | IAM role, NAT, launch template, Auto Scaling, load balancer (CP4, CP5) |
| [cost-analysis.md](cost-analysis.md) | What bills, teardown order, cost control (CP7) |

## Verify and troubleshoot

| Document | Use it for |
|---|---|
| [testing.md](testing.md) | What was run and passed, what was not tested, and the AWS validation tests still to do |
| [troubleshooting.md](troubleshooting.md) | Real issues found so far, a log for your AWS issues, and likely problems by area |
| [../screenshots/README.md](../screenshots/README.md) | The capture checklist for your real AWS screenshots |

## Project management (single source of truth)

| Document | Role |
|---|---|
| [project/PROJECT_STATUS.md](project/PROJECT_STATUS.md) | Progress per checkpoint |
| [project/DECISIONS.md](project/DECISIONS.md) | Decisions, alternatives, trade-offs |
| [project/EVIDENCE_REGISTER.md](project/EVIDENCE_REGISTER.md) | **The only evidence register**: each claim, its evidence, what it does not prove |
| [project/QUALITY_REVIEW.md](project/QUALITY_REVIEW.md) | Reviews, release gates, release decision |
| [project/NEXT_STEPS.md](project/NEXT_STEPS.md) | What to do next |

## Learning and presentation

| Document | Purpose |
|---|---|
| [interview-qa.md](interview-qa.md) | Questions and answers matched to the real implementation, tagged by what you can say now |
| [linkedin-ideas.md](linkedin-ideas.md) | Post ideas gated behind real evidence |
| [visual/01-technical-case-study.pdf](visual/01-technical-case-study.pdf), [visual/02-visual-project-notebook.pdf](visual/02-visual-project-notebook.pdf), [visual/03-notebook-project-summary.pdf](visual/03-notebook-project-summary.pdf) | Three A4 documents (HTML sources alongside) |
| [assets.md](assets.md) | Image and font sources and licences |
