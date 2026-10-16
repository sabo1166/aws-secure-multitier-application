# Evidence rules

Where evidence lives:

| Folder | Holds | Published? |
|---|---|---|
| `raw/` | Original screenshots and terminal output, straight from the Console or terminal | **Never.** Git-ignored. May contain account IDs, ARNs, IPs, emails |
| `redacted/` | Redacted **text** evidence: pytest output, command output, health checks | Yes, after you read it once more |
| [`../screenshots/`](../screenshots/README.md) | Redacted **images**, organised by area with numbered names | Yes, after redaction |

Every evidence file is tied to a row in [`docs/project/EVIDENCE_REGISTER.md`](../docs/project/EVIDENCE_REGISTER.md). A file that no row refers to is clutter; a row marked VERIFIED without a file is a lie, and `node tools/check-docs.mjs` rejects it.

## Naming

- Text: `evidence/redacted/E-<id>-<short-description>.txt`, with the command on the first line and a date. Example: `E-015-pytest-output.txt`.
- Images: `screenshots/<area>/NN-short-description.png` using the names in the screenshots checklist.

## What a good screenshot contains

1. The Region selector visible.
2. The resource name and the specific tab that shows the setting (the **Routes** tab and the **Subnet associations** tab are two screenshots).
3. The browser time or console clock if the evidence is a test result.
4. No full-screen captures with unrelated tabs or personal data.

## Redaction checklist (before copying out of `raw/`)

- [ ] 12-digit account ID (also inside ARNs and URLs)
- [ ] Email addresses
- [ ] Public IP addresses, Elastic IPs, the ALB DNS name if you prefer
- [ ] RDS endpoint and secret ARNs
- [ ] Any secret value, password or access key (if one appears, stop and tell Claude; it must be rotated)
- [ ] Names, emails and addresses in database rows
- [ ] Resource IDs (`vpc-...`, `sg-...`) are not secrets, but blur them if unsure

## Text evidence

Command output goes in a `.txt` file, copied exactly, with the command on the first line. Do not paste outputs into chat that contain secrets.

## Who produced it

State it in the register row. Rows E-015 to E-018 and E-020 to E-023 were produced by Claude running the local build; every AWS row must be produced by you. Nobody fabricates evidence; a missing screenshot stays `PENDING`.
