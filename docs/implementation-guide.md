# Implementation guide

The route through the project. Everything on AWS is built **manually in the Console** (no pipelines, templates or scripts that create resources). Local work needs no AWS account.

## How to work any checkpoint

1. **Predict**: write down what you expect to see and why, before you click.
2. **Implement** with the values in the runbook.
3. **Verify behaviour**, not just configuration (a screenshot of a setting is not a test of the setting).
4. **Capture** the listed evidence, redact it, and save it under [../screenshots/README.md](../screenshots/README.md).
5. **Review**: update [project/EVIDENCE_REGISTER.md](project/EVIDENCE_REGISTER.md) and [project/PROJECT_STATUS.md](project/PROJECT_STATUS.md), then run `node tools/check-docs.mjs`.
6. **Explain it aloud** using the interview prompts before moving on.

Statuses: `PLANNED`, `IN PROGRESS`, `IMPLEMENTED` (exists, configuration shown), `VERIFIED` (behaviour observed, evidence recorded), `FAILED`, `BLOCKED`.

## Sequence

| Step | Checkpoint | Guide | Evidence | Cost |
|---|---|---|---|---|
| 1 | **CP8** application, local | [local-setup.md](local-setup.md), [checkpoints/CP8-application-local.md](checkpoints/CP8-application-local.md), [testing.md](testing.md) | E-015 to E-019 | none |
| 2 | **CP0** account guardrails | [checkpoints/CP0-account-guardrails.md](checkpoints/CP0-account-guardrails.md) | E-001, E-002 | none |
| 3 | **CP1** VPC and subnets | [checkpoints/CP1-vpc-and-subnets.md](checkpoints/CP1-vpc-and-subnets.md) | E-003, E-004 | none |
| 4 | **CP2** security groups | [checkpoints/CP2-security-groups.md](checkpoints/CP2-security-groups.md) | E-005 | none |
| 5 | **CP3** RDS | [rds-setup-guide.md](rds-setup-guide.md) sections 1 to 10, 12 to 14 | E-006 | RDS bills |
| 6 | **CP4** IAM, NAT, launch template, first instance | [deployment-guide.md](deployment-guide.md) parts A to D, then RDS guide sections 11, 15 to 19 | E-011, E-013, E-008 | NAT, EC2 bill |
| 7 | **CP5** ALB, target group, two instances | [deployment-guide.md](deployment-guide.md) parts E and F | E-009 | ALB bills |
| 8 | **CP6** end-to-end and negative tests | [testing.md](testing.md) "AWS validation", deployment guide part G | E-007, E-008, E-010, E-012 | all running |
| 9 | **CP7** teardown and cost check | [cost-analysis.md](cost-analysis.md) | E-014 | stops billing |

Do CP8 first: it proves the application works before any AWS cost exists, and you will understand what you are deploying.

Runbooks for CP0 to CP2 and CP8 follow the nine-part format (objective, navigation, values, security and cost, expected result, verification, evidence, failures, gate). CP3 to CP7 are written as the RDS and deployment guides, each with its own evidence and verification steps, and are tracked as checkpoints in [project/PROJECT_STATUS.md](project/PROJECT_STATUS.md).

## Rules that keep the project honest

- Do not mark anything `VERIFIED` without an evidence file and an observed result.
- A healthy target group is not proof that checkout works; a database setting is not proof the database is unreachable.
- Hide account IDs, public IPs, credentials and database endpoints before a screenshot leaves `evidence/raw/` ([../evidence/README.md](../evidence/README.md)).
- If something fails, record it in [troubleshooting.md](troubleshooting.md) with the evidence. A resolved failure is stronger portfolio material than a clean run.
