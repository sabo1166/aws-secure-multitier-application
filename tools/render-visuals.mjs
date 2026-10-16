// Render the visual documents in docs/visual/*.html to PNG and PDF and inspect the layout mechanically.
// Usage: node tools/render-visuals.mjs
// For every .page element it reports content that overflows the A4 page and any text clipped inside a box.
import { spawn } from 'node:child_process';
import { existsSync, writeFileSync, mkdtempSync, readdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const dir = resolve(dirname(fileURLToPath(import.meta.url)), '..', 'docs', 'visual');
const files = readdirSync(dir).filter((f) => f.endsWith('.html'));
const browser = ['C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', 'C:/Program Files/Microsoft/Edge/Application/msedge.exe', 'C:/Program Files/Google/Chrome/Application/chrome.exe'].find(existsSync);
if (!browser) { console.error('No Edge/Chrome found'); process.exit(2); }

const port = 9500 + Math.floor(Math.random() * 200);
const proc = spawn(browser, [`--remote-debugging-port=${port}`, '--headless=new', '--disable-gpu', `--user-data-dir=${mkdtempSync(join(tmpdir(), 'viz-'))}`, 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let problems = 0;

try {
  let wsUrl;
  for (let i = 0; i < 60 && !wsUrl; i++) {
    try { wsUrl = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === 'page')?.webSocketDebuggerUrl; } catch { /* starting */ }
    if (!wsUrl) await sleep(200);
  }
  const ws = new WebSocket(wsUrl); await new Promise((r) => (ws.onopen = r));
  let id = 0; const pending = new Map();
  ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); } };
  const send = (method, params = {}) => new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
  await send('Page.enable'); await send('Runtime.enable');

  for (const f of files) {
    const base = f.replace(/\.html$/, '');
    await send('Emulation.setDeviceMetricsOverride', { width: 860, height: 1200, deviceScaleFactor: 2, mobile: false });
    await send('Page.navigate', { url: pathToFileURL(join(dir, f)).href });
    await sleep(1500);
    await send('Runtime.evaluate', { expression: 'document.fonts.ready.then(() => true)', awaitPromise: true });

    const probe = await send('Runtime.evaluate', { returnByValue: true, expression: `(() => {
      const out = [];
      const pages = [...document.querySelectorAll('.page')];
      pages.forEach((p, i) => {
        if (p.scrollHeight > p.clientHeight + 1) out.push('page ' + (i + 1) + ' content overflows by ' + (p.scrollHeight - p.clientHeight) + 'px');
        if (p.scrollWidth > p.clientWidth + 1) out.push('page ' + (i + 1) + ' overflows horizontally');
        p.querySelectorAll('.card, .chip, .node, .sticky, td, th, .callout, .figure').forEach((e) => {
          if (e.scrollWidth > e.clientWidth + 2 && getComputedStyle(e).overflow !== 'visible') out.push('page ' + (i + 1) + ' clipped text in <' + e.tagName.toLowerCase() + '> ' + (e.textContent || '').trim().slice(0, 40));
        });
        const foot = p.querySelector('.foot');
        if (foot) { const last = [...p.children].filter((c) => c !== foot && !c.classList.contains('foot')).pop(); if (last && last.getBoundingClientRect().bottom > foot.getBoundingClientRect().top - 2) out.push('page ' + (i + 1) + ' content collides with the footer'); }
      });
      document.querySelectorAll('img').forEach((im) => { if (!im.complete || im.naturalWidth === 0) out.push('broken image ' + im.getAttribute('src')); });
      return { pages: pages.length, issues: out };
    })()` });
    const { pages, issues } = probe.result.result.value;

    const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: { x: (860 - 794) / 2, y: 0, width: 794, height: pages * (1123 + 18), scale: 1 } });
    writeFileSync(join(dir, `${base}.png`), Buffer.from(shot.result.data, 'base64'));
    const pdf = await send('Page.printToPDF', { printBackground: true, preferCSSPageSize: true });
    writeFileSync(join(dir, `${base}.pdf`), Buffer.from(pdf.result.data, 'base64'));
    console.log(`${issues.length ? 'ISSUES' : 'OK    '} ${f}: ${pages} page(s) -> ${base}.png, ${base}.pdf`);
    for (const i of issues) { console.log(`   - ${i}`); problems++; }
  }
  ws.close();
} finally { proc.kill(); }
process.exit(problems ? 1 : 0);
