# RDS setup guide (Amazon RDS for MySQL, AWS Console)

**Status: PLANNED. Nothing in this guide has been executed.** It was written from the project's own design and from AWS documentation read on 2026-10-15. Console labels change, so treat menu names as a guide and note any mismatch in [troubleshooting.md](troubleshooting.md). Evidence this guide produces is tracked as E-006, E-007, E-008 and E-013 in [project/EVIDENCE_REGISTER.md](project/EVIDENCE_REGISTER.md).

Do this guide as **CP3**, after CP0 to CP2 are IMPLEMENTED. Steps that need the application instance (sections 11, 15 to 19) can only be finished after CP4 creates it; the guide says where to pause.

---

## 1. Why RDS is used in this project

Orders and stock are relational data (an order has many lines, stock must change atomically with an order). RDS gives a managed MySQL: automated backups, patching windows, encryption at rest and a security-group boundary, so the project can focus on networking and access control instead of operating a database server. The trade-off is cost: an RDS instance bills while it exists, even when idle. See [cost-analysis.md](cost-analysis.md).

## 2. How the application and database communicate

```
FastAPI on EC2 (app-sg)  --TCP 3306, TLS-->  RDS endpoint (db-sg)
```

- The application connects to the **RDS endpoint hostname**. Inside the VPC that name resolves to a private IP address. This is why the VPC needs DNS hostnames enabled (CP1).
- The only permitted path is `app-sg` to `db-sg` on TCP 3306 (CP2). There is no route to the internet from the db subnets and the instance is not publicly accessible.
- The application authenticates as a dedicated low-privilege MySQL user, `sole_app`, whose password lives in Secrets Manager. The master (admin) account is used only for one-off setup.

## 3. Prerequisites in the existing VPC

Check each item against your own screenshots before you start:

| Prerequisite | From | Check |
|---|---|---|
| Region chosen and selected in the console | D-002 | Region selector |
| VPC `mt-vpc`, DNS hostnames enabled | CP1 | VPC details |
| Subnets `mt-db-a` (10.0.20.0/24) and `mt-db-b` (10.0.21.0/24) in two different AZs | CP1 | Subnets list |
| Route table `mt-db-rt` with only the local route, associated with both db subnets | CP1 | Route table tabs |
| Security groups `mt-alb-sg`, `mt-app-sg`, `mt-db-sg` with the rules in CP2 | CP2 | Rule tabs |

If anything differs, fix it first. Do not "adjust" CIDRs or group names in this guide; they are the project's design values, not identifiers invented here.

## 4. Select the correct VPC

On the RDS create page, **Connectivity** has a VPC selector. Choose `mt-vpc`. **A DB instance's VPC cannot be changed after creation**, so a wrong choice means deleting and recreating the instance. Confirm the name and the CIDR 10.0.0.0/16 before continuing.

## 5. Create the DB subnet group

Console: **RDS** > **Subnet groups** > **Create DB subnet group**.

| Field | Value | Reason |
|---|---|---|
| Name | `mt-db-subnets` | Project prefix for easy cleanup |
| Description | `Private database subnets for SOLE ATELIER` | |
| VPC | `mt-vpc` | |
| Availability Zones | The two AZs of your db subnets | |
| Subnets | `mt-db-a` and `mt-db-b` only (check the CIDR column: 10.0.20.0/24, 10.0.21.0/24) | Never select a public or app subnet |

**Why two AZs for one instance:** AWS requires a DB subnet group to cover at least two Availability Zones, even for a single-AZ instance, and the API returns `DBSubnetGroupDoesNotCoverEnoughAZs` otherwise. The second subnet also leaves the door open to Multi-AZ later. Source: [Working with a DB instance in a VPC](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_VPC.WorkingWithRDSInstanceinaVPC.html), checked 2026-10-15.

**Evidence:** `screenshots/05-database/01-db-subnet-group.png` (E-006).

## 6. Choose a supported MySQL version

Choose the newest **MySQL 8.4** minor version offered as the default in the create wizard. Per the AWS version documentation checked on 2026-10-15, 8.4 is in standard support (end of standard support 31 July 2029), whereas **8.0 is already in Extended Support**, which is a paid add-on. Do not pick 8.0, and do not pick an older version just because it appears in the list. Re-check the [MySQL on Amazon RDS versions](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/MySQL.Concepts.VersionMgmt.html) page before you build, because these dates change.

## 7. Instance and storage for a learning lab

Console: **RDS** > **Databases** > **Create database** > **Standard create** > Engine **MySQL**.

| Setting | Learning-lab value | Reason |
|---|---|---|
| Templates | **Dev/Test** (or **Free tier** only if the console offers it for your account and you have read what it includes) | Avoids Multi-AZ by default. Do not assume free-tier eligibility |
| Availability and durability | **Single DB instance** | Cost (D-007). Not production-grade |
| DB instance identifier | `mt-sole-atelier-db` | |
| DB instance class | Smallest burstable class offered (for example a `db.t4g.micro` or `db.t3.micro`) | Cheapest adequate for a demo. Check current pricing |
| Storage type and size | General Purpose SSD, the minimum allocated size | Demo data is tiny |
| Storage autoscaling | **Disabled** | Prevents silent cost growth |
| Performance Insights, Enhanced Monitoring | **Off** | Avoids extra cost; basic CloudWatch metrics remain |
| Backup retention | Default or lowest value you accept; note the cost implication | Backups protect data but cost storage beyond the free allowance, so check the pricing page |
| Deletion protection | **Off for this lab** | You must be able to clean up; turn it **on** in production |

## 8. Disable public accessibility

Under **Connectivity**:

| Setting | Value |
|---|---|
| Compute resource | Don't connect to an EC2 compute resource (you attach the security group yourself) |
| Network type | IPv4 |
| VPC | `mt-vpc` |
| DB subnet group | `mt-db-subnets` |
| **Public access** | **No** |
| VPC security group | **Choose existing** > `mt-db-sg`; **remove the default group** |
| Availability Zone | No preference (or the AZ of `mt-db-a` to keep traffic in one AZ) |

Never set Public access to Yes to "make it connect". Connection errors have network causes, listed in section 20.

## 9. Enable encryption at rest

Under **Additional configuration** > **Encryption**, leave **Enable encryption** checked with the default AWS managed key (`aws/rds`). Encryption cannot be turned on later for an existing unencrypted instance without a snapshot copy and restore, so decide now. This protects the storage volume, snapshots and backups; it does not protect data from a user who can already log in to the database.

## 10. Configure credentials securely

Under **Credentials settings**:

- Master username: `admin` (a name you choose; do not use it in the app).
- Select **Manage master credentials in AWS Secrets Manager** with the default encryption key. RDS creates and rotates the master password for you; you never type or see it unless you retrieve it deliberately. By default RDS rotates it every seven days. Secrets Manager storage has a cost, so check the [pricing page](https://aws.amazon.com/secrets-manager/pricing/). Source: [Password management with Amazon RDS and AWS Secrets Manager](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-secrets-manager.html), checked 2026-10-15.

Under **Additional configuration** set **Initial database name** to `sole_atelier`. Leave the rest at defaults (port 3306, default parameter group for now, you change TLS enforcement in section 12).

Create the database. Creation takes several minutes. **Evidence:** `screenshots/05-database/02-rds-config-connectivity.png` showing Public access No, the VPC, the subnet group and the security group (E-006). Do not capture the Credentials or endpoint area unredacted.

**Why this matters for E-013:** no database password is typed into any file, user data or screenshot.

## 11. Create the application database user

> **Pause point.** This needs the application instance from CP4 (Session Manager shell) and its outbound path. Return here after CP4.

The application must not use the admin account. Create a user that can only read and write data:

1. In **Secrets Manager**, open the RDS-managed secret (its name starts with `rds!db-`) > **Retrieve secret value**. You will paste the admin password at a prompt in step 3, so keep that page open privately; never paste it into chat or a file.
2. On the app instance (Session Manager), generate the application user's password and keep it in the terminal only for the next minute:
   ```bash
   openssl rand -hex 24
   ```
   Hexadecimal output avoids characters that need escaping in SQL.
3. Connect as admin with TLS (client install and CA bundle are in sections 15 and 18) and run, replacing the placeholder with the generated value:
   ```sql
   CREATE USER 'sole_app'@'%' IDENTIFIED BY '<generated-password>' REQUIRE SSL;
   GRANT SELECT, INSERT, UPDATE, DELETE ON sole_atelier.* TO 'sole_app'@'%';
   ```
   `'%'` is acceptable because `db-sg` already limits who can reach port 3306. `REQUIRE SSL` forces TLS for this account.
4. In **Secrets Manager** > **Store a new secret** > **Other type of secret**, add key/value pairs `username` = `sole_app` and `password` = the generated value. Name it `sole-atelier/db-app`. Leave rotation off (a documented limitation) and default encryption.
5. Create a second secret `sole-atelier/session` with one pair, `session_secret` = the output of `openssl rand -base64 48` (at least 32 characters). Both instances read it, so their cookies are interchangeable.
6. Clear the terminal (`clear`) and close the retrieved-password page.

Notes: the `sole_app` user has no `CREATE`, `ALTER` or `DROP`, so a SQL injection bug could not drop tables. Creating the tables is a separate admin step (section 17).

## 12. Configure the RDS security group

`mt-db-sg` was built in CP2. Confirm:

| Direction | Rule |
|---|---|
| Inbound | TCP 3306, **source `mt-app-sg`** (a security group, not a CIDR) |
| Outbound | none |

Also require encrypted connections: **RDS** > **Parameter groups** > **Create parameter group** (family `mysql8.4`) > edit `require_secure_transport` = `1` > then **Databases** > your instance > **Modify** > DB parameter group = the new one. By default RDS for MySQL has this parameter OFF; changing it needs no reboot on a dynamic parameter ([AWS docs](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/mysql-ssl-connections.require-ssl.html), checked 2026-10-15). The `REQUIRE SSL` on the user is a second layer.

## 13. Allow inbound TCP 3306 only from the application security group

This is the single inbound rule above. **Evidence:** `screenshots/04-security/03-db-sg-rules.png` (E-005, CP2). To prove it works and nothing else does, see the negative tests in [testing.md](testing.md) (E-007).

## 14. Retrieve the RDS endpoint

**RDS** > **Databases** > `mt-sole-atelier-db` > **Connectivity & security** > **Endpoint**. It looks like `<identifier>.<random>.<region>.rds.amazonaws.com`. Use it as `DB_HOST`. The endpoint is not a secret, but redact it in published screenshots anyway; it names your account's resource.

## 15. Configure the application's environment variables

Nothing sensitive goes in this file. It holds names and ARNs, not passwords:

```bash
APP_ENV=production
DB_HOST=<rds-endpoint-hostname>
DB_PORT=3306
DB_NAME=sole_atelier
DB_SECRET_ARN=<arn of sole-atelier/db-app>
SESSION_SECRET_ARN=<arn of sole-atelier/session>
AWS_REGION=<your region>
DB_SSL_CA=/opt/sole-atelier/global-bundle.pem
SESSION_HTTPS_ONLY=false
```

The full list with comments is in [../.env.example](../.env.example). `SESSION_HTTPS_ONLY=false` is required while the site is HTTP-only (browsers do not send `Secure` cookies over HTTP); set it to `true` when HTTPS is added.

Download the RDS CA bundle on the instance (needs outbound 443 through the NAT gateway; confirm the URL on the [AWS SSL/TLS page](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.SSL.html)):

```bash
sudo mkdir -p /opt/sole-atelier
sudo curl -fsS -o /opt/sole-atelier/global-bundle.pem https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
```

## 16. Install the Python dependencies

The launch template's user data (deployment guide, Part C) already creates `/opt/sole-atelier/venv` and runs `pip install -r requirements.txt` from the cloned repository, so you normally have nothing to do here. To redo it by hand:

```bash
sudo -u soleapp /opt/sole-atelier/venv/bin/pip install -r /opt/sole-atelier/repo/requirements.txt
```

Either way this needs outbound 443 to the Python package index through the NAT gateway. **Unverified:** which Python version Amazon Linux 2023 provides and whether it supports the pinned dependency versions. The project was tested on Python 3.13 locally; check `python3 --version` and install a suitable newer package from the OS repositories if needed. Record the result in [troubleshooting.md](troubleshooting.md).

## 17. Run schema initialization safely

`backend.init_db` only creates tables that do not exist. It never alters or drops anything. Run it once as the admin user, typing the password at the prompt (`getpass` does not echo or store it).

A Session Manager shell runs as `ssm-user`, which cannot read `/etc/sole-atelier.env` (it is `root:soleapp`, mode 640), so run the command as the service account and load that file first:

```bash
sudo -u soleapp bash -c 'set -a; . /etc/sole-atelier.env; set +a; cd /opt/sole-atelier/repo && /opt/sole-atelier/venv/bin/python -m backend.init_db --admin-user admin --seed'
```

The prompt asks for the admin password; paste it from the Secrets Manager page (section 11). It connects with the RDS CA bundle named by `DB_SSL_CA`. **Unverified:** this exact command has not been run; if the interactive prompt does not appear through `sudo`, record what happened in [troubleshooting.md](troubleshooting.md).

Use `--seed` only for the demo catalogue; it inserts products only when the table is empty. After this, the application runs as `sole_app` with no schema rights. Because the grant in section 11 covers `sole_atelier.*`, the new tables are already usable.

**Production note:** there is no migration tool (D-015). Schema changes after launch need a proper migration process such as Alembic, plus a backup and rollback plan.

## 18. Test database connectivity

1. From the app instance (the CA bundle path is readable by all users), TLS check with the MySQL client (package name on AL2023 is usually `mariadb105`; run `dnf search mariadb` to confirm):
   ```bash
   mysql -h <endpoint> -u sole_app -p --ssl-ca=/opt/sole-atelier/global-bundle.pem --ssl-verify-server-cert -e "SELECT 1"
   ```
   Client flags differ by version (`--ssl-mode=VERIFY_IDENTITY` on newer MySQL clients). Success prints `1`.
2. Confirm the application's own check: `curl -s http://127.0.0.1:8080/health/ready` should return `{"status":"ok","database":"ok"}`.
3. Negative checks (E-007): from a machine outside the VPC, `nc -vz <endpoint> 3306` must time out. And `sole_app` must fail to `DROP TABLE` or `CREATE TABLE`.

**Evidence:** `evidence/redacted/E-008-ready-check.txt` (command and output), `screenshots/07-validation/` entries listed in [../screenshots/README.md](../screenshots/README.md).

## 19. Create and retrieve a demonstration order

Through the ALB (after CP5) place a demo order in a browser, then on the app instance as `sole_app`:

```sql
SELECT id, public_id, status, total, created_at FROM sole_atelier.orders ORDER BY id DESC LIMIT 3;
SELECT order_id, product_name, size, quantity, unit_price, line_total FROM sole_atelier.order_items ORDER BY id DESC LIMIT 5;
```

A row whose total matches the confirmation page proves the full path browser, ALB, app, RDS. A healthy target group alone does **not** prove this. **Evidence:** a screenshot of the confirmation page and the query result, with customer fields masked (E-008).

## 20. Troubleshooting common connection and permission errors

| Symptom | Likely cause | What to check |
|---|---|---|
| Connection **timed out** | Security group or routing, not credentials | `db-sg` inbound rule source is `mt-app-sg` (not a CIDR), the instance really has `mt-app-sg`, correct VPC and endpoint, `app-sg` outbound allows 3306 to `db-sg` |
| `Unknown MySQL server host` | DNS or typo | DNS hostnames enabled in the VPC, endpoint copied fully |
| `Access denied for user` | Wrong user/password or host pattern | Secret value matches the MySQL user; user was created with `'%'`; TLS options |
| `Connections using insecure transport are prohibited` (error 3159) | `require_secure_transport` is ON and the client did not use TLS | Pass the CA bundle; the app does this via `DB_SSL_CA` |
| `SSL connection error` / certificate verify failed | Missing or wrong CA bundle | Re-download `global-bundle.pem`; check `DB_SSL_CA` path and read permission |
| `Table ... doesn't exist` | Schema not initialised | Run section 17 |
| `INSERT command denied` / `CREATE command denied` | Expected for `CREATE`; for `INSERT` the grant is missing | `SHOW GRANTS FOR 'sole_app'@'%'` |
| Instance creation fails with subnet group error | Subnet group has one AZ | Section 5 |
| App says 503 `database_unavailable`, `/health` is OK | Database unreachable but app alive (by design) | Same checks as "timed out"; look at the app log (`journalctl -u sole-atelier`) |

**Never** fix a timeout by making the instance public or opening 3306 to `0.0.0.0/0`.

## 21. Estimating costs and cleaning up

Chargeable here: the RDS instance (hourly), its storage and backups, the Secrets Manager secrets. Look up the current prices on the AWS pricing pages and record the date you looked in [cost-analysis.md](cost-analysis.md); this guide deliberately quotes none.

Clean up when you are finished (full order in [cost-analysis.md](cost-analysis.md)):

1. **RDS** > select the instance > **Actions** > **Delete**. For a lab you may decline the final snapshot and automated-backup retention; read the confirmation carefully because that choice is permanent. Deletion protection must be off first.
2. Delete the DB subnet group `mt-db-subnets` and any custom parameter group.
3. Delete the secrets (`sole-atelier/db-app`, `sole-atelier/session`). Secrets Manager schedules deletion after a recovery window; check the console for the current minimum and whether billing continues during it.
4. Verify in **RDS** (Databases, Snapshots, Subnet groups) that nothing remains, in the same Region you built in.

## Learning configuration versus production-ready

| Topic | This learning lab | A production ecommerce database |
|---|---|---|
| Availability | Single instance, single AZ | Multi-AZ with tested failover |
| Backups | Default retention, restore never tested | Chosen retention, regularly tested restores, point-in-time recovery |
| Credentials | Static app password, no rotation | Rotated app credentials, short-lived access where possible |
| Schema changes | `create_all`, no migrations | Versioned migrations with rollback |
| Observability | Basic metrics only | Alarms, slow-query logging, audit logging |
| Payment and personal data | None collected beyond a demo name and address | PCI scope handled by a payment provider, data-protection obligations, retention policy |
| Network | Single NAT, HTTP only | Redundant egress, TLS end to end, WAF |
