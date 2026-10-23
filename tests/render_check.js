// Smoke test: open the built page in headless Chromium at desktop/phone widths, light/dark,
// fail on any page error or horizontal overflow, and click through the main controls.
// Usage: node tests/render_check.js spanish-coast-climate.html   (needs `npm i playwright`)
const { chromium } = require('playwright');
(async () => {
  const file = 'file://' + require('path').resolve(process.argv[2] || 'spanish-coast-climate.html');
  const b = await chromium.launch(); const errs = [];
  for (const [w, h, scheme] of [[1280, 900, 'light'], [400, 860, 'dark']]) {
    const ctx = await b.newContext({ viewport: { width: w, height: h }, colorScheme: scheme }); const p = await ctx.newPage();
    p.on('pageerror', (e) => errs.push(`${w}: ${e.message}`));
    await p.goto(file); await p.waitForTimeout(600);
    const [sw, cw] = await p.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]);
    if (sw > cw) errs.push(`${w}: horizontal overflow ${sw}>${cw}`);
    for (const f of ['spain', 'brava', 'sol', 'blanca', 'mallorca']) { await p.click(`#cb-frames button[data-f="${f}"]`); await p.waitForTimeout(100); }
    for (const pl of ['begur', 'nerja', 'bristol', 'torrox']) { await p.selectOption('#cb-place', pl); await p.waitForTimeout(100); }
    await p.screenshot({ path: `render-${w}.png`, fullPage: true });
    await ctx.close();
  }
  await b.close();
  if (errs.length) { console.error(errs.join('\n')); process.exit(1); }
  console.log('ok');
})();
