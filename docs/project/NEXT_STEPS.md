# NEXT_STEPS

Last updated: 2026-10-15. Claude will not perform AWS actions, commit, push or publish. Nothing on AWS exists yet.

## For you, in order

1. **Re-run the application yourself (CP8, E-019).** Follow [../local-setup.md](../local-setup.md): `pytest`, run the app, place a demo order. Then **break something on purpose** (see CP8 step 6), predict which test fails, and restore it. Save your own output as `evidence/redacted/E-019-my-pytest-run.txt`. You cannot defend code you have never run.
2. **Read the code you will be asked about**, in this order: `backend/services/orders.py`, `backend/services/cart.py`, `backend/security.py`, `backend/config.py`. Use [../interview-qa.md](../interview-qa.md) as the quiz; answer aloud without notes.
3. **Make the decisions only you can make:**
   - D-002 Region and D-012 identity type ([DECISIONS.md](DECISIONS.md)).
   - Accept or challenge each PROPOSED decision, especially D-006 (single NAT), D-007 (single-AZ database), D-014 (app delivery by pinned Git commit).
   - Repository licence (none chosen).
   - Whether to keep the name SOLE ATELIER (not checked for trademarks).
   - The wording of the **Authorship and AI assistance** section in [../../README.md](../../README.md): it must say what you personally did.
4. **Do CP0 in the Console** ([CP0](../checkpoints/CP0-account-guardrails.md)): budget alert, root MFA, non-root identity. Capture the screenshots listed in [../../screenshots/README.md](../../screenshots/README.md) (`04-security/05` to `07`), hide account IDs and emails first, and send them to me redacted.
5. **Check the Billing Free Tier page** and tell me what your account actually includes.
6. Then CP1 and CP2 (free). Stop and ask before CP3: RDS, NAT and the load balancer cost money.

## Manual AWS Console screenshot checklist

The full numbered checklist, what each image must show, and redaction reminders are in [../../screenshots/README.md](../../screenshots/README.md). In short, in order of the build:

1. CP0: `04-security/07-budget.png`, `05-root-mfa.png`, `06-nonroot-session.png`
2. CP1: `02-networking/01` to `06` (VPC, subnets, three route tables, two shots each where noted)
3. CP2: `04-security/01` to `03` (three security groups)
4. CP3: `05-database/01` to `05`
5. CP4: `04-security/04` (IAM role), `03-compute/01`, `02`, `04`, `07-validation/05` (Session Manager), `02-networking/07` (NAT)
6. CP5: `03-compute/03`, `05`, `06`
7. CP6: `06-application/aws-01`, `aws-02`, `07-validation/01` to `08` and your real troubleshooting capture(s)
8. CP7: `07-validation/09`, `10`

## For Claude (when your evidence arrives)

1. Review each screenshot; write what it shows and what it does **not** prove; update [EVIDENCE_REGISTER.md](EVIDENCE_REGISTER.md) and [PROJECT_STATUS.md](PROJECT_STATUS.md). PLANNED becomes IMPLEMENTED only with a screenshot of the configuration, and VERIFIED only with an observed behaviour.
2. Correct the runbooks wherever your Console differs from what I wrote from memory.
3. Re-run `pytest`, `node tools/check-docs.mjs`, and update [QUALITY_REVIEW.md](QUALITY_REVIEW.md) gates 3, 5 and 7.
4. Before any publication: re-run `pip-audit`, and review every image for account IDs, emails, IPs and endpoints.

## Before you publish to GitHub (your decision, I will not do it)

- [ ] You edited the Authorship section and chose a licence (or deliberately none)
- [ ] You read every file you are putting your name on
- [ ] `node tools/check-docs.mjs` passes and `pytest` passes
- [ ] No `.env`, database file, key or `evidence/raw/` content is in the folder you push (`.gitignore` covers them, E-023)
- [ ] Every image in `screenshots/` was reviewed by you for private data
- [ ] README status still matches reality (it says nothing is deployed until it is)

## Blocked on

Your Region and identity decisions (D-002, D-012) and CP0 evidence. No AWS status moves past PLANNED until then.

## Parked (do not start)

Real photography, HTTPS and a domain, payments, infrastructure as code, CI/CD, Multi-AZ. Each is a documented next improvement, not a task for now.
