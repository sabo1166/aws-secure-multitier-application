// Local QA helper: capture a page at an exact viewport width using Edge/Chrome device emulation.
// Usage: node tools/capture-screenshot.mjs <url> <out.png> [width=1440] [height=900] [--full]
// It drives a locally installed browser over the DevTools Protocol. No cloud services involved.
import { spawn } from 'node:child_process';
import { existsSync, writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const [url, out, w = '1440', h = '900', ...flags] = process.argv.slice(2);
if (!url || !out) { console.error('usage: capture-screenshot.mjs <url> <out.png> [width] [height] [--full]'); process.exit(2); }
const full = flags.includes('--full');
const candidates = [
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
];
const browser = candidates.find(existsSync);
if (!browser) { console.error('No Edge/Chrome found'); process.exit(2); }

const port = 9300 + Math.floor(Math.random() * 500);
const profile = mkdtempSync(join(tmpdir(), 'cap-'));
const proc = spawn(browser, [`--remote-debugging-port=${port}`, '--headless=new', '--disable-gpu', `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function target() {
  for (let i = 0; i < 50; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
      const page = list.find((t) => t.type === 'page');
      if (page) return page.webSocketDebuggerUrl;
    } catch { /* browser still starting */ }
    await sleep(200);
  }
  throw new Error('browser did not start');
}

try {
  const ws = new WebSocket(await target());
  await new Promise((r) => (ws.onopen = r));
  let id = 0; const pending = new Map();
  ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); } };
  const send = (method, params = {}) => new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });

  const width = Number(w), height = Number(h), mobile = width < 700;
  await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile });
  await send('Page.enable');
  await send('Page.navigate', { url });
  await sleep(1800);
  let clip;
  if (full) {
    const m = await send('Page.getLayoutMetrics');
    const size = m.result.cssContentSize || m.result.contentSize;
    clip = { x: 0, y: 0, width, height: Math.ceil(size.height), scale: 1 };
    await send('Emulation.setDeviceMetricsOverride', { width, height: clip.height, deviceScaleFactor: 1, mobile });
    await sleep(400);
  }
  const shot = await send('Page.captureScreenshot', { format: 'png', ...(clip ? { clip } : {}) });
  writeFileSync(out, Buffer.from(shot.result.data, 'base64'));
  const overflow = await send('Runtime.evaluate', { expression: 'document.documentElement.scrollWidth - document.documentElement.clientWidth', returnByValue: true });
  console.log(`saved ${out} (${width}px wide); horizontal overflow px: ${overflow.result.result.value}`);
  ws.close();
} finally {
  proc.kill();
}
