// Before/after check for refactors: render the same settings in two versions of a dashboard and require
// identical page markup (text, tables, chart geometry). Settings are injected through the page's saved params.
// Usage: node tests/compare_pages.js <old .html file or old site dir> <old params key> <new site dir> <region> [new params key]
// e.g.   node tests/compare_pages.js old.html spain-climate-params _site spain-coast --skip-map
// --skip-map leaves the map card out of the comparison (the map itself is meant to differ since phase B).
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const { serve, stubTiles } = require('./serve');

const SKIP_MAP = process.argv.includes('--skip-map');
const PLACES = ['begur', 'llanca', 'roses', 'lescala', 'palamos', 'tossa', 'figueres', 'girona', 'olot', 'nerja', 'torrox',
  'frigiliana', 'marbella', 'estepona', 'alicante', 'altea', 'javea', 'palma', 'soller', 'pollensa', 'dunning', 'bristol'];
const MEASURES = ['tmax', 'tmin', 'ride', 'warm', 'rain', 'wet', 'tram', 'hot', 'frost'];
const combos = [
  ...PLACES.map((place, i) => ({ place, measure: MEASURES[i % 9], period: ['1', '7', 'year', '4'][i % 4], year: ['all', '2020', '2025'][i % 3],
    compare: ['dunning', 'bristol', 'nerja', 'none'][i % 4], frame: 'auto', region: ['all', 'Costa Brava', 'UK', 'Mallorca'][i % 4] })),
  ...MEASURES.map((measure) => ({ place: 'torrox', measure, period: 'year', year: 'all', compare: 'dunning', frame: 'spain', region: 'all' })),
];

(async () => {
  const args = process.argv.slice(2).filter((a) => a !== '--skip-map');
  const [oldFile, oldKey, newDir, region, newKey = 'dc-params-' + region] = args;
  const server = await serve(newDir);
  const oldServer = fs.statSync(oldFile).isDirectory() ? await serve(oldFile) : null;   // an earlier build, served the same way
  const oldUrl = oldServer ? oldServer.url + region + '/' : 'file://' + path.resolve(oldFile);
  const sides = [['old', oldUrl, oldKey], ['new', server.url + region + '/', newKey]];
  const b = await chromium.launch();
  let bad = 0;
  for (const [i, c] of combos.entries()) {
    const got = {};
    for (const [side, url, key] of sides) {
      const ctx = await b.newContext({ viewport: { width: 1280, height: 900 } });
      await stubTiles(ctx);
      await ctx.addInitScript(([k, v]) => localStorage.setItem(k, v), [key, JSON.stringify(c)]);
      const p = await ctx.newPage();
      await p.goto(url); await p.waitForLoadState('networkidle'); await p.waitForTimeout(500);
      // The map card is left out when --skip-map is given (phase B replaced the map); otherwise normalise the
      // old map legend's random gradient id.
      got[side] = (await p.evaluate((skip) => { const c = document.querySelector('.cb').cloneNode(true); if (skip) c.querySelector('#map-card').remove(); return c.innerHTML; }, SKIP_MAP)).replace(/cbgrad[a-z0-9]+/g, 'cbgrad');
      await ctx.close();
    }
    if (got.old !== got.new) {
      bad++;
      let j = 0; while (got.old[j] === got.new[j]) j++;
      console.log(`DIFF #${i} ${JSON.stringify(c)}\n  old: …${got.old.slice(Math.max(0, j - 80), j + 120)}\n  new: …${got.new.slice(Math.max(0, j - 80), j + 120)}`);
    }
  }
  await b.close(); server.close(); if (oldServer) oldServer.close();
  console.log(bad ? `${bad} of ${combos.length} settings differ` : `ok: all ${combos.length} settings render identically`);
  process.exit(bad ? 1 : 0);
})();
