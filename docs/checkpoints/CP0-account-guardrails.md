# CP0 Account guardrails

Status: **PLANNED**. Evidence: E-001, E-002 (see [../project/EVIDENCE_REGISTER.md](../project/EVIDENCE_REGISTER.md)).

AWS Console layouts change. Where I name a menu path, treat it as a guide and tell me if your screen differs; I have not been able to check these against a live Console.

## 1. Objective and why it matters

Make mistakes cheap and visible before building anything. A budget alert limits surprise cost; MFA on the root user protects the one identity that cannot be restricted; using a non-root identity daily means your normal work cannot close the account or change billing by accident. Choosing one Region now prevents resources hiding in another Region.

## 2. Console navigation

- **Region:** top-right Region selector (decide per D-002 first).
- **Root MFA:** account menu (top right) > **Security credentials** > **Multi-factor authentication (MFA)** > **Assign MFA device**.
- **Non-root identity:** either **IAM Identity Center** (recommended by AWS for people) or **IAM** > **Users** > **Create user**. Choose one and record it in DECISIONS (new entry D-012).
- **Budget:** **Billing and Cost Management** > **Budgets** > **Create budget**.

## 3. Configuration values and rationale

| Item | Value | Rationale |
|---|---|---|
| Root MFA | Authenticator app or passkey/security key | Phishing-resistant is better; any MFA beats none |
| Admin identity | One identity with the AdministratorAccess managed policy, MFA enabled | Broad for a personal lab; a known limitation, not a production pattern. Write that in QUALITY_REVIEW |
| Access keys | None for root. None for the lab identity | The Console needs none; keys leak |
| Budget type | Cost budget, monthly | Simple threshold alerting |
| Budget amount | A value you choose and can afford to lose | Your risk tolerance, not mine |
| Alert thresholds | Actual at 50% and 100%; Forecasted at 100% | Early warning, then a forecast warning |
| Alert email | Your own address | Must be monitored; an unread alert is no control |
| Billing access for IAM | Enable "IAM user and role access to Billing information" if you use a non-root identity | Otherwise a non-root identity cannot see costs (Account settings) |

## 4. Security and cost implications

- Security: root credentials are used only for tasks that require root. Store the root recovery method safely.
- Cost: budgets alert, they do not stop spending. Cost data lags. Check the Billing **Free Tier** page to see what your account actually includes; do not assume.

## 5. Expected result

Root has MFA. You sign in daily as the non-root identity. One budget exists with its notification email.

## 6. Verification procedure

1. Sign out, sign in as the non-root identity, and confirm the Console header shows that identity, not root.
2. Open Budgets, open the budget, and confirm thresholds and the email recipient.
3. Confirm the email subscription if AWS sent a confirmation or test message.
4. Confirm the Region selector shows the chosen Region.

## 7. Evidence to capture

- `E-001-budget-config.png` (budget details with thresholds, recipient email blurred).
- `E-002-root-mfa.png` (Security credentials page showing an assigned MFA device) and `E-002-nonroot-session.png` (Console header or account menu showing the non-root principal; account ID blurred).

Note what these do not prove: the budget screenshot does not prove an alert will arrive.

## 8. Common failures and diagnostics

| Symptom | Likely cause | Check |
|---|---|---|
| Non-root user sees "access denied" in Billing | IAM billing access not activated | Account settings, IAM access to billing information |
| No budget emails | Wrong address, spam folder, notification not saved | Open the budget, Edit, view alert recipients |
| MFA code rejected | Phone clock drift | Sync device time; re-register if needed |
| Resources not visible later | Wrong Region selected | Region selector |

## 9. Gate to move forward

Both E-001 and E-002 evidence reviewed by Claude and recorded as IMPLEMENTED (or VERIFIED once the sign-in test is shown). Region recorded in D-002.

## Interview prep

Explain in your own words: why not use root daily; what a budget can and cannot do; why the admin policy here is acceptable for a lab but not for a team.
