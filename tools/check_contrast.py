"""Compute WCAG 2.x contrast ratios for the storefront's real colour pairs (values taken from frontend/static/css/site.css).

    python tools/check_contrast.py

AA needs 4.5:1 for normal text, 3:1 for large text and for UI component boundaries/focus indicators.
This checks colour pairs only. It is not a full accessibility audit.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

CSS = Path(__file__).resolve().parent.parent / "frontend" / "static" / "css" / "site.css"


def tokens() -> dict[str, str]:
    root = re.search(r":root\s*\{(.*?)\}", CSS.read_text(encoding="utf-8"), re.S).group(1)
    return {k: v.strip() for k, v in re.findall(r"--([\w-]+):\s*([^;]+);", root)}


def lum(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(a: str, b: str) -> float:
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def main() -> int:
    t = tokens()
    pairs = [
        ("Body text: ivory on background", t["ivory"], t["bg"], 4.5),
        ("Body text: ivory on panel", t["ivory"], t["panel"], 4.5),
        ("Muted text on background", t["muted"], t["bg"], 4.5),
        ("Muted text on panel", t["muted"], t["panel"], 4.5),
        ("Muted text on footer (#08090a)", t["muted"], "#08090a", 4.5),
        ("Champagne eyebrow/link on background", t["champagne"], t["bg"], 4.5),
        ("Champagne on panel", t["champagne"], t["panel"], 4.5),
        ("Error text on background", t["danger"], t["bg"], 4.5),
        ("Primary button: dark text on ivory", t["bg"], t["ivory"], 4.5),
        ("Primary button hover: dark text on champagne", t["bg"], t["champagne"], 4.5),
        ("Focus ring (blue) against background (UI, 3:1)", t["blue"], t["bg"], 3.0),
        ("Focus ring (blue) against panel (UI, 3:1)", t["blue"], t["panel"], 3.0),
    ]
    failed = 0
    for name, fg, bg, need in pairs:
        r = ratio(fg, bg)
        ok = r >= need
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {r:5.2f}:1 (needs {need})  {name}  [{fg} on {bg}]")
    print(f"\n{len(pairs) - failed}/{len(pairs)} pairs meet WCAG AA")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
