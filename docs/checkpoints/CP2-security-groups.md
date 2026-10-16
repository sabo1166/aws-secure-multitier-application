# CP2 Security groups

Status: **PLANNED**. Evidence: E-005. Depends on CP1 gate.

Menu paths are from memory and unverified against the live Console.

## 1. Objective and why it matters

Express "who may talk to whom" as three tier-based rules. Security groups attach to network interfaces and are stateful. Referencing another group, instead of a CIDR, means a new instance in that group is automatically allowed and nothing else is.

## 2. Console navigation

**VPC** > **Security groups** > **Create security group**. Select VPC `mt-vpc`. Edit inbound rules on the create page; edit outbound afterwards via **Outbound rules** > **Edit outbound rules**.

## 3. Configuration values and rationale

Create all three groups first with no custom rules, then add rules. The groups reference each other (alb-sg egress points at app-sg, app-sg ingress points at alb-sg), so a group must exist before another can name it.

| Group | Inbound | Outbound |
|---|---|---|
| `mt-alb-sg` | HTTP, TCP 80, source `0.0.0.0/0` | Custom TCP 8080, destination `mt-app-sg` (delete the default allow-all) |
| `mt-app-sg` | Custom TCP 8080, source `mt-alb-sg`. **No port 22** | Custom TCP 3306 to `mt-db-sg`; HTTPS TCP 443 to `0.0.0.0/0` (delete the default allow-all) |
| `mt-db-sg` | MySQL/Aurora TCP 3306, source `mt-app-sg` | None (delete the default allow-all) |

Rationale:
- 0.0.0.0/0 on port 80 is the only intentionally public rule in the project. Everything else is group-to-group.
- 443 outbound from the app tier is what Session Manager, Secrets Manager and package downloads need; it is the broadest rule below the ALB, so know why it exists (D-005, D-008).
- Port 8080 for the app avoids running a web server as root on a privileged port.
- An empty outbound list on db-sg is valid: replies to allowed inbound connections are permitted automatically because security groups are stateful.

## 4. Security and cost implications

- Security: removing default allow-all egress is an extra control that can cause confusing failures later; the diagnostics below say how to find them.
- Cost: security groups are free.

## 5. Expected result

Three groups. Rule counts: alb-sg 1 in / 1 out; app-sg 1 in / 2 out; db-sg 1 in / 0 out.

## 6. Verification procedure

1. For each group open **Inbound rules** and **Outbound rules** and confirm source and destination show `sg-...` references (with the group name) where specified, not CIDR ranges.
2. Search every group for port 22: there must be none.
3. Open `mt-db-sg` > **Related resources** later (after CP3) to confirm the database uses it.
4. Predict-then-check: if someone attaches a new instance to `mt-app-sg` in another subnet, can it reach the database? (Yes. That is exactly what the group means.) Can an instance with no group reach it? (No.)

## 7. Evidence to capture

`E-005-alb-sg-rules.png`, `E-005-app-sg-rules.png`, `E-005-db-sg-rules.png`, each showing both inbound and outbound (two screenshots per group if needed).

What this proves: configuration only. It does not prove traffic is blocked or allowed. Behavior tests are in CP6.

## 8. Common failures and diagnostics

| Symptom (later checkpoints) | Likely cause | Check |
|---|---|---|
| Target group unhealthy | app-sg inbound not 8080 from alb-sg, or alb-sg outbound missing 8080 to app-sg, or app listening on a different port | Both SG rule sets; health check port |
| App cannot reach DB | app-sg outbound lacks 3306 to db-sg, or db-sg inbound source wrong | Both rule sets |
| Instance not appearing in Session Manager, or package install hangs | Missing 443 outbound, or no NAT route | app-sg outbound; app-rt routes |
| Rule would not save | Group referenced is in a different VPC | VPC selection |

## 9. Gate to move forward

All three groups captured and reviewed; no rule other than ALB port 80 uses 0.0.0.0/0 inbound, and the only 0.0.0.0/0 outbound is 443 on app-sg. Status becomes IMPLEMENTED.

## Interview prep

Stateful vs stateless (SG vs NACL); why reference a group; why remove default egress; what breaks if ALB egress is removed entirely.
