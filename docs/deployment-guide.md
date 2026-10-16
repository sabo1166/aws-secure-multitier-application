# Deployment guide (manual, AWS Console)

**Status: PLANNED. None of these steps has been run.** The user-data script below is an **untested draft**; the first real run will teach you what needs fixing, and those fixes belong in [troubleshooting.md](troubleshooting.md). Everything is done by hand in the Console. There is no pipeline, template or script that creates AWS resources.

Order of work and what each part proves is in [implementation-guide.md](implementation-guide.md). Cost warnings first: the **NAT gateway, ALB, RDS instance, EC2 instances and secrets are billed while they exist**. Look up current prices on the AWS pricing pages and record the date in [cost-analysis.md](cost-analysis.md) before creating each one, and time-box the lab.

Placeholders in `<angle brackets>` are values you obtain from your own account. None is invented here.

---

## Part A: IAM role for the instances (CP4)

**Objective:** give the instances exactly two powers: use Session Manager, and read two named secrets.

Console: **IAM** > **Roles** > **Create role** > Trusted entity **AWS service** > **EC2**.

| Setting | Value | Reason |
|---|---|---|
| Managed policy | `AmazonSSMManagedInstanceCore` | Session Manager access with no inbound port |
| Inline policy (add after creation) | see below | Least privilege for secrets |
| Role name | `mt-app-role` | |

Inline policy, using the **exact ARNs** shown in Secrets Manager for `sole-atelier/db-app` and `sole-atelier/session` (they end in a random suffix, so do not guess or wildcard them):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "secretsmanager:GetSecretValue",
    "Resource": ["<arn-of-sole-atelier/db-app>", "<arn-of-sole-atelier/session>"]
  }]
}
```

The secrets use the default AWS managed key, so no extra KMS permission is needed in the same account. **Not granted on purpose:** access to the RDS master secret, any S3, any `*`.

**Verify:** role page shows two policies. **Evidence:** `screenshots/04-security/04-iam-role-permissions.png` (E-011). **Proves:** configuration. **Does not prove:** that the role works (Part D does).

## Part B: NAT gateway and private route (CP4)

**Why now and not earlier:** it is the first thing that costs real money by the hour. Create it only when you are ready to launch instances, and delete it first at teardown.

1. **VPC** > **NAT gateways** > **Create NAT gateway**: name `mt-nat-a`, subnet **`mt-public-a`**, connectivity **Public**, **Allocate Elastic IP**.
2. **Route tables** > `mt-app-rt` > **Routes** > **Edit routes** > add `0.0.0.0/0` target **NAT gateway** `mt-nat-a`.
3. Do **not** touch `mt-db-rt`. The database subnets stay without any internet route.

**Single-NAT trade-off (D-006):** both app subnets send outbound traffic through the NAT in AZ a. If AZ a fails, private instances in AZ b lose outbound access (package installs, Secrets Manager, Session Manager) though inbound ALB traffic to them can still work. Accepted for cost; state it in the README.

**Evidence:** `screenshots/02-networking/05-nat-gateway.png`, `06-app-route-table-nat.png` (E-004 follow-up).

## Part C: Launch template (CP4)

Console: **EC2** > **Launch templates** > **Create launch template**.

| Setting | Value | Reason |
|---|---|---|
| Name | `mt-app-lt` | |
| AMI | Amazon Linux 2023 (match architecture to the instance type) | Maintained, SSM agent preinstalled |
| Instance type | Smallest general-purpose type that runs the app (for example `t3.micro` or `t4g.micro`) | Cost. Check pricing and whether your account has free-tier credit |
| Key pair | **Don't include** | No SSH (D-005) |
| Subnet | **Don't include** (the ASG picks) | |
| Security group | `mt-app-sg` | |
| Storage | Default size, **encrypted** | Encryption at rest |
| IAM instance profile | `mt-app-role` | |
| Advanced > Metadata version | **V2 only (token required)** | Blocks the classic SSRF path to instance credentials |
| Advanced > Auto-assign public IP | **Disable** (leave off in the subnet too) | Instances stay private |
| Advanced > User data | the draft below | Bootstraps the app |

### User data draft (UNTESTED)

Edit the placeholders in a local text editor, never in a shared place. Nothing here is a secret: the values are an endpoint, ARNs and a Git commit.

```bash
#!/bin/bash
set -euxo pipefail

# Package names must be confirmed on AL2023: `dnf search python3` / `dnf search git`.
dnf install -y git python3.12

useradd --system --home-dir /opt/sole-atelier --shell /sbin/nologin soleapp || true
mkdir -p /opt/sole-atelier
git clone <your-public-repo-url> /opt/sole-atelier/repo
git -C /opt/sole-atelier/repo checkout <commit-sha-you-reviewed>   # pin to a reviewed commit, not a moving branch

python3.12 -m venv /opt/sole-atelier/venv
/opt/sole-atelier/venv/bin/pip install -r /opt/sole-atelier/repo/requirements.txt

curl -fsS -o /opt/sole-atelier/global-bundle.pem https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem

cat > /etc/sole-atelier.env <<'EOF'
APP_ENV=production
DB_HOST=<rds-endpoint-hostname>
DB_PORT=3306
DB_NAME=sole_atelier
DB_SECRET_ARN=<arn-of-sole-atelier/db-app>
SESSION_SECRET_ARN=<arn-of-sole-atelier/session>
AWS_REGION=<region>
DB_SSL_CA=/opt/sole-atelier/global-bundle.pem
SESSION_HTTPS_ONLY=false
EOF
chown root:soleapp /etc/sole-atelier.env && chmod 640 /etc/sole-atelier.env
chown -R soleapp:soleapp /opt/sole-atelier

cat > /etc/systemd/system/sole-atelier.service <<'EOF'
[Unit]
Description=SOLE ATELIER (FastAPI)
After=network-online.target
Wants=network-online.target

[Service]
User=soleapp
WorkingDirectory=/opt/sole-atelier/repo
EnvironmentFile=/etc/sole-atelier.env
ExecStart=/opt/sole-atelier/venv/bin/uvicorn backend.main:create_app --factory --host 0.0.0.0 --port 8080 --proxy-headers
Restart=on-failure
NoNewPrivileges=true
ProtectSystem=full

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now sole-atelier
```

**Known risks in this draft (all unverified):**

- `git clone` assumes the repository is public and reachable through the NAT. If you keep it private, you need another delivery method (for example an S3 object read by the role, which adds a service and a permission).
- `python3.12` may not be the right package name or version on AL2023, and the pinned requirements may need a different Python.
- The app starts before the database user and tables exist on the very first launch (RDS guide, sections 11 and 17). Expect `503` from `/health/ready` and, if the secret does not exist yet, a failed start. Do Part D first, finish the RDS pause point, then restart the service.
- It runs from a cloned Git commit and PyPI downloads: pin versions (already pinned in `requirements.txt`) and review what you deploy.

**Evidence:** `screenshots/03-compute/01-launch-template.png` (details), and a screenshot showing the **User data** with placeholders visible and **no secret values** (E-013).

## Part D: Auto Scaling group of one, and first checks (CP4)

Console: **EC2** > **Auto Scaling groups** > **Create**.

| Setting | Value | Reason |
|---|---|---|
| Name | `mt-app-asg` | |
| Launch template | `mt-app-lt` | |
| VPC / subnets | `mt-vpc`, **`mt-app-a` and `mt-app-b`** | Two AZs |
| Load balancing | **No load balancer** for now | Debug the instance first |
| Group size | Desired 1, min 1, max 2 | One instance while you debug |
| Health checks | EC2 (switched to ELB in Part G) | |

When the instance is running:

1. **EC2** > the instance > **Connect** > **Session Manager**. If the tab is greyed out, wait a few minutes; if it stays so, see troubleshooting (role, NAT route, 443 egress).
2. In the session: `curl -s http://127.0.0.1:8080/health` should print `{"status":"ok"}`. If not: `sudo journalctl -u sole-atelier --no-pager | tail -50`.
3. Finish the RDS pause point (RDS guide sections 11, 15 to 19), then `sudo systemctl restart sole-atelier` and `curl -s http://127.0.0.1:8080/health/ready`.

**Evidence:** instance details showing **no public IPv4** and the attached role (E-010, E-011); Session Manager session (E-011); `E-008-ready-check.txt` (E-008).

## Part E: Target group and Application Load Balancer (CP5)

**Target group** (**EC2** > **Target groups** > **Create**):

| Setting | Value |
|---|---|
| Type | Instances |
| Name | `mt-app-tg` |
| Protocol / port | HTTP / **8080** |
| VPC | `mt-vpc` |
| Health check path | `/health` |
| Healthy threshold / interval | defaults are fine; shorten the interval only for faster lab feedback |
| Register targets | skip (the ASG registers them) |

**Load balancer** (**EC2** > **Load balancers** > **Create** > **Application Load Balancer**):

| Setting | Value | Reason |
|---|---|---|
| Name | `mt-alb` | |
| Scheme | **Internet-facing**, IPv4 | |
| VPC | `mt-vpc` | |
| Mappings | AZ a with **`mt-public-a`**, AZ b with **`mt-public-b`** | Public subnets only |
| Security group | `mt-alb-sg` (remove default) | |
| Listener | HTTP **80** forward to `mt-app-tg` | HTTP only (D-009) |

## Part F: Connect the ASG to the target group and scale to two (CP5)

1. **Auto Scaling groups** > `mt-app-asg` > **Load balancing** > **Edit** > attach `mt-app-tg`.
2. **Health checks** > enable **Elastic Load Balancing health checks**; set a health check grace period long enough for boot (several minutes; tune from what you observe).
3. **Group details** > set desired capacity 2.

**Verify:** target group **Targets** tab shows two targets, one per AZ, `healthy`. **Evidence:** `screenshots/03-compute/05-target-group-healthy.png`, `06-asg-two-instances.png` (E-009).

**What this proves and does not:** healthy targets prove the ALB can reach port 8080 and `/health` returns 200. They do **not** prove the database connection, the checkout path or the security of the database. Those need Part G.

## Part G: End-to-end validation (CP6)

Run the tests in [testing.md](testing.md) section "AWS validation": ALB DNS name in a browser (home, product, add to bag, demo checkout), a row in `orders` (E-008), the database unreachable from outside (E-007), instances not directly reachable (E-010), and the terminate-one-instance test (E-012). Capture evidence into `screenshots/07-validation/` as listed in [../screenshots/README.md](../screenshots/README.md).

## Part H: Teardown (CP7)

Follow the deletion order in [cost-analysis.md](cost-analysis.md). Delete the NAT gateway and release its Elastic IP first, because it is the most expensive idle resource in this design.

## Known limitations of this deployment design

HTTP only, no custom domain; single NAT; single-AZ database; no log shipping (application logs stay in the journal on the instance); no automated deploys (a new version means a new launch template version and an instance refresh by hand); secrets not rotated.
