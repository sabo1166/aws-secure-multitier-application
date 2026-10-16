"""Does the test suite notice when important behaviour is broken?

Applies each deliberate bug below to the source, runs the tests, and restores the file (always, even
on Ctrl-C). A mutation is "caught" if at least one test fails. A surviving mutation means a gap in
the tests.

    python tools/mutation_check.py

Run from the project root with the virtual environment active. It edits files in backend/ temporarily;
do not run it while the dev server is auto-reloading.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MUTATIONS = [
    ("Stock guard removed (allows overselling)", "backend/services/orders.py",
     "                    ProductSize.stock >= line.quantity,", "                    ProductSize.stock >= 0,"),
    ("CSRF check disabled", "backend/security.py",
     "    if not expected or not hmac.compare_digest(expected, supplied):", "    if False:"),
    ("Quantity ignored when pricing a line", "backend/services/cart.py",
     "line.line_total = (line.unit_price * qty).quantize(CENT)", "line.line_total = (line.unit_price * 1).quantize(CENT)"),
    ("Price snapshot replaced by a live lookup of zero", "backend/services/orders.py",
     "                    unit_price=line.unit_price,", "                    unit_price=0,"),
    ("Inactive products shown in the shop", "backend/services/catalog.py",
     "stmt = select(Product).where(Product.is_active.is_(True)).options(selectinload(Product.sizes))\n    q = q.strip()",
     "stmt = select(Product).options(selectinload(Product.sizes))\n    q = q.strip()"),
    ("Order confirmation visible to anyone with the reference", "backend/routes/pages.py",
     '    if public_id not in request.session.get("orders", []):', "    if False:"),
]


def run_tests() -> tuple[bool, str]:
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-x"], cwd=ROOT, capture_output=True, text=True)
    last = [l for l in proc.stdout.strip().splitlines() if l.strip()][-1] if proc.stdout.strip() else "no output"
    return proc.returncode != 0, last


def main() -> int:
    ok, baseline = run_tests()
    if ok:
        print(f"Baseline tests already failing, fix first: {baseline}")
        return 2
    print(f"Baseline: {baseline}\n")
    survived = 0
    for name, rel, old, new in MUTATIONS:
        path = ROOT / rel
        original = path.read_text(encoding="utf-8")
        if old not in original:
            print(f"SKIP  {name}: pattern not found in {rel} (update the tool)")
            survived += 1
            continue
        try:
            path.write_text(original.replace(old, new, 1), encoding="utf-8")
            caught, last = run_tests()
        finally:
            path.write_text(original, encoding="utf-8")
        print(f"{'CAUGHT  ' if caught else 'SURVIVED'}  {name}  [{last}]")
        survived += not caught
    ok, after = run_tests()
    print(f"\nAfter restoring files: {after}")
    print(f"{len(MUTATIONS) - survived}/{len(MUTATIONS)} mutations caught")
    return 1 if survived or ok else 0


if __name__ == "__main__":
    sys.exit(main())
