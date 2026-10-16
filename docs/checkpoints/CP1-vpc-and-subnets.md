# CP1 VPC, subnets, internet gateway, route tables

Status: **PLANNED**. Evidence: E-003, E-004. Depends on CP0 gate. Design: [../architecture.md](../architecture.md).

Menu paths are from memory and unverified against the live Console; tell me where your screen differs.

## 1. Objective and why it matters

Build the network that every later control sits on. The key idea you must be able to defend: a subnet is "public" only because its route table sends 0.0.0.0/0 to an internet gateway, not because of its name.

## 2. Console navigation

**VPC** service > **Your VPCs** > **Create VPC** > choose **VPC only** (building the pieces yourself is the point; the "VPC and more" wizard hides them). Then **Subnets**, **Internet gateways**, **Route tables**.

## 3. Configuration values and rationale

**VPC**

| Field | Value | Rationale |
|---|---|---|
| Name | `mt-vpc` | Prefix `mt-` on everything makes cleanup and searching easy |
| IPv4 CIDR | `10.0.0.0/16` | Large private range; room for more subnets |
| IPv6 | None | Not needed; avoids a second address family to secure |
| Tenancy | Default | Dedicated costs extra |
| After creating | Actions > Edit VPC settings > enable **DNS hostnames** (DNS resolution stays on) | RDS endpoints and AWS service names resolve through VPC DNS |

**Subnets** (Subnets > Create subnet, select `mt-vpc`; pick two different AZs, call them a and b)

| Name | AZ | CIDR |
|---|---|---|
| `mt-public-a` | a | `10.0.0.0/24` |
| `mt-public-b` | b | `10.0.1.0/24` |
| `mt-app-a` | a | `10.0.10.0/24` |
| `mt-app-b` | b | `10.0.11.0/24` |
| `mt-db-a` | a | `10.0.20.0/24` |
| `mt-db-b` | b | `10.0.21.0/24` |

Leave **auto-assign public IPv4** off on every subnet. The ALB gets its own public addresses; nothing else needs one.

**Internet gateway:** name `mt-igw`, create, then **Actions > Attach to VPC** > `mt-vpc`.

**Route tables** (Route tables > Create route table, VPC `mt-vpc`)

| Name | Extra routes | Subnet associations (Subnet associations tab > Edit) |
|---|---|---|
| `mt-public-rt` | `0.0.0.0/0` to `mt-igw` | `mt-public-a`, `mt-public-b` |
| `mt-app-rt` | none yet (NAT added in CP4) | `mt-app-a`, `mt-app-b` |
| `mt-db-rt` | none, ever | `mt-db-a`, `mt-db-b` |

The VPC's **main route table** stays unassociated by choice; do not add routes to it. Any subnet you forget to associate falls back to the main route table, so check that no subnet is left on it.

## 4. Security and cost implications

- Security: the IGW is attached, so the only thing keeping app and db subnets private is that their route tables have no IGW route. This is a first layer; security groups are the second (CP2).
- Cost: VPC, subnets, route tables and an attached IGW have no hourly charge. Do not create a NAT Gateway or any public IPv4 resource yet.

## 5. Expected result

One VPC, six subnets in two AZs, one IGW attached, three route tables with the associations above.

## 6. Verification procedure

1. Subnets list: sorted by name, confirm CIDR and AZ columns match the table; no two subnets share a CIDR.
2. Each route table: **Routes** tab and **Subnet associations** tab. Only `mt-public-rt` contains an `igw-` target.
3. VPC > **Resource map** (or the VPC details page) gives a visual cross-check.
4. Predict-then-check: before opening `mt-db-rt`, write down what its routes should be (answer: one local route for 10.0.0.0/16).

## 7. Evidence to capture

- `E-003-vpc-details.png` (DNS hostnames enabled visible) and `E-003-subnets.png` (name, AZ, CIDR columns).
- `E-004-public-rt-routes.png`, `E-004-public-rt-assoc.png`, `E-004-app-rt.png`, `E-004-db-rt.png` (each showing Routes and associations; the app and db tables may combine both tabs in two shots).

These prove configuration. They do not prove instances are unreachable; that arrives with E-007 and E-010.

## 8. Common failures and diagnostics

| Symptom | Likely cause | Check |
|---|---|---|
| "CIDR overlaps" error | Typo or wrong VPC selected | Compare against the table |
| Both subnets land in the same AZ | Default AZ selection | Reopen subnet, check AZ column |
| IGW state "Detached" | Skipped attach step | Actions > Attach to VPC |
| A private subnet shows an `igw-` route | Associated with the public route table | Subnet associations tab of each table |
| A subnet shows no explicit association | Falls back to main table | Route tables > Subnet associations > Explicit tab |
| Resources not visible | Wrong Region | Region selector |

## 9. Gate to move forward

E-003 and E-004 screenshots reviewed; every subnet has an explicit association; you can answer the interview questions below without notes. Status then becomes IMPLEMENTED (nothing here is behavior-verified until CP6).

## Interview prep

What makes a subnet public? What is the "local" route? Why two AZs for the db subnets when RDS is a single instance? What does the main route table do and why is leaving it alone safer?
