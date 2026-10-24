// Smoke test: open each page in headless Chromium at desktop/phone widths, light/dark,
// fail on any page error, failed request or horizontal overflow, and click through the main controls (dashboards).
// Usage: node tests/render_check.js _site                       (every page in the built site, served over HTTP)
//        node tests/render_check.js spanish-coast-climate.html  (one standalone file)
// Screenshots go to the current directory as render-<page>-<width>.png. Needs `npm ci` and `npx playwright install chromium`.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const { serve, stubTiles } = require('./serve');

const pagesIn = (dir) => fs.readdirSync(dir, { recursive: true }).filter((f) => f.endsWith('.html')).map((f) => f.split(path.sep).join('/'));

(async () => {
  const target = process.argv[2] || '_site';
  let server = null, pages;
  if (fs.statSync(target).isDirectory()) {
    server = await serve(target);
    pages = pagesIn(target).map((f) => [f.replace(/index\.html$/, '').replace(/\/$/, '') || 'index', server.url + f.replace(/index\.html$/, '')]);
  } else {
    pages = [[path.basename(target, '.html'), 'file://' + path.resolve(target)]];
  }
  const b = await chromium.launch(); const errs = [];
  for (const [name, url] of pages) {
    for (const [w, h, scheme] of [[1280, 900, 'light'], [400, 860, 'dark']]) {
      const ctx = await b.newContext({ viewport: { width: w, height: h }, colorScheme: scheme }); await stubTiles(ctx); const p = await ctx.newPage();
      p.on('pageerror', (e) => errs.push(`${name} ${w}: ${e.message}`));
      p.on('console', (m) => { if (m.type() === 'error') errs.push(`${name} ${w}: console: ${m.text()}`); });
      p.on('requestfailed', (r) => errs.push(`${name} ${w}: request failed ${r.url()}`));
      p.on('response', (r) => { if (r.status() >= 400) errs.push(`${name} ${w}: HTTP ${r.status()} ${r.url()}`); });
      await p.goto(url); await p.waitForLoadState('networkidle'); await p.waitForTimeout(600);
      const [sw, cw] = await p.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]);
      if (sw > cw) errs.push(`${name} ${w}: horizontal overflow ${sw}>${cw}`);
      if (await p.$('#cb-frames')) {   // dashboard pages only: data must have loaded, then click through the main controls
        if (await p.$('.cb-fail')) errs.push(`${name} ${w}: a panel shows "Failed to load"`);
        if (!(await p.$('#cb-tbody tr'))) errs.push(`${name} ${w}: places table is empty`);
        const dots = await p.locator('#cb-map path.leaflet-interactive').count();
        if (!dots) errs.push(`${name} ${w}: map has no place markers`);
        for (const f of ['spain', 'brava', 'sol', 'blanca', 'mallorca']) { await p.click(`#cb-frames button[data-f="${f}"]`); await p.waitForTimeout(100); }
        for (const pl of ['begur', 'nerja', 'bristol', 'torrox']) { await p.selectOption('#cb-place', pl); await p.waitForTimeout(100); }
        // clicking a visible marker (other than the selected one) must change the selected place
        const before = await p.inputValue('#cb-place');
        const target = await p.evaluate(() => {
          const box = document.querySelector('#cb-map').getBoundingClientRect();
          const dots = [...document.querySelectorAll('#cb-map path.leaflet-interactive')].map((el) => el.getBoundingClientRect())
            .filter((r) => r.left > box.left + 20 && r.right < box.right - 240 && r.top > box.top + 20 && r.bottom < box.bottom - 20);
          const r = dots.find((d) => d.width < 22) || dots[0];   // unselected markers are smaller
          return r ? [r.left + r.width / 2, r.top + r.height / 2] : null;
        });
        if (!target) errs.push(`${name} ${w}: no clickable marker in view`);
        else {
          await p.mouse.click(target[0], target[1]); await p.waitForTimeout(400);
          if ((await p.inputValue('#cb-place')) === before) errs.push(`${name} ${w}: clicking a map marker did not select a place`);
        }
      }
      await p.screenshot({ path: `render-${name.replace(/\//g, '_')}-${w}.png`, fullPage: true });
      await ctx.close();
    }
    console.log('checked', name);
  }
  await b.close();
  if (server) server.close();
  if (errs.length) { console.error(errs.join('\n')); process.exit(1); }
  console.log('ok');
})();
