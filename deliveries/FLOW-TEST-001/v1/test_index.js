// FLOW-TEST-001 v1 automated verification (C11). Run: node test_index.js
// Uses the pre-installed Playwright Chromium. No network access is needed or allowed.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const FILE = path.resolve(__dirname, 'index.html');
const INITIAL = 'Co-Intelligence workflow test passed.';
const FINAL = 'All agents completed their handoffs.';
const LABEL = 'Complete handoffs';

const results = [];
function check(id, name, ok, detail) {
  results.push({ id, name, result: ok ? 'PASS' : 'FAIL', detail });
}

(async () => {
  const src = fs.readFileSync(FILE, 'utf8');
  // Static checks
  check('S1', 'No external URLs (http/https/// ) in source', !/(https?:)?\/\/[a-z0-9]/i.test(src), 'regex scan');
  check('S2', 'No src= or href= attributes', !/\s(src|href)\s*=/i.test(src), 'regex scan');
  check('S3', 'Restrictive CSP meta present (default-src none)', /http-equiv="Content-Security-Policy"[^>]*default-src 'none'/.test(src), 'meta tag');
  check('S4', 'Text updated via textContent only (no innerHTML/outerHTML/document.write/eval)',
    /\.textContent\s*=/.test(src) && !/innerHTML|outerHTML|document\.write|eval\(|new Function/.test(src), 'source scan');
  check('S5', 'No fetch/XMLHttpRequest/WebSocket/sendBeacon/import', !/fetch\(|XMLHttpRequest|WebSocket|sendBeacon|import\(/.test(src), 'source scan');

  const browser = await chromium.launch();
  const page = await browser.newPage();
  const requests = [];
  const consoleErrors = [];
  page.on('request', r => requests.push(r.url()));
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', e => consoleErrors.push(String(e)));
  await page.goto('file://' + FILE);

  const msg = () => page.evaluate(() => document.getElementById('message').textContent);
  const bodyText = () => page.evaluate(() => document.body.innerText);

  check('R1', 'Initial text exact', (await msg()) === INITIAL, JSON.stringify(await msg()));
  const label = await page.evaluate(() => document.getElementById('complete').textContent);
  check('R2', 'Button label exact', label === LABEL, JSON.stringify(label));
  const btns = await page.locator('button').count();
  check('R3', 'Exactly one button', btns === 1, String(btns));
  const t0 = await bodyText();
  check('R4', 'No quotation marks displayed (initial)', !/["'‘’“”]/.test(t0), JSON.stringify(t0));

  await page.click('#complete');
  check('R5', 'First click shows final text exactly', (await msg()) === FINAL, JSON.stringify(await msg()));
  const htmlAfter1 = await page.evaluate(() => document.body.innerHTML);

  await page.click('#complete');
  await page.click('#complete');
  await page.click('#complete');
  const htmlAfter4 = await page.evaluate(() => document.body.innerHTML);
  check('R6', 'Repeat clicks are a no-op (text and DOM unchanged)', (await msg()) === FINAL && htmlAfter1 === htmlAfter4, JSON.stringify(await msg()));
  const t1 = await bodyText();
  check('R7', 'No quotation marks displayed (final)', !/["'‘’“”]/.test(t1), JSON.stringify(t1));

  const external = requests.filter(u => !u.startsWith('file://'));
  check('R8', 'No network requests other than the file itself', external.length === 0 && requests.length === 1, JSON.stringify(requests));
  check('R9', 'No console errors or CSP violations', consoleErrors.length === 0, JSON.stringify(consoleErrors));

  await browser.close();
  const failed = results.filter(r => r.result !== 'PASS');
  const out = { file: 'deliveries/FLOW-TEST-001/v1/index.html', run_at_utc: new Date().toISOString(),
    chromium: browser.version ? browser.version() : 'n/a', passed: results.length - failed.length, total: results.length, results };
  console.log(JSON.stringify(out, null, 2));
  process.exit(failed.length ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
