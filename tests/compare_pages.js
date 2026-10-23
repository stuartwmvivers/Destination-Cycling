// Before/after check for refactors: render the same settings in two versions of a dashboard and require
// identical page markup (text, tables, chart geometry). Settings are injected through the page's saved params.
// Usage: node tests/compare_pages.js <old .html file> <old params key> <new site dir> <region> [new params key]
// e.g.   node tests/compare_pages.js spanish-coast-climate.html spain-climate-params _site spain-coast
const { chromium } = require('playwright');
const path = require('path');
const { serve } = require('./serve');

const PLACES = ['begur', 'llanca', 'roses', 'lescala', 'palamos', 'tossa', 'figueres', 'girona', 'olot', 'nerja', 'torrox',
  'frigiliana', 'marbella', 'estepona', 'alicante', 'altea', 'javea', 'palma', 'soller', 'pollensa', 'dunning', 'bristol'];
const MEASURES = ['tmax', 'tmin', 'ride', 'warm', 'rain', 'wet', 'tram', 'hot', 'frost'];
const combos = [
  ...PLACES.map((place, i) => ({ place, measure: MEASURES[i % 9], period: ['1', '7', 'year', '4'][i % 4], year: ['all', '2020', '2025'][i % 3],
    compare: ['dunning', 'bristol', 'nerja', 'none'][i % 4], frame: 'auto', region: ['all', 'Costa Brava', 'UK', 'Mallorca'][i % 4] })),
  ...MEASURES.map((measure) => ({ place: 'torrox', measure, period: 'year', year: 'all', compare: 'dunning', frame: 'spain', region: 'all' })),
];

(async () => {
  const [oldFile, oldKey, newDir, region, newKey = 'dc-params-' + region] = process.argv.slice(2);
  const server = await serve(newDir);
  const sides = [['old', 'file://' + path.resolve(oldFile), oldKey], ['new', server.url + region + '/', newKey]];
  const b = await chromium.launch();
  let bad = 0;
  for (const [i, c] of combos.entries()) {
    const got = {};
    for (const [side, url, key] of sides) {
      const ctx = await b.newContext({ viewport: { width: 1280, height: 900 } });
      await ctx.addInitScript(([k, v]) => localStorage.setItem(k, v), [key, JSON.stringify(c)]);
      const p = await ctx.newPage();
      await p.goto(url); await p.waitForLoadState('networkidle'); await p.waitForTimeout(500);
      // The map legend's gradient gets a random id on every draw; normalise it.
      got[side] = (await p.evaluate(() => document.querySelector('.cb').innerHTML)).replace(/cbgrad[a-z0-9]+/g, 'cbgrad');
      await ctx.close();
    }
    if (got.old !== got.new) {
      bad++;
      let j = 0; while (got.old[j] === got.new[j]) j++;
      console.log(`DIFF #${i} ${JSON.stringify(c)}\n  old: …${got.old.slice(Math.max(0, j - 80), j + 120)}\n  new: …${got.new.slice(Math.max(0, j - 80), j + 120)}`);
    }
  }
  await b.close(); server.close();
  console.log(bad ? `${bad} of ${combos.length} settings differ` : `ok: all ${combos.length} settings render identically`);
  process.exit(bad ? 1 : 0);
})();
