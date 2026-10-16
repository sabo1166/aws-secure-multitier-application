# Interview questions and answers

Answers match the code and the evidence **as of today**. Each has a tag:

- **[Can say now]**: true and demonstrable from the local build (run the tests or the app to show it).
- **[After AWS evidence]**: only say it once the matching register row is VERIFIED with your own evidence. Until then say "my design is..., I have not deployed it yet".

Practise out loud in your own words. If you cannot explain a line, do not use it.

## Application and code

**1. Walk me through what happens when a customer clicks "Add to bag".** [Can say now]
The browser sends product id, size and quantity as JSON with a CSRF token header. The server validates the shape (Pydantic, unknown fields refused), loads the product from the database, checks the size exists and has stock, and checks the quantity against both stock and a per-line cap. It stores only ids and quantities in a signed session cookie and returns a cart that it priced from the database.

**2. How do you stop a customer changing the price?** [Can say now]
The cart cookie never holds prices, and the API refuses extra fields such as `price`. Every cart view and every order recomputes prices from the `products` table. There are tests that send a `price` field, that change a price in the database after adding to the bag, and that check order lines snapshot the price at purchase time.

**3. Two people want the last pair at the same moment. What happens?** [Can say now]
Stock is reserved with `UPDATE product_sizes SET stock = stock - :n WHERE ... AND stock >= :n` inside the order transaction. The database arbitrates: one update affects a row, the other affects none, and that request gets a 409 and rolls back every line. I tested it with a sequential two-buyer case and a simulated race. I have **not** load-tested real parallel requests, and I have only run it on SQLite so far.

**4. Why a cookie cart rather than a database cart?** [Can say now]
It needs no table, works across two instances behind a load balancer without sticky sessions (all instances share the signing key), and holds nothing sensitive. The costs: it is per browser, it is lost when cookies clear, and it is limited in size. A real shop would move carts server-side for signed-in customers.

**5. What stops a double-clicked "Place order" from creating two orders?** [Can say now]
The button disables on click, and the checkout form carries a client-generated idempotency key that is unique in the database. A repeat request returns the first order with 200 instead of creating another, and stock is decremented once. There is a test.

**6. How do you prevent SQL injection?** [Can say now]
Only SQLAlchemy expressions with bound parameters; no SQL strings are built from input. The search uses `icontains` with autoescape so `%` and `_` are literal. Tests send injection strings and wildcards.

**7. How do you prevent XSS and what does the CSP do?** [Can say now]
Jinja2 autoescapes output; a test puts `<script>` in an address and checks it is escaped. The Content-Security-Policy allows scripts and styles only from the site itself, and a test guards the templates against inline script or style so the policy keeps working.

**8. Explain CSRF in this app.** [Can say now]
The session holds a random token that pages expose in a meta tag; every POST/PATCH/DELETE must echo it in `X-CSRF-Token`, compared in constant time. A token from another session is rejected (tested). `SameSite=Lax` on the cookie is a second layer.

**9. Which HTTP methods and status codes do you use, and why?** [Can say now]
GET for reads, POST to add a cart item or create an order (201 on creation, 200 when an idempotent replay returns the existing one), PATCH to change a quantity, DELETE to remove a line. 404 unknown item or product, 409 conflicts such as sold out or empty cart, 422 validation, 403 CSRF, 503 when the database is unavailable.

**10. What does `/health` check, and why not the database?** [Can say now]
`/health` is liveness only; the load balancer uses it. `/health/ready` also runs `SELECT 1`. If the load balancer depended on the database, a short database outage would mark every instance unhealthy and a partial failure would become a total one. During an outage the app returns 503 on data pages while staying "alive". Tested locally with a simulated database failure; AWS behaviour not observed.

**11. How is configuration handled?** [Can say now]
Environment variables only. `APP_ENV=production` makes the app refuse a placeholder or short session secret, SQLite, or a missing database. Locally it falls back to SQLite so the project runs with no setup. Credentials are read from Secrets Manager at startup in AWS. The Secrets Manager call is unit tested with a fake client, not against AWS.

**12. What does the test suite not cover?** [Can say now]
MySQL (only SQLite so far), real concurrent load, other browsers or real devices, screen readers, security scanning of dependencies, and anything on AWS.

## AWS design (answer with "design" until you have evidence)

**13. Why a private subnet and what makes a subnet public?** [After AWS evidence: E-003, E-004]
A subnet is public only because its route table sends 0.0.0.0/0 to an internet gateway. The app and database subnets have no such route (app subnets reach out through a NAT gateway; db subnets have only the local route).

**14. Explain your security groups.** [After AWS evidence: E-005, E-007, E-010]
`alb-sg` allows 80 from the internet; `app-sg` allows 8080 only from `alb-sg`; `db-sg` allows 3306 only from `app-sg`. Referencing groups means a replacement instance is allowed automatically and nothing else is. Security groups are stateful, so replies need no rule. Egress is restricted too: the app tier may only reach the database and 443.

**15. How do you get a shell without SSH?** [After AWS evidence: E-011]
Session Manager: the instance role has the SSM managed policy, and the instance reaches the SSM service over 443 through the NAT. No inbound port, no key pair, and access is controlled by IAM.

**16. Why RDS is in private subnets and how do you prove it is not reachable from the internet?** [After AWS evidence: E-006, E-007]
Configuration: Publicly accessible No, db subnets without an internet route, `db-sg` allows only `app-sg`. Behaviour: a connection attempt from outside times out. The configuration alone does not prove it; the failed connection does.

**17. Why does the DB subnet group need two AZs for one instance?** [Can say now, from AWS docs]
AWS requires a DB subnet group to cover at least two AZs even for a single-AZ instance, which also keeps Multi-AZ possible later. My instance runs in one AZ, so the database is still a single point of failure.

**18. Which database account does the app use?** [After AWS evidence]
A dedicated `sole_app` user with SELECT, INSERT, UPDATE and DELETE only. Schema creation is a separate admin step with the password typed at a prompt. So a SQL injection bug could not drop tables. The app user still has write access to all tables, which is a documented limitation.

**19. Where is the database password and who can read it?** [After AWS evidence: E-013, E-011]
In Secrets Manager. The instance role can read only the two named secrets. It is not in code, user data or screenshots. It is not rotated (RDS rotates the admin secret by default; the app user's does not).

**20. What happens if AZ a fails?** [Design now, observed later]
Probably an outage: the NAT gateway and the RDS instance are both in AZ a. The two app instances in two AZs protect against one instance failing (E-012), not against losing AZ a. I chose that for cost and say so.

**21. Why is the NAT gateway created late and deleted first?** [Can say now]
It bills by the hour whether or not traffic flows, and I want the expensive resources to exist for the shortest validated window. I will quote prices only after looking them up.

**22. What would you change to make this production ready?** [Can say now]
HTTPS with ACM and a domain, WAF and rate limiting, Multi-AZ RDS and NAT per AZ, server-side carts and accounts, a payment provider so card data never touches my servers, migrations with Alembic, rotated application credentials, log shipping and alarms, automated dependency scanning, and infrastructure as code for repeatability. Doing these manually first was deliberate: I wanted to understand each piece before automating it.

**23. Why not Terraform or Docker?** [Can say now]
The project is a manual-console learning project (D-001). Automation comes after I can explain each resource. It is a deliberate scope decision, not an omission.

**24. A target group shows healthy. Is the application working?** [Can say now]
No. It proves the ALB reached port 8080 and `/health` returned 200. It says nothing about the database, the checkout flow or the security of any tier. That is why the register separates configuration from behaviour.

## Claims to avoid

"Deployed on AWS", "highly available", "production ready", "secure" without qualification, "tested with RDS", any statement about cost figures you have not looked up, or anything about users or traffic.
