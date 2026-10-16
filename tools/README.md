# Tools

Local helpers for checking quality. **None of them creates, changes or contacts AWS resources**, and none is part of the application or its deployment. Run from the repository root.

| Tool | Run | What it does |
|---|---|---|
| `check-docs.mjs` | `node tools/check-docs.mjs` | Validates links and images, statuses, the evidence register (VERIFIED needs a real file), required files, screenshots marked CAPTURED, secrets, and that no automation or infrastructure-as-code files exist |
| `browser-smoke.mjs` | `node tools/browser-smoke.mjs <url> [screenshot-dir]` | Drives a real Edge or Chrome through the storefront (assets load, bag, checkout, filters, keyboard, mobile). Places a demo order, so use a fresh throwaway database |
| `capture-screenshot.mjs` | `node tools/capture-screenshot.mjs <url> <out.png> [w] [h] [--full]` | Screenshot at an exact viewport width using device emulation. Also renders `architecture.png` from the SVG |
| `mutation_check.py` | `python tools/mutation_check.py` | Breaks six behaviours one at a time and confirms the tests fail each time; restores the files |
| `check_contrast.py` | `python tools/check_contrast.py` | WCAG AA contrast of the stylesheet's colour pairs |
| `render-visuals.mjs` | `node tools/render-visuals.mjs` | Renders `docs/visual/*.html` to PNG and PDF and reports overflow or clipping |

The Node tools need Node 22 or newer (built-in `WebSocket` and `fetch`) and an installed Edge or Chrome. Their recorded results are in `evidence/redacted/`.
