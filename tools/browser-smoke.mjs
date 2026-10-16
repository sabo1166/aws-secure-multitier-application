// Real-browser smoke test of the storefront UI (drives Edge/Chrome over the DevTools Protocol).
// Usage: node tools/browser-smoke.mjs <base-url> [screenshot-dir]
// Run it against a LOCAL server with a throwaway SQLite database; it places a demo order.
import { spawn } from 'node:child_process';
import { existsSync, writeFileSync, mkdtempSync, mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const base = (process.argv[2] || 'http://127.0.0.1:8000').replace(/\/$/, '');
const shotDir = process.argv[3];
if (shotDir) mkdirSync(shotDir, { recursive: true });
const browser = ['C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', 'C:/Program Files/Microsoft/Edge/Application/msedge.exe', 'C:/Program Files/Google/Chrome/Application/chrome.exe'].find(existsSync);
if (!browser) { console.error('No Edge/Chrome found'); process.exit(2); }

// Pre-flight: the test buys 3 pairs of NOIR / 01 in US 9, so it needs a freshly seeded database.
try {
  const noir = await (await fetch(`${base}/api/products/noir-01`)).json();
  const nine = noir.sizes.find((x) => x.size === '9');
  if (!nine || nine.stock < 3) { console.error('Database is not fresh: NOIR / 01 US 9 has fewer than 3 in stock. Restart the server on a new SQLite file and rerun.'); process.exit(2); }
} catch (e) { console.error(`Cannot reach ${base}: ${e}`); process.exit(2); }

const port = 9800 + Math.floor(Math.random() * 150);
const proc = spawn(browser, [`--remote-debugging-port=${port}`, '--headless=new', '--disable-gpu', `--user-data-dir=${mkdtempSync(join(tmpdir(), 'smoke-'))}`, 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const results = [];
const check = (name, ok, detail = '') => { results.push({ name, ok }); console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${ok ? '' : '  -> ' + detail}`); };

async function connect() {
  for (let i = 0; i < 60; i++) {
    try {
      const page = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === 'page');
      if (page) { const ws = new WebSocket(page.webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r)); return ws; }
    } catch { /* starting */ }
    await sleep(200);
  }
  throw new Error('browser did not start');
}

try {
  const ws = await connect();
  let id = 0; const pending = new Map();
  ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); } };
  const send = (method, params = {}) => new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
  const ev = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); return r.result.result ? r.result.result.value : undefined; };
  const waitFor = async (expr, ms = 6000) => { const end = Date.now() + ms; while (Date.now() < end) { if (await ev(expr)) return true; await sleep(120); } return false; };
  const goto = async (path) => { await send('Page.navigate', { url: base + path }); await sleep(250); await waitFor('document.readyState === "complete"'); await sleep(250); };
  const shot = async (name) => { if (!shotDir) return; await sleep(300); const r = await send('Page.captureScreenshot', { format: 'png' }); writeFileSync(join(shotDir, name), Buffer.from(r.result.data, 'base64')); };
  const setViewport = (width, height) => send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: width < 700 });
  const click = (sel) => ev(`(() => { const e = document.querySelector(${JSON.stringify(sel)}); if (!e) return false; e.click(); return true; })()`);
  const fill = (sel, v) => ev(`(() => { const e = document.querySelector(${JSON.stringify(sel)}); e.value = ${JSON.stringify(v)}; e.dispatchEvent(new Event('input', {bubbles:true})); return true; })()`);
  const text = (sel) => ev(`(document.querySelector(${JSON.stringify(sel)}) || {}).textContent || ''`);

  await send('Page.enable'); await send('Runtime.enable');
  await setViewport(1440, 900);

  // 1. Product page: size is required, then add to bag
  await goto('/products/noir-01');
  check('PDP loads with product name', (await text('h1')).includes('NOIR'));
  await shot('02-product-detail-desktop.png');
  await click('#add-form button[type="submit"]');
  check('Adding without a size shows a message and adds nothing', await waitFor(`document.getElementById('add-error').textContent.includes('select a size')`) && (await text('[data-cart-count]')) === '0');
  await click('label[for="size-9"]');
  check('Selecting a size updates stock status', await waitFor(`document.getElementById('stock-status').textContent.includes('US 9')`));
  await click('[data-qty-step="1"]');
  check('Quantity stepper increments', (await ev(`document.getElementById('qty').value`)) === '2');
  await click('#add-form button[type="submit"]');
  check('Add to bag updates the live bag count to 2', await waitFor(`document.querySelector('[data-cart-count]').textContent === '2'`));

  // 2. Cart: change quantity, totals recomputed by server
  await goto('/cart');
  check('Cart shows the line and server-computed total', (await text('.cart-line')).includes('NOIR') && (await text('.summary')).includes('$490.00'));
  await click('[data-cart-step="1"]');
  check('Cart + button changes quantity to 3 and total to $735.00', await waitFor(`document.querySelector('.cart-line output') && document.querySelector('.cart-line output').textContent === '3' && document.querySelector('.summary').textContent.includes('$735.00')`));
  await shot('04-cart-desktop.png');

  // 3. Checkout: validation, then success
  await goto('/checkout');
  check('Demo banner is visible on checkout', (await text('.demo-banner')).includes('No payment is taken'));
  check('No card fields exist on checkout', (await ev(`document.querySelectorAll('input[name*="card" i], input[autocomplete^="cc-"]').length`)) === 0);
  await click('#place-order');
  check('Empty checkout shows field errors from the server', await waitFor(`[...document.querySelectorAll('[data-error-for]')].some(e => e.textContent.length > 0)`));
  await fill('#c-name', 'Ada Example'); await fill('#c-email', 'not-an-email');
  await fill('#c-l1', '1 Test Street'); await fill('#c-city', 'Testville'); await fill('#c-zip', 'AB1 2CD'); await fill('#c-country', 'Testland');
  await click('#place-order');
  check('Invalid email is rejected inline', await waitFor(`document.querySelector('[data-error-for="customer_email"]').textContent.length > 0`));
  await shot('05-checkout-validation-desktop.png');
  await fill('#c-email', 'ada@example.com');
  await click('#place-order');
  check('Valid checkout redirects to a confirmation page', await waitFor(`location.pathname.startsWith('/orders/')`, 8000));
  await waitFor('document.readyState === "complete"');
  const confirmation = await text('main');
  check('Confirmation states demo / no payment', confirmation.includes('Demo order recorded') && confirmation.includes('No payment was processed'));
  await shot('06-order-confirmation-desktop.png');
  await goto('/');
  check('Bag is empty again after the order', (await text('[data-cart-count]')) === '0');

  // 4. Filters
  await goto('/shop');
  await ev(`(() => { const s = document.getElementById('f-sort'); s.value = 'price_desc'; s.dispatchEvent(new Event('change', {bubbles:true})); })()`);
  check('Sort select reloads the list sorted high to low', await waitFor(`location.search.includes('sort=price_desc') && document.querySelector('.card h3').textContent.includes('MONOLITH')`));
  await goto('/shop?q=zzzz');
  check('Empty search shows the empty state', (await text('.empty')).includes('Nothing matches'));
  await goto('/shop');
  await shot('03-shop-desktop.png');

  // 4a. Static assets really load from the frontend folder: stylesheet applied, JS ran, fonts and images decoded
  const assetProbe = `(async () => {
    await document.fonts.ready;
    const bad = [];
    if (getComputedStyle(document.body).backgroundColor !== 'rgb(255, 255, 255)') bad.push('stylesheet not applied');
    if (!document.documentElement.classList.contains('js')) bad.push('boot.js did not run');
    if (!document.fonts.check('500 20px "Cormorant Garamond"')) bad.push('serif font not loaded');
    if (!document.fonts.check('400 16px Inter')) bad.push('Inter font not loaded');
    document.querySelectorAll('img').forEach((i) => { if (!i.complete || i.naturalWidth === 0) bad.push('image failed ' + i.getAttribute('src')); });
    return bad.join('; ');
  })()`;
  for (const p of ['/', '/shop', '/products/noir-01', '/collections']) {
    await goto(p);
    await sleep(600);
    const bad = await ev(assetProbe);
    check(`Static assets load on ${p}: CSS, JS, fonts, images`, bad === '', bad);
  }

  // 4b. Structural accessibility checks (not a full audit)
  const a11yProbe = `(() => {
    const bad = [];
    if (document.querySelectorAll('h1').length !== 1) bad.push('h1 count ' + document.querySelectorAll('h1').length);
    if (!document.documentElement.lang) bad.push('html lang missing');
    document.querySelectorAll('img').forEach((i) => { if (!i.hasAttribute('alt')) bad.push('img without alt ' + i.src); });
    document.querySelectorAll('input:not([type=hidden]), select, textarea').forEach((e) => {
      if (!(e.labels && e.labels.length) && !e.getAttribute('aria-label')) bad.push('unlabelled ' + (e.name || e.id));
    });
    document.querySelectorAll('button').forEach((b) => { if (!b.textContent.trim() && !b.getAttribute('aria-label')) bad.push('unnamed button'); });
    if (!document.querySelector('main')) bad.push('no <main>');
    return bad.join('; ');
  })()`;
  for (const p of ['/', '/shop', '/products/noir-01', '/collections', '/journal', '/about', '/policies', '/cart']) {
    await goto(p);
    const problems = await ev(a11yProbe);
    check(`A11y structure ${p}: one h1, lang, alt text, labelled controls, <main>`, problems === '', problems);
  }
  await goto('/');
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
  check('Keyboard: first Tab focuses the skip link', (await ev(`document.activeElement && document.activeElement.className`)) === 'skip-link');
  const seen = new Set();
  for (let i = 0; i < 12; i++) {
    await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
    await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
    seen.add(await ev(`(() => { const a = document.activeElement; const r = a.getBoundingClientRect(); const idx = Array.from(document.querySelectorAll('a,button,input,select,summary')).indexOf(a); return '#' + idx + ' ' + a.tagName + ' ' + (a.getAttribute('href') || a.id || a.className) + ':' + (r.width > 0 && r.height > 0 ? 'visible' : 'HIDDEN'); })()`));
  }
  check('Keyboard: 12 Tab presses reach 12 distinct visible controls', seen.size === 12 && ![...seen].some((s) => s.endsWith('HIDDEN')), [...seen].join(' | '));

  // 5. Mobile navigation
  await setViewport(390, 844);
  await goto('/');
  check('Mobile: nav hidden until the menu button is used', (await ev(`getComputedStyle(document.getElementById('primary-nav')).display`)) === 'none');
  await click('.nav-toggle');
  check('Mobile: menu opens and aria-expanded is true', (await ev(`getComputedStyle(document.getElementById('primary-nav')).display`)) !== 'none' && (await ev(`document.querySelector('.nav-toggle').getAttribute('aria-expanded')`)) === 'true');
  await shot('07-mobile-menu.png');
  check('Mobile: no horizontal overflow on home', (await ev('document.documentElement.scrollWidth - document.documentElement.clientWidth')) <= 0);
  await goto('/shop');
  check('Mobile: no horizontal overflow on shop', (await ev('document.documentElement.scrollWidth - document.documentElement.clientWidth')) <= 0);
  await goto('/products/noir-01');
  check('Mobile: no horizontal overflow on product page', (await ev('document.documentElement.scrollWidth - document.documentElement.clientWidth')) <= 0);
  await goto('/');
  await shot('01-homepage-mobile.png');
  await setViewport(1440, 900);
  await goto('/');
  await shot('01-homepage-desktop.png');

  ws.close();
} catch (e) {
  check('smoke test ran without crashing', false, String(e));
} finally {
  proc.kill();
}
const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} checks passed`);
process.exit(failed ? 1 : 0);
