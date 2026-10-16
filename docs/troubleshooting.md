# Troubleshooting

Three parts: problems that were **actually hit and fixed during the local build** (real), a log for **your** AWS problems (empty on purpose), and **likely** problems by area (predicted from the design, not yet observed). Do not move anything from "likely" to "observed" until you have seen it and have evidence.

## Method (use this order every time)

1. State the symptom exactly (error text, status code, which step).
2. Locate the layer: DNS, route, security group, instance, process, application, database.
3. Prove or disprove one hypothesis at a time with a read-only check.
4. Fix one thing, re-test the original symptom, and write down cause, fix and evidence.

## 1. Issues found and fixed during the local build (real)

| Problem | How it showed up | Cause | Fix |
|---|---|---|---|
| Importing the app created a database file | A test run left `sole_atelier.db` behind | A module-level `app = create_app()` ran on import | Removed it. The app is a factory: `uvicorn backend.main:create_app --factory`. Importing is now side-effect free |
| Hero shoe overlapped the buttons and was clipped | Visual review of the desktop screenshot | Illustration drawn too large for the crop | Regenerated the art smaller and positioned right (`scripts/generate_product_art.py`) |
| Product cards had the shoe floating in empty space | Visual review | Portrait 4:5 crop of a side-on shoe | Square artwork and 1:1 cards |
| Mobile screenshot looked broken (text cut off) | Headless browser screenshot at 390 px | The browser enforces a minimum window width, so the capture was a cropped wider layout, not a real narrow viewport | Wrote `tools/capture-screenshot.mjs`, which uses real device-metrics emulation, and added an overflow check |
| Test claimed the empty cart page returns 503 during a database outage | `assert 200 == 503` | Test was wrong: an empty cart never queries the database | Test now uses `/collections`, which does |
| Validation errors read like library output | "value is not a valid email address: An email address must have an @-sign" | Raw Pydantic messages | Friendly messages that never echo the submitted value |
| Race-condition test was fragile | Counting `execute` calls broke whenever SQLAlchemy issued internal selects | Counted the wrong thing | Count only UPDATE statements |
| Stock guard was covered by only one test | Mutation check (remove the guard) failed just one test | Thin coverage of the oversell path | Kept as a noted weakness; the race and two-buyer tests cover it from different angles |

## 2. Your AWS issue log (fill in as you go)

Record only things you really hit. Keep the evidence file path.

| Date | Step | Symptom (exact) | Cause (proved how) | Fix | Evidence |
|---|---|---|---|---|---|
| | | | | | |

## 3. Likely problems by area (predicted, not yet observed)

### Networking and security groups

| Symptom | Check |
|---|---|
| Subnet unexpectedly reaches the internet | Which route table is associated? A subnet with no explicit association uses the main table |
| Cannot reach anything from a private instance | `mt-app-rt` has `0.0.0.0/0` to the NAT gateway; NAT is in a **public** subnet with an Elastic IP; `app-sg` allows outbound 443 |
| Rule will not save | Referenced group is in a different VPC |
| Target group unhealthy, "Request timed out" | `app-sg` inbound 8080 from `alb-sg`; `alb-sg` outbound 8080 to `app-sg`; the process listens on 8080 on `0.0.0.0` |
| Target unhealthy with a 4xx/5xx code | Health check path must be `/health` and return 200; read `journalctl -u sole-atelier` |

### Session Manager

| Symptom | Check |
|---|---|
| Connect > Session Manager is greyed out | Instance profile attached with `AmazonSSMManagedInstanceCore`; instance can reach SSM endpoints over 443 through the NAT; wait a few minutes after launch |

### Bootstrap (user data)

| Symptom | Check |
|---|---|
| Service never started | `sudo cat /var/log/cloud-init-output.log`, then `sudo systemctl status sole-atelier` and `journalctl -u sole-atelier` |
| `dnf` or `pip` hangs | No outbound path: NAT, route, or `app-sg` egress 443 |
| `git clone` fails | Repository private, URL wrong, or no outbound 443 |
| `No matching distribution` from pip | Python version on the AMI does not match the pinned requirements |
| App fails at start with a secrets error | Role lacks `GetSecretValue` on that exact ARN, wrong Region in `AWS_REGION`, or the secret does not exist yet |

### Load balancer and Auto Scaling

| Symptom | Check |
|---|---|
| ALB DNS name times out | `alb-sg` inbound 80 from `0.0.0.0/0`; ALB is internet-facing in the **public** subnets |
| 502/503 from the ALB | No healthy targets, or the app is crashing; check the target group |
| ASG keeps replacing instances | Health check grace period shorter than boot time |
| Cart seems to empty between requests | Instances use different session keys (check both read the same `SESSION_SECRET_ARN` secret) |

### Database

See the troubleshooting table in [rds-setup-guide.md](rds-setup-guide.md) (section 20).

### Application

| Symptom | Check |
|---|---|
| 403 on every cart/checkout call | Browser blocked cookies, or CSRF token missing; reload the page to get a fresh token |
| Add to bag says size not offered or sold out | The server is authoritative; the page may be stale, reload |
| Checkout 409 "just sold out" | Stock changed between bag and order; this is the designed race handling |
| `/health` OK but pages return 503 | Database unreachable; `/health/ready` confirms |
