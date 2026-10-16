"""Generate the original product illustrations and hero art (SVG).

These are ORIGINAL vector illustrations drawn by this script, not photographs. They stand in for
product photography, which must be supplied separately before a real launch (see docs/assets.md).

    python scripts/generate_product_art.py
"""
from __future__ import annotations

import math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "frontend" / "static" / "images"

# Silhouette outlines in a local 800x520 space, toe pointing right.
UPPER = {
    "low": "M120,352 C108,320 106,262 118,214 C124,194 142,186 160,190 C196,198 216,226 250,222 C280,218 296,184 322,174 C350,164 372,176 400,198 C440,232 500,250 560,268 C640,292 722,306 748,340 C754,348 754,352 752,352 Z",
    "high": "M120,352 C108,300 106,190 120,108 C126,88 148,80 174,86 C214,96 238,128 272,132 C300,132 312,150 336,160 C366,172 392,186 420,206 C460,236 510,252 564,268 C640,292 722,306 748,340 C754,348 754,352 752,352 Z",
    "runner": "M118,334 C106,300 104,246 116,206 C122,188 140,180 160,184 C196,192 216,218 252,214 C282,210 298,190 330,184 C372,178 410,200 450,226 C500,256 580,276 650,300 C712,322 744,338 752,364 L118,334 Z",
}
SOLE = {
    "low": "M104,352 L752,352 L752,372 C752,404 720,424 690,424 L170,424 C128,424 104,404 104,372 Z",
    "high": "M104,352 L752,352 L752,372 C752,404 720,424 690,424 L170,424 C128,424 104,404 104,372 Z",
    "runner": "M96,330 L752,364 L752,392 C752,424 724,442 690,442 L166,442 C120,442 96,420 96,388 Z",
}
TOECAP = {
    "low": "M588,276 C650,296 722,308 748,340 L752,352 L600,352 C590,320 588,296 588,276 Z",
    "high": "M588,276 C650,296 722,308 748,340 L752,352 L600,352 C590,320 588,296 588,276 Z",
    "runner": "M610,290 C672,310 736,326 752,364 L636,358 C624,332 616,312 610,290 Z",
}
HEEL = {
    "low": "M120,352 C108,320 106,262 118,214 C124,196 140,190 150,192 L190,196 C176,250 176,310 182,352 Z",
    "high": "M120,352 C108,300 106,190 120,108 C126,90 144,84 158,86 L198,92 C180,170 176,280 184,352 Z",
    "runner": "M118,334 C106,300 104,246 116,206 C122,190 138,184 150,186 L192,194 C178,248 178,300 186,338 Z",
}
STRIPE = {
    "low": "M230,332 C330,322 430,302 520,270 L528,284 C436,318 336,342 232,352 Z",
    "high": "M230,332 C330,322 430,302 520,270 L528,284 C436,318 336,342 232,352 Z",
    "runner": "M214,326 C320,316 440,290 560,282 L566,296 C446,306 330,336 216,344 Z",
}
LACE_LINE = {"low": ((332, 184), (520, 252)), "high": ((346, 168), (524, 250)), "runner": ((338, 192), (500, 240))}
CENTER = {"low": (426, 262), "high": (426, 254), "runner": (424, 266)}

COLORWAYS = {
    "noir-01": dict(sil="low", up=("#1b1c21", "#0b0c0f"), sole=("#4a4a50", "#2a2b30"), cap="#16171b", heel="#101114", stripe="#c9b18a", lace="#d8d2c5", edge="#ffffff"),
    "chrome-runner": dict(sil="runner", up=("#dfe3e8", "#8a9099"), sole=("#f1efe9", "#cfcbc2"), cap="#a9afb7", heel="#7b818a", stripe="#2f6bff", lace="#f4f4f2", edge="#ffffff", mesh=True),
    "atelier-low": dict(sil="low", up=("#f3eee3", "#d6cdb9"), sole=("#faf6ec", "#e2dac8"), cap="#e6dfcf", heel="#cbbfa6", stripe="#b89b6a", lace="#fbf8f0", edge="#ffffff"),
    "monolith-high": dict(sil="high", up=("#34363c", "#17181b"), sole=("#efe9dc", "#d3ccbb"), cap="#202125", heel="#141518", stripe="#c9b18a", lace="#cfc9bd", edge="#ffffff"),
    "velocity-form": dict(sil="runner", up=("#3a3c42", "#1a1b1f"), sole=("#f0ebe0", "#cdc6b4"), cap="#e9e3d6", heel="#2a2c31", stripe="#2f6bff", lace="#ece7dc", edge="#ffffff", mesh=True),
    "studio-04": dict(sil="low", up=("#c4baa7", "#938875"), sole=("#f3eee3", "#d8d0bd"), cap="#aea38f", heel="#857a68", stripe="#5b5447", lace="#f1ece1", edge="#ffffff"),
}


SOLE_BOTTOM = {"low": 424, "high": 424, "runner": 442}
COLLAR = {"low": (205, 208, 54, 12, 20), "high": (214, 108, 56, 12, 26), "runner": (206, 202, 54, 12, 18)}


def shoe(cw: dict) -> str:
    """One sneaker with studio lighting, material grain, stitching, eyelets and a layered sole (all vector)."""
    sil = cw["sil"]
    (x1, y1), (x2, y2) = LACE_LINE[sil]
    ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
    span = math.hypot(x2 - x1, y2 - y1)
    base, shade, hi, eyelets = [], [], [], []
    for i in range(6):
        t = (i + 0.5) / 6
        x, y = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
        ax, ay, bx, by = x - 16, y + 14, x + 16, y - 14
        shade.append(f'<line x1="{ax:.0f}" y1="{ay + 3:.0f}" x2="{bx:.0f}" y2="{by + 3:.0f}"/>')
        base.append(f'<line x1="{ax:.0f}" y1="{ay:.0f}" x2="{bx:.0f}" y2="{by:.0f}"/>')
        hi.append(f'<line x1="{ax + 3:.0f}" y1="{ay - 2:.0f}" x2="{bx - 3:.0f}" y2="{by - 2:.0f}"/>')
        for ex, ey in ((ax - 2, ay + 1), (bx + 2, by - 1)):
            eyelets.append(f'<circle cx="{ex:.0f}" cy="{ey:.0f}" r="4.6" fill="#0a0a0c" stroke="{cw["lace"]}" stroke-opacity=".45" stroke-width="1.4"/>')
    mesh = ""
    if cw.get("mesh"):
        mesh = '<g clip-path="url(#up)" opacity=".28"><rect x="300" y="170" width="460" height="200" fill="url(#mesh)"/></g>'
    sb = SOLE_BOTTOM[sil]
    ccx, ccy, crx, cry, crot = COLLAR[sil]
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - 20
    return f"""
  <clipPath id="up"><path d="{UPPER[sil]}"/></clipPath>
  <clipPath id="so"><path d="{SOLE[sil]}"/></clipPath>
  <pattern id="mesh" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="10" stroke="#000" stroke-width="3"/></pattern>
  <linearGradient id="gu" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{cw['up'][0]}"/><stop offset="1" stop-color="{cw['up'][1]}"/></linearGradient>
  <linearGradient id="gs" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{cw['sole'][0]}"/><stop offset="1" stop-color="{cw['sole'][1]}"/></linearGradient>
  <linearGradient id="lit" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".34"/><stop offset=".32" stop-color="#fff" stop-opacity=".04"/><stop offset=".62" stop-color="#000" stop-opacity=".05"/><stop offset="1" stop-color="#000" stop-opacity=".55"/></linearGradient>
  <linearGradient id="litx" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#000" stop-opacity=".45"/><stop offset=".3" stop-color="#000" stop-opacity="0"/><stop offset=".78" stop-color="#fff" stop-opacity=".06"/><stop offset="1" stop-color="#000" stop-opacity=".2"/></linearGradient>
  <radialGradient id="spec" cx=".66" cy=".34" r=".38"><stop offset="0" stop-color="#fff" stop-opacity=".42"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
  <linearGradient id="solelit" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".4"/><stop offset=".25" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".38"/></linearGradient>
  <filter id="grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="3" seed="7"/><feColorMatrix values="0 0 0 0 .5  0 0 0 0 .5  0 0 0 0 .5  0 0 0 1.5 -.5"/></filter>
  <filter id="soft3" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="3"/></filter>
  <path d="{SOLE[sil]}" fill="url(#gs)"/>
  <g clip-path="url(#so)">
    <rect x="90" y="{sb - 16}" width="680" height="30" fill="#0c0c0e" opacity=".62"/>
    <line x1="100" y1="{sb - 7}" x2="760" y2="{sb - 7}" stroke="#fff" stroke-opacity=".28" stroke-width="3" stroke-dasharray="9 7"/>
    <rect x="90" y="340" width="680" height="110" fill="url(#solelit)"/>
    <rect x="90" y="340" width="680" height="110" filter="url(#grain)" opacity=".22"/>
    <line x1="100" y1="355" x2="760" y2="355" stroke="#fff" stroke-opacity=".5" stroke-width="1.6"/>
  </g>
  <path d="{SOLE[sil]}" fill="none" stroke="#fff" stroke-opacity=".2" stroke-width="1.5"/>
  <path d="{SOLE[sil].split(' L')[0]} L752,{352 if sil != 'runner' else 364}" fill="none" stroke="{cw['stripe']}" stroke-width="3" opacity=".9"/>
  <path d="{UPPER[sil]}" fill="url(#gu)"/>
  {mesh}
  <path d="{TOECAP[sil]}" fill="{cw['cap']}"/>
  <path d="{HEEL[sil]}" fill="{cw['heel']}"/>
  <path d="{STRIPE[sil]}" fill="{cw['stripe']}"/>
  <g clip-path="url(#up)">
    <rect x="90" y="70" width="700" height="300" fill="url(#lit)"/>
    <rect x="90" y="70" width="700" height="300" fill="url(#litx)"/>
    <rect x="90" y="70" width="700" height="300" fill="url(#spec)"/>
    <rect x="90" y="70" width="700" height="300" filter="url(#grain)" opacity=".3"/>
    <ellipse cx="{ccx}" cy="{ccy}" rx="{crx}" ry="{cry}" transform="rotate({crot} {ccx} {ccy})" fill="#040405" opacity=".9" filter="url(#soft3)"/>
    <ellipse cx="{ccx + 6}" cy="{ccy + 8}" rx="{crx - 8}" ry="{cry - 4}" transform="rotate({crot} {ccx} {ccy})" fill="{cw['heel']}" opacity=".55" filter="url(#soft3)"/>
    <g transform="translate(5,-8)"><path d="{UPPER[sil]}" fill="none" stroke="#fff" stroke-opacity=".38" stroke-width="1.6" stroke-dasharray="5 6"/></g>
    <path d="{TOECAP[sil]}" fill="none" stroke="#fff" stroke-opacity=".4" stroke-width="1.6" stroke-dasharray="5 6"/>
    <path d="{TOECAP[sil]}" fill="none" stroke="#000" stroke-opacity=".5" stroke-width="3" filter="url(#soft3)"/>
    <path d="{HEEL[sil]}" fill="none" stroke="#000" stroke-opacity=".45" stroke-width="4" filter="url(#soft3)"/>
  </g>
  <path d="{UPPER[sil]}" fill="none" stroke="{cw['edge']}" stroke-opacity=".16" stroke-width="2"/>
  <g clip-path="url(#up)"><ellipse cx="{mx:.0f}" cy="{my:.0f}" rx="{span / 2 + 24:.0f}" ry="22" transform="rotate({ang:.1f} {mx:.0f} {my:.0f})" fill="{cw['cap']}" opacity=".85" filter="url(#soft3)"/></g>
  {''.join(eyelets)}
  <g stroke="#000" stroke-width="9" stroke-linecap="round" opacity=".38" filter="url(#soft3)">{''.join(shade)}</g>
  <g stroke="{cw['lace']}" stroke-width="7" stroke-linecap="round" opacity=".96">{''.join(base)}</g>
  <g stroke="#fff" stroke-width="1.8" stroke-linecap="round" opacity=".55">{''.join(hi)}</g>
"""


def stage(w: int, h: int, body: str, label: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="{label}">
<defs>
  <radialGradient id="bg" cx=".5" cy=".42" r=".75"><stop offset="0" stop-color="#ff5468"/><stop offset=".55" stop-color="#d4192f"/><stop offset="1" stop-color="#8e0c1e"/></radialGradient>
  <radialGradient id="floor" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#000" stop-opacity=".5"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
  <linearGradient id="rim" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ffffff" stop-opacity="0"/><stop offset=".5" stop-color="#ffffff" stop-opacity=".5"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></linearGradient>
</defs>
<rect width="{w}" height="{h}" fill="url(#bg)"/>
{body}
</svg>
"""


def product_svg(slug: str, name: str) -> str:
    cw = COLORWAYS[slug]
    cx, cy = CENTER[cw["sil"]]
    s = 1.2
    tx, ty = 500 - cx * s, 490 - cy * s
    floor_y = ty + SOLE_BOTTOM[cw["sil"]] * s
    body = f"""<defs>
  <linearGradient id="rfg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".34"/><stop offset=".55" stop-color="#fff" stop-opacity=".06"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
  <mask id="rmask" maskUnits="userSpaceOnUse" x="0" y="{floor_y:.0f}" width="1000" height="260"><rect x="0" y="{floor_y:.0f}" width="1000" height="260" fill="url(#rfg)"/></mask>
  <linearGradient id="wall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#000" stop-opacity=".22"/><stop offset="1" stop-color="#000" stop-opacity="0"/></linearGradient>
  <radialGradient id="pool" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#fff" stop-opacity=".28"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
  <filter id="gr" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".8" numOctaves="2" seed="3"/><feColorMatrix values="0 0 0 0 .5  0 0 0 0 .5  0 0 0 0 .5  0 0 0 1.2 -.45"/></filter>
  <filter id="rb" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="2.2"/></filter>
  <filter id="cb" x="-20%" y="-200%" width="140%" height="500%"><feGaussianBlur stdDeviation="9"/></filter>
</defs>
<rect x="0" y="0" width="1000" height="{floor_y:.0f}" fill="url(#wall)"/>
<ellipse cx="500" cy="{floor_y + 14:.0f}" rx="460" ry="70" fill="url(#pool)"/>
<g id="sh" transform="translate({tx:.1f},{ty:.1f}) scale({s})">{shoe(cw)}</g>
<g mask="url(#rmask)"><g transform="translate(0,{2 * floor_y:.1f}) scale(1,-1)" filter="url(#rb)"><use href="#sh"/></g></g>
<ellipse cx="500" cy="{floor_y + 3:.0f}" rx="360" ry="13" fill="#000" opacity=".8" filter="url(#cb)"/>
<ellipse cx="500" cy="{floor_y + 1:.0f}" rx="300" ry="5" fill="#000" opacity=".9" filter="url(#cb)"/>
<rect width="1000" height="1000" filter="url(#gr)" opacity=".07"/>"""
    return stage(1000, 1000, body, f"{name}, original illustration of a sneaker")


def hero_svg() -> str:
    cw = COLORWAYS["noir-01"]
    cw = {**cw, "sil": "low"}
    cx, cy = CENTER["low"]
    s = 1.12
    tx, ty = 1120 - cx * s, 470 - cy * s
    floor_y = 470 + (440 - cy) * s
    body = f"""<ellipse cx="1120" cy="{floor_y:.0f}" rx="420" ry="30" fill="url(#floor)"/>
<rect x="700" y="{floor_y + 10:.0f}" width="840" height="2" fill="url(#rim)"/>
<g transform="translate({tx:.1f},{ty:.1f}) scale({s})">{shoe(cw)}</g>"""
    return stage(1600, 900, body, "NOIR / 01 low-top sneaker, original illustration")


def main() -> None:
    names = {"noir-01": "NOIR / 01", "chrome-runner": "CHROME RUNNER", "atelier-low": "ATELIER LOW",
             "monolith-high": "MONOLITH HIGH", "velocity-form": "VELOCITY FORM", "studio-04": "STUDIO 04"}
    (OUT / "products").mkdir(parents=True, exist_ok=True)
    for slug, name in names.items():
        (OUT / "products" / f"{slug}.svg").write_text(product_svg(slug, name), encoding="utf-8")
    (OUT / "hero.svg").write_text(hero_svg(), encoding="utf-8")
    print(f"wrote {len(names)} product images and hero.svg to {OUT}")


if __name__ == "__main__":
    main()
