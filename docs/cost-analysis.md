# Cost analysis and cleanup

**This file deliberately contains no prices.** AWS prices and free-tier rules change, and quoting them from memory would be unreliable. You look each one up on the day you build, write the date in the table, and decide whether you accept the cost. Nothing has been created yet, so the project has cost nothing so far.

## What costs money in this design

| Resource | Billed by (qualitatively) | Created in | Delete in | Price page (verify the link) | Price checked (date, region) |
|---|---|---|---|---|---|
| NAT gateway | Per hour it exists, plus per GB processed | CP4 | **First** at teardown | <https://aws.amazon.com/vpc/pricing/> | |
| Public IPv4 addresses (NAT's Elastic IP, ALB nodes) | Per hour per address; AWS charges for public IPv4 | CP4, CP5 | With their owners | VPC pricing page, "Public IPv4 Address" | |
| Application Load Balancer | Per hour plus capacity units | CP5 | Early at teardown | <https://aws.amazon.com/elasticloadbalancing/pricing/> | |
| RDS for MySQL instance | Per hour, plus storage, plus backup storage beyond the free allowance | CP3 | After the above | <https://aws.amazon.com/rds/mysql/pricing/> | |
| EC2 instances and EBS volumes | Per second the instance runs, plus provisioned storage | CP4, CP5 | Via the ASG | <https://aws.amazon.com/ec2/pricing/on-demand/> | |
| Secrets Manager secrets | Per secret per month plus per API calls | CP3 | With a recovery window | <https://aws.amazon.com/secrets-manager/pricing/> | |
| Data transfer | Out to the internet and across AZs, per GB | Always | n/a | EC2 pricing, "Data Transfer" | |
| CloudWatch | Not used beyond default metrics | | | | |

Free: VPC, subnets, route tables, internet gateway, security groups, IAM, budgets (the first budgets), Session Manager use.

## Cost control rules

1. **Budget first (CP0).** An alert is a notification, not a cap. Confirm the email arrives.
2. **Time-box the expensive layer.** Build NAT, ALB and RDS in one session when you can finish validation the same day, capture evidence, then tear down. Build the free layers (CP0 to CP2) at leisure.
3. **One Region.** Do everything in the Region you chose in D-002, and check that same Region at teardown.
4. **Before you stop for the night, ask:** is a NAT, ALB, RDS or EC2 instance still running? If yes and you are not working, delete or stop what can be stopped. (A stopped RDS instance restarts automatically after a limited number of days and still bills for storage. Check the current rule rather than relying on it.)
5. **Look at the bill the next day.** Billing data lags, so a zero today does not prove zero tomorrow (E-014).

## Teardown order (CP7)

Delete in this order so dependencies release cleanly and the costliest items go first. Take screenshots of the final empty lists as evidence.

1. **Auto Scaling group** `mt-app-asg` (this terminates the instances). Then the launch template.
2. **Load balancer** `mt-alb`, then the target group `mt-app-tg`.
3. **NAT gateway** `mt-nat-a`, wait for it to show deleted, then **release the Elastic IP**.
4. **RDS instance** (decline snapshots only if you are certain), then DB subnet group and any parameter group.
5. **Secrets** (`sole-atelier/db-app`, `sole-atelier/session`; note the scheduled-deletion window and whether it bills).
6. **IAM role** `mt-app-role` (and its instance profile).
7. **Security groups**: `mt-alb-sg`, `mt-app-sg`, `mt-db-sg` (delete rules referencing each other first if needed).
8. **VPC pieces**: route table associations, the custom route tables, the internet gateway (detach, then delete), subnets, then the VPC.
9. **Verify per service in the build Region:** EC2 (instances, volumes, Elastic IPs, load balancers), VPC (NAT gateways, endpoints), RDS (databases, snapshots), Secrets Manager. Keep the budget.

## Estimating before you build

Write the numbers yourself so you can defend them: hours you expect each resource to exist, multiplied by the hourly price you looked up, plus storage. Put the result and the date in the table above. A quick answer to "why is this lab not free" is: the NAT gateway, ALB and RDS instance bill by the hour even when idle.
