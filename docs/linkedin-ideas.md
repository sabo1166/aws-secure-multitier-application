# LinkedIn content ideas (drafts to write only from real work)

This is a planning list, not a set of posts. **Nothing here has been posted or should be posted until the precondition is met.** Each idea needs real evidence of your own. Write in your own words, name what is a lab and what is verified, and publish manually; no automation posts for you.

Rules: no claim of an AWS deployment before E-009 and E-008 are VERIFIED; no engagement, recruiter-interest, usage or performance numbers you have not measured; no account IDs, endpoints or credentials in images; no "excited to announce" style filler.

| # | Idea | Precondition | Evidence to link | Honest label |
|---|---|---|---|---|
| 1 | "My test suite passed. Then I broke the code on purpose to see if it would notice." (mutation check of stock guard, CSRF, price calculation: 3 of 3 caught, one only by a single test) | Available now | `evidence/redacted/E-015-*` | Built and tested locally (SQLite) |
| 2 | "Why my load balancer health check does not touch the database" (liveness vs readiness, and what a database blip would do) | Available now for the design and local behaviour; add AWS observation after CP6 | E-015, later E-009 | Local; design for AWS |
| 3 | "Never trust the browser's price: how the cart works" (ids only in the cookie, server re-prices, snapshot at order time) | Available now | E-015 | Built and tested locally |
| 4 | "The last pair of shoes: preventing overselling with one SQL statement" | Available now (sequential and simulated race only; do not claim concurrency load testing) | E-015 | Tested locally, no load test |
| 5 | "A mobile screenshot that lied to me" (headless browser minimum width, and the capture tool I wrote) | Available now | `docs/troubleshooting.md` section 1 | Real local issue |
| 6 | "Private subnet, public subnet: it is a route table, not a name" | After CP1 evidence (E-003, E-004) | Your route table screenshots | Verified configuration |
| 7 | "A healthy target group proved less than I thought" | After CP5 and CP6 | E-009 and E-008 side by side | Verified in AWS |
| 8 | "How I proved my database is not reachable from the internet" (configuration versus a failed connection) | After E-006 and E-007 | Both screenshots | Verified in AWS |
| 9 | "What I got wrong the first time" (your real AWS troubleshooting story) | After you record an issue in `docs/troubleshooting.md` section 2 | The evidence files | Real incident |
| 10 | "What this lab costs and how I kept it from costing more" (NAT, ALB, RDS, teardown order) | After CP7, with prices you looked up and dated | E-014 | Verified teardown |
| 11 | "Preparing a repository so a stranger can run it" (README, `.env.example`, secret scan) | After you review the repository yourself | Repo link (only after you decide to publish) | Process |

## Template (fill from your evidence)

> **What I built:** one sentence, with the label (local / deployed / verified).
> **What went wrong or surprised me:** the real event.
> **What I changed:** the decision and why.
> **Evidence:** the screenshot or test output.
> **What is still unproven:** one honest line.

Record each post in this table with the date you actually published it and the evidence file it relies on.
