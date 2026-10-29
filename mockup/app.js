// Interface mock-up (docs/interface-plan.md, DC-27): places first, plain words, the full controls in "Adjust".
// Data: data/areas.json (mockup/make_data.py) and, in a private copy only, data/prices.json.
(() => {
  const $ = (s, el = document) => el.querySelector(s);
  const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
  const num = (x, d = 0) => (x == null ? '–' : Number(x).toLocaleString('en-GB', { maximumFractionDigits: d, minimumFractionDigits: d }));
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const WINTER = [0, 1, 2, 3, 4, 9, 10, 11];   // October to May, the months the weather score counts most
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private browsing: not remembered */ } },
  };

  // ---------- factors, presets and settings ----------
  const FACTORS = [
    { id: 'climbing', label: 'Climbing', what: 'Big climbs (300 m or more) within riding distance.' },
    { id: 'weather', label: 'Riding weather', what: 'Dry, mild days for riding, mostly October to May.' },
    { id: 'airport', label: 'Flights', what: 'A short drive to an airport with direct flights from Edinburgh or Glasgow.' },
    { id: 'quiet', label: 'Quiet roads', what: 'Minor roads and loops with little traffic.' },
    { id: 'walking', label: 'Walking and running', what: 'Paths and trails, and hills to walk up.' },
    { id: 'flat', label: 'Easy rides', what: 'Flat or rolling roads for a gentle day.' },
    { id: 'gravel', label: 'Gravel', what: 'Unpaved tracks through the countryside.' },
  ];
  const AGREED = { climbing: 35, weather: 20, airport: 13, quiet: 12, walking: 10, flat: 5, gravel: 5 };
  const PRESETS = [
    { id: 'agreed', label: 'Our agreed balance', w: AGREED },
    { id: 'warm', label: 'Warmest winters', w: { climbing: 20, weather: 40, airport: 13, quiet: 10, walking: 10, flat: 4, gravel: 3 } },
    { id: 'cycling', label: 'Best cycling', w: { climbing: 40, weather: 15, airport: 5, quiet: 20, walking: 0, flat: 10, gravel: 10 } },
    { id: 'flights', label: 'Easiest to get to', w: { climbing: 25, weather: 15, airport: 35, quiet: 10, walking: 8, flat: 4, gravel: 3 } },
    { id: 'quiet', label: 'Quietest', w: { climbing: 25, weather: 15, airport: 10, quiet: 25, walking: 15, flat: 5, gravel: 5 } },
  ];
  const WHERE = [
    { id: 'all', label: 'All Spain', f: () => true },
    { id: 'main', label: 'Mainland', f: (a) => a.lat > 30 && !isBalearic(a) },
    { id: 'canaries', label: 'Canary Islands', f: (a) => a.lat < 30 },
    { id: 'balearics', label: 'Balearics', f: (a) => isBalearic(a) },
  ];
  const isBalearic = (a) => a.lat > 38.5 && a.lat < 40.3 && a.lon > 1.1;
  const DEFAULTS = { w: AGREED, flights: 'year_round', minClimbs: 3, quieter: true, pmin: null, pmax: null, where: 'all' };
  let S = { ...DEFAULTS, ...store.get('dc-mock-settings', {}) };
  S.w = { ...AGREED, ...(S.w || {}) };
  let favs = store.get('dc-mock-favs', []);
  let cmp = store.get('dc-mock-compare', []);
  let adjustOpen = store.get('dc-mock-adjust', false);
  let shown = 12, prevOrder = null;
  const save = () => store.set('dc-mock-settings', S);

  let D, A, PRICE = {};
  const byId = {};

  // ---------- scoring (as the score page: weighted mean of 0-1 components, built-up penalty, airport curve) ----------
  const airportCurve = (m) => (m == null ? 0.15 : m <= 60 ? 1 : m <= 120 ? 1 - 0.5 * (m - 60) / 60 : 0.15 + 0.35 * Math.exp(-(m - 120) / 60));
  const airportVal = (a) => {
    const yr = a.yr ? airportCurve(a.yr.min) : 0.15;
    return S.flights === 'seasonal' ? Math.max(yr, D.meta.seasonal_credit * (a.any ? airportCurve(a.any.min) : 0.15)) : yr;
  };
  const comp = (a, k) => (k === 'airport' ? airportVal(a) : a.c[k] || 0);
  function score(a) {
    let s = 0, t = 0;
    for (const f of FACTORS) {
      if (f.id === 'airport' && S.flights === 'ignore') continue;
      const w = +S.w[f.id] || 0; s += w * comp(a, f.id); t += w;
    }
    const base = t ? (s / t) * 100 : 0;
    return S.quieter ? base * (1 - D.meta.built.strength * (a.c.built || 0)) : base;
  }
  const priceOf = (a) => PRICE[a.id] || null;
  const passes = (a) => {
    if (a.near_n < S.minClimbs) return false;
    if (!WHERE.find((w) => w.id === S.where).f(a)) return false;
    const p = priceOf(a);
    if ((S.pmin || S.pmax) && Object.keys(PRICE).length) {
      if (!p) return false;
      if (S.pmin && p.eur_m2 < S.pmin) return false;
      if (S.pmax && p.eur_m2 > S.pmax) return false;
    }
    return true;
  };
  let ORDER = [];
  function rank() {
    A.forEach((a) => { a.total = score(a); });
    ORDER = A.filter(passes).sort((x, y) => y.total - x.total);
    ORDER.forEach((a, i) => { a.rank = i + 1; });
  }

  // ---------- words for numbers ----------
  const level = (x) => (x >= 0.8 ? 'Excellent' : x >= 0.6 ? 'Very good' : x >= 0.4 ? 'Good' : x >= 0.2 ? 'Fair' : 'Limited');
  const dots = (x) => Math.max(1, Math.min(5, Math.round(x * 5 + 0.25)));
  const wordFor = (w) => (w <= 0 ? 'Not at all' : w <= 6 ? 'A little' : w <= 14 ? 'Some' : w <= 25 ? 'A lot' : 'Most of all');
  const mins = (m) => (m == null ? '–' : m < 60 ? `${m} min` : `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, '0')}`);
  const flightsWord = (ap) => {
    if (!ap) return '';
    const yr = [ap.edi, ap.gla].includes('year_round');
    const who = ap.edi === 'year_round' && ap.gla === 'year_round' ? 'Edinburgh and Glasgow' : ap.edi === 'year_round' ? 'Edinburgh' : ap.gla === 'year_round' ? 'Glasgow' : 'Edinburgh or Glasgow';
    return yr ? `all year from ${who}` : `summer only from ${who}`;
  };
  const tColour = (t) => `var(--t${t < 8 ? 0 : t < 12 ? 1 : t < 16 ? 2 : t < 20 ? 3 : t < 25 ? 4 : 5})`;
  const where = (a) => [a.muni && a.muni !== a.name ? a.muni : null, a.province].filter(Boolean).join(', ');
  const strengths = (a) => FACTORS.filter((f) => f.id !== 'airport' && comp(a, f.id) >= 0.6).sort((x, y) => comp(a, y.id) - comp(a, x.id)).slice(0, 3)
    .map((f) => ({ climbing: 'Great climbing', weather: 'Sunny riding winters', quiet: 'Quiet roads', walking: 'Good walking', flat: 'Easy rides', gravel: 'Gravel tracks' }[f.id]));
  const winterHigh = (a) => Math.round(a.high[0]);
  const winterRide = (a) => Math.round(WINTER.reduce((s, m) => s + a.ride[m], 0));

  const ICON = {
    sun: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
    mountain: '<svg viewBox="0 0 24 24"><path d="M3 20l6-10 4 6 3-4 5 8z"/></svg>',
    plane: '<svg viewBox="0 0 24 24"><path d="M2 16l20-8-3-2-7 3-5-4-2 1 3 5-4 2-2-1z"/><path d="M3 21h18"/></svg>',
    home: '<svg viewBox="0 0 24 24"><path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z"/></svg>',
    star: '<svg viewBox="0 0 24 24"><path d="M12 3l2.8 5.7 6.2.9-4.5 4.4 1 6.2L12 17.3 6.5 20.2l1-6.2L3 9.6l6.2-.9z"/></svg>',
    walk: '<svg viewBox="0 0 24 24"><circle cx="13" cy="4" r="2"/><path d="M10 22l2-7 3 3v6M8 12l3-4 3 2 3 3M12 8l-1 5"/></svg>',
    fork: '<svg viewBox="0 0 24 24"><path d="M7 3v8a2 2 0 0 0 4 0V3M9 11v10M17 3c-2 0-3 3-3 6s1 4 3 4v8"/></svg>',
    map: '<svg viewBox="0 0 24 24"><path d="M9 4l-6 2v14l6-2 6 2 6-2V4l-6 2z"/><path d="M9 4v14M15 6v14"/></svg>',
    compare: '<svg viewBox="0 0 24 24"><path d="M4 5h6v14H4zM14 5h6v14h-6z"/></svg>',
    bike: '<svg viewBox="0 0 24 24"><circle cx="6" cy="16" r="4"/><circle cx="18" cy="16" r="4"/><path d="M6 16l4-8h5l3 8M10 8l2 8h-6M14 5h3"/></svg>',
  };
  const starBtn = (a, cls = 'star') => `<button type="button" class="${cls}" data-star="${a.id}" aria-pressed="${favs.includes(a.id)}" aria-label="${favs.includes(a.id) ? 'Remove from' : 'Add to'} favourites: ${esc(a.name)}">${ICON.star}</button>`;

  // ---------- routing ----------
  const app = $('#app');
  let map = null;
  function route() {
    if (map) { map.remove(); map = null; }
    redraw = null; document.body.classList.remove('exploring'); window.onresize = null;
    const h = location.hash.replace(/^#\/?/, '');
    const [page, id] = h.split('/');
    document.querySelectorAll('[data-nav]').forEach((a) => a.classList.toggle('on', a.dataset.nav === (page || 'places') || (page === 'area' && a.dataset.nav === 'places')));
    if (page === 'area' && byId[id]) areaPage(byId[id]);
    else if (page === 'favourites') favouritesPage();
    else if (page === 'compare') comparePage();
    else if (page === 'about') aboutPage();
    else if (page === 'explore') explorePage();
    else homePage();
    counts();
  }
  function counts() {
    $('#fav-count').textContent = favs.length || '';
    $('#cmp-count').textContent = cmp.length || '';
  }
  function toggleFav(id) {
    favs = favs.includes(id) ? favs.filter((x) => x !== id) : [...favs, id];
    store.set('dc-mock-favs', favs);
    document.querySelectorAll(`[data-star="${id}"]`).forEach((b) => {
      const on = favs.includes(id); b.setAttribute('aria-pressed', on);
      if (b.dataset.label) b.lastChild.textContent = on ? ' In your favourites' : ' Add to favourites';
    });
    if (pins[id]) pins[id].getElement()?.firstChild?.classList.toggle('fav', favs.includes(id));
    counts();
  }
  function toggleCmp(id) {
    cmp = cmp.includes(id) ? cmp.filter((x) => x !== id) : [...cmp, id].slice(-3);
    store.set('dc-mock-compare', cmp); counts();
  }
  document.addEventListener('click', (e) => {
    const s = e.target.closest('[data-star]');
    if (s) { e.preventDefault(); e.stopPropagation(); toggleFav(s.dataset.star); return; }
    const c = e.target.closest('[data-cmp]');
    if (c) { e.preventDefault(); toggleCmp(c.dataset.cmp); c.setAttribute('aria-pressed', cmp.includes(c.dataset.cmp)); c.lastChild.textContent = cmp.includes(c.dataset.cmp) ? ' In compare' : ' Compare'; return; }
  });

  // ---------- home ----------
  let pins = {};
  function homePage() {
    rank();
    const pre = PRESETS.find((p) => FACTORS.every((f) => (+S.w[f.id] || 0) === p.w[f.id]));
    app.innerHTML = `
      <section class="intro">
        <h1>Places worth a look</h1>
        <p>Areas of Spain for cycling holidays and a holiday home, best first. Each is judged on the climbs nearby, the winter weather,
        flights from Edinburgh and Glasgow, quiet roads and walking. Choose your priorities, or open <b>Adjust</b> to fine-tune them.</p>
      </section>
      <div class="bar">
        <span class="bar-lab">Priorities</span>
        <div class="chips" role="group" aria-label="Priorities">
          ${PRESETS.map((p) => `<button type="button" class="chip" data-preset="${p.id}" aria-pressed="${pre && pre.id === p.id}">${esc(p.label)}</button>`).join('')}
        </div>
        <button type="button" class="btn ${adjustOpen ? 'primary' : ''}" id="adjust-btn" aria-expanded="${adjustOpen}">${adjustOpen ? 'Close Adjust' : 'Adjust…'}</button>
        <div class="chips where" role="group" aria-label="Where">
          ${WHERE.map((w) => `<button type="button" class="chip" data-where="${w.id}" aria-pressed="${S.where === w.id}">${esc(w.label)}</button>`).join('')}
        </div>
      </div>
      <div class="layout ${adjustOpen ? 'adjusting' : ''}">
        ${adjustOpen ? `<aside class="adjust" aria-label="Adjust the ranking">${adjustHtml()}</aside>` : ''}
        <section class="list" id="list" aria-label="Places, best first"></section>
        <div class="mapwrap"><div id="map" role="region" aria-label="Map of the places"></div><div id="inset" aria-label="Canary Islands"></div></div>
      </div>`;
    app.querySelectorAll('[data-preset]').forEach((b) => b.onclick = () => { S.w = { ...PRESETS.find((p) => p.id === b.dataset.preset).w }; save(); refresh(); });
    app.querySelectorAll('[data-where]').forEach((b) => b.onclick = () => { S.where = b.dataset.where; save(); refresh(true); });
    $('#adjust-btn').onclick = () => { adjustOpen = !adjustOpen; store.set('dc-mock-adjust', adjustOpen); route(); };
    if (adjustOpen) wireAdjust();
    redraw = (fit) => { drawList(); drawPins(fit); };
    drawMap(); drawList();
  }
  let redraw = null;   // the current page's response to a change of settings
  function refresh(fit) {
    const before = ORDER.map((a) => a.id);
    rank();
    prevOrder = before;
    app.querySelectorAll('[data-preset]').forEach((b) => b.setAttribute('aria-pressed', FACTORS.every((f) => (+S.w[f.id] || 0) === PRESETS.find((p) => p.id === b.dataset.preset).w[f.id])));
    app.querySelectorAll('[data-where]').forEach((b) => b.setAttribute('aria-pressed', S.where === b.dataset.where));
    if (adjustOpen) syncAdjust();
    if (redraw) redraw(fit);
  }
  function card(a) {
    const p = priceOf(a);
    const was = prevOrder ? prevOrder.indexOf(a.id) : -1;
    const move = prevOrder && was >= 0 && was + 1 !== a.rank ? (was + 1 > a.rank ? `<span class="move up">▲ ${was + 1 - a.rank}</span>` : `<span class="move down">▼ ${a.rank - was - 1}</span>`) : prevOrder && was < 0 ? '<span class="move up">New</span>' : '';
    return `<article class="card" data-id="${a.id}">
      ${move}
      <div class="rank" aria-label="Rank ${a.rank}">${a.rank}</div>
      <h2><a href="#/area/${a.id}">${esc(a.name)}</a></h2>
      ${starBtn(a)}
      <div class="sub">${esc(where(a))} · ${esc(a.setting)}${a.elev != null ? `, ${num(a.elev)} m up` : ''}</div>
      <div class="facts">
        <div class="fact">${ICON.sun}<div><b>${winterHigh(a)}° in January</b><span>${winterRide(a)} good riding days, Oct to May</span></div></div>
        <div class="fact">${ICON.mountain}<div><b>${a.near_n} big climbs</b><span>within 26 km by road</span></div></div>
        <div class="fact">${ICON.plane}<div><b>${a.yr ? `${esc(a.yr.name)}, ${mins(a.yr.min)}` : a.any ? `${esc(a.any.name)}, ${mins(a.any.min)}` : 'No direct flights near'}</b><span>${esc(flightsWord(a.yr || a.any))}</span></div></div>
        ${Object.keys(PRICE).length ? `<div class="fact">${ICON.home}<div><b>${p ? `About €${num(Math.round(p.eur_m2 / 50) * 50)} per m²` : 'No price yet'}</b><span>${p ? 'average of recent sales' : 'too few sales recorded'}</span></div></div>` : ''}
      </div>
      <div class="strip" aria-hidden="true">
        <div class="strip-cap">Afternoon warmth, month by month</div>
        <div class="strip-cells">${a.high.map((t) => `<i style="background:${tColour(t)}"></i>`).join('')}</div>
        <div class="strip-lab">${MONTHS.map((m) => `<span>${m[0]}</span>`).join('')}</div>
      </div>
      <div class="tags">${strengths(a).map((s) => `<span class="tag">${s}</span>`).join('')}</div>
    </article>`;
  }
  function drawList() {
    const list = $('#list'); if (!list) return;
    const items = ORDER.slice(0, shown);
    list.innerHTML = items.length ? items.map(card).join('') + (ORDER.length > shown ? `<button type="button" class="btn more" id="more">Show more places (${ORDER.length - shown} left)</button>` : '')
      : `<div class="empty">No places match these choices. Try fewer climbs, a wider price range or another area — or <button type="button" class="btn subtle" id="reset2">go back to our agreed balance</button>.</div>`;
    list.querySelectorAll('.card').forEach((c) => {
      c.onclick = (e) => { if (!e.target.closest('a,button')) location.hash = `#/area/${c.dataset.id}`; };
      c.onmouseenter = () => hl(c.dataset.id, true); c.onmouseleave = () => hl(c.dataset.id, false);
    });
    const m = $('#more'); if (m) m.onclick = () => { shown += 12; prevOrder = null; drawList(); drawPins(); };
    const r = $('#reset2'); if (r) r.onclick = () => { S = { ...DEFAULTS, w: { ...AGREED } }; save(); refresh(true); };
    setTimeout(() => { prevOrder = null; }, 0);
  }
  function hl(id, on) {
    const p = pins[id]; if (!p) return;
    p.getElement()?.firstChild?.classList.toggle('hl', on);
    if (on) p.setZIndexOffset(1000); else p.setZIndexOffset(0);
  }
  let inset = null;   // the Canaries, as on Spanish maps: a small inset, so the main map can stay close on the mainland
  const tiles = () => L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 17, attribution: '© OpenStreetMap contributors' });
  function drawMap() {
    map = L.map('map', { scrollWheelZoom: false, zoomSnap: 0.25, zoomControl: false });
    L.control.zoom({ position: 'topright' }).addTo(map);
    tiles().addTo(map);
    inset = L.map('inset', { zoomControl: false, attributionControl: false, dragging: false, scrollWheelZoom: false, doubleClickZoom: false, boxZoom: false, keyboard: false, touchZoom: false });
    tiles().addTo(inset);
    inset.fitBounds([[27.6, -18.2], [29.4, -13.4]]);
    map.on('unload', () => { inset.remove(); inset = null; });
    drawPins(true);
  }
  function drawPins(fit) {
    if (!map) return;
    Object.values(pins).forEach((p) => p.remove()); pins = {};
    const items = ORDER.slice(0, shown);
    const canary = (a) => a.lat < 30, mixed = items.some(canary) && items.some((a) => !canary(a));
    $('#inset').style.display = mixed ? '' : 'none';
    items.slice().reverse().forEach((a) => {
      const icon = L.divIcon({ className: '', html: `<div class="pin${favs.includes(a.id) ? ' fav' : ''}">${a.rank}</div>`, iconSize: [30, 30], iconAnchor: [15, 15] });
      const m = L.marker([a.lat, a.lon], { icon, title: `${a.rank}. ${a.name}`, keyboard: true }).addTo(mixed && canary(a) ? inset : map);
      m.on('click', () => {
        const c = app.querySelector(`.card[data-id="${a.id}"]`);
        if (c) { c.scrollIntoView({ behavior: 'smooth', block: 'center' }); c.classList.add('hl'); setTimeout(() => c.classList.remove('hl'), 1600); }
      });
      pins[a.id] = m;
    });
    if (fit !== false && items.length) {
      const b = L.latLngBounds(items.filter((a) => !mixed || !canary(a)).map((a) => [a.lat, a.lon]));
      map.fitBounds(b.pad(0.15), { maxZoom: 9 });
    }
  }

  // ---------- adjust ----------
  function adjustHtml() {
    const priced = Object.keys(PRICE).length;
    return `
      <button type="button" class="btn primary adjust-close" id="adjust-done">Done</button>
      <div><h2>Adjust</h2><p class="hint">Move a slider and the list re-orders straight away. Your settings are kept on this device.</p></div>
      <div class="group" style="border-top:0;padding-top:0">
        <h3>How much does each matter?</h3>
        ${FACTORS.map((f) => `<div class="w" data-w="${f.id}">
          <label class="w-top" for="w-${f.id}"><span>${f.label}</span><span class="w-word"></span></label>
          <input type="range" id="w-${f.id}" min="0" max="40" step="1" value="${S.w[f.id]}">
          <p>${f.what}</p></div>`).join('')}
      </div>
      <div class="group">
        <h3>Flights</h3>
        ${[['year_round', 'Only airports with flights all year'], ['seasonal', 'Also count summer-only routes (at half value)'], ['ignore', "Don't consider flights"]]
          .map(([v, l]) => `<label class="radio"><input type="radio" name="flights" value="${v}" ${S.flights === v ? 'checked' : ''}> ${l}</label>`).join('')}
      </div>
      <div class="group">
        <h3>Climbs</h3>
        <div class="stepper"><span>Must have at least</span><button type="button" id="mc-minus" aria-label="Fewer climbs">−</button><output id="mc">${S.minClimbs}</output><button type="button" id="mc-plus" aria-label="More climbs">+</button><span>big climbs</span></div>
        <p class="hint">Climbs of 300 m or more that start within 26 km by road.</p>
      </div>
      <div class="group">
        <h3>Surroundings</h3>
        <label class="check"><input type="checkbox" id="quieter" ${S.quieter ? 'checked' : ''}> Prefer quieter surroundings</label>
        <p class="hint">Places in or next to big towns and resort strips move down a little.</p>
      </div>
      ${priced ? `<div class="group">
        <h3>Home prices (private)</h3>
        <div class="price-in"><label>From € <input type="number" id="pmin" min="0" step="100" inputmode="numeric" value="${S.pmin ?? ''}"></label>
        <label>to € <input type="number" id="pmax" min="0" step="100" inputmode="numeric" value="${S.pmax ?? ''}"></label><span>per m²</span></div>
        <p class="hint">Average price of recent sales in the municipality. Leave empty to see everywhere.</p>
      </div>` : ''}
      <button type="button" class="btn" id="reset">Back to our agreed balance</button>`;
  }
  function syncAdjust() {
    FACTORS.forEach((f) => {
      const row = app.querySelector(`[data-w="${f.id}"]`); if (!row) return;
      const v = +S.w[f.id] || 0;
      row.querySelector('input').value = v;
      row.querySelector('.w-word').textContent = f.id === 'airport' && S.flights === 'ignore' ? 'Not counted' : wordFor(v);
      row.classList.toggle('off', v === 0);
    });
    const mc = $('#mc'); if (mc) mc.textContent = S.minClimbs;
  }
  function wireAdjust() {
    syncAdjust();
    FACTORS.forEach((f) => { $(`#w-${f.id}`).oninput = (e) => { S.w = { ...S.w, [f.id]: +e.target.value }; save(); refresh(); }; });
    app.querySelectorAll('input[name="flights"]').forEach((r) => r.onchange = () => { S.flights = r.value; save(); refresh(); });
    $('#mc-minus').onclick = () => { S.minClimbs = Math.max(1, S.minClimbs - 1); save(); refresh(); };
    $('#mc-plus').onclick = () => { S.minClimbs = Math.min(10, S.minClimbs + 1); save(); refresh(); };
    $('#quieter').onchange = (e) => { S.quieter = e.target.checked; save(); refresh(); };
    const pi = (id, k) => { const el = $(id); if (el) el.onchange = () => { S[k] = el.value ? +el.value : null; save(); refresh(true); }; };
    pi('#pmin', 'pmin'); pi('#pmax', 'pmax');
    $('#reset').onclick = () => { S = { ...DEFAULTS, w: { ...AGREED } }; save(); route(); };
    $('#adjust-done').onclick = () => { adjustOpen = false; store.set('dc-mock-adjust', false); route(); };
  }

  // ---------- area page ----------
  function areaPage(a) {
    rank();
    const p = priceOf(a);
    const ap = a.yr || a.any;
    const inOrder = ORDER.indexOf(a);
    const prev = inOrder > 0 ? ORDER[inOrder - 1] : null, next = inOrder >= 0 && inOrder < ORDER.length - 1 ? ORDER[inOrder + 1] : null;
    const yearRow = (label, vals, fmt, cls) => `<div class="rl">${label}</div>${vals.map((v, m) => `<div class="c ${cls(v, m)}" ${cls(v, m) === 't' ? `style="background:${tColour(v)}"` : ''}>${fmt(v)}</div>`).join('')}`;
    const maxDays = 31;
    const barRow = (label, vals, sun) => `<div class="rl">${label}</div>${vals.map((v) => `<div class="bars${sun ? ' sun' : ''}" title="${num(v)} days"><i style="height:${Math.max(2, (v / maxDays) * 100)}%"></i></div>`).join('')}`;
    const rate = (k, label, what) => `<div class="rating"><b>${label}</b><span class="dots" aria-label="${level(comp(a, k))}">${[1, 2, 3, 4, 5].map((i) => `<i class="${i <= dots(comp(a, k)) ? 'on' : ''}"></i>`).join('')}</span><span class="what">${level(comp(a, k))}${what ? ` · ${what}` : ''}</span></div>`;
    const q = encodeURIComponent(`${a.muni || a.name}, ${a.province}`);
    app.innerHTML = `
      <a class="btn subtle back" href="#/">← All places</a>
      <div class="ahead">
        <div><h1>${esc(a.name)}</h1><div class="sub">${esc(where(a))} · ${esc(a.setting)}${a.elev != null ? `, ${num(a.elev)} m up` : ''}${a.rank ? ` · number ${a.rank} on your list` : ''}</div></div>
        <div class="actions">
          <button type="button" class="btn" data-star="${a.id}" data-label="1" aria-pressed="${favs.includes(a.id)}"><svg class="ico star-ico" viewBox="0 0 24 24"><path d="M12 3l2.8 5.7 6.2.9-4.5 4.4 1 6.2L12 17.3 6.5 20.2l1-6.2L3 9.6l6.2-.9z"/></svg> ${favs.includes(a.id) ? 'In your favourites' : 'Add to favourites'}</button>
          <button type="button" class="btn" data-cmp="${a.id}" aria-pressed="${cmp.includes(a.id)}">${ICON.compare.replace('<svg', '<svg class="ico"')} ${cmp.includes(a.id) ? 'In compare' : 'Compare'}</button>
        </div>
      </div>
      <div class="tiles">
        <div class="tile"><div class="k">January afternoons</div><div class="v">${winterHigh(a)}°C</div><div class="s">typical high, here at ${num(a.elev)} m</div></div>
        <div class="tile"><div class="k">Good riding days</div><div class="v">${num(a.ride_year)}</div><div class="s">a year, ${winterRide(a)} of them Oct to May</div></div>
        <div class="tile"><div class="k">Big climbs nearby</div><div class="v">${a.near_n}</div><div class="s">300 m or more, within 26 km</div></div>
        <div class="tile"><div class="k">Nearest useful airport</div><div class="v">${ap ? mins(ap.min) : '–'}</div><div class="s">${ap ? `${esc(ap.name)}, ${esc(flightsWord(ap))}` : 'none with direct flights'}</div></div>
        ${Object.keys(PRICE).length ? `<div class="tile"><div class="k">Homes</div><div class="v">${p ? `€${num(Math.round(p.eur_m2 / 50) * 50)}` : '–'}</div><div class="s">${p ? 'per m², recent sales average' : 'too few sales recorded'}</div></div>` : ''}
      </div>
      <div class="agrid">
        <div>
          <section class="sec">
            <h2>${ICON.sun} The year here</h2>
            <p class="muted">A typical year (2017–2025). Riding days are counted at the height of the nearby climbs; the rest are for the village itself.</p>
            <div class="year" role="table" aria-label="Month by month">
              <div></div>${MONTHS.map((m, i) => `<div class="h${WINTER.includes(i) ? ' win' : ''}">${m}</div>`).join('')}
              ${yearRow('Afternoon high', a.high, (v) => `${Math.round(v)}°`, () => 't')}
              ${barRow('Good riding days', a.ride)}
              ${yearRow('', a.ride, (v) => num(v), () => 'n')}
              ${barRow('Warm enough to sit out', a.sit, true)}
              ${yearRow('', a.sit, (v) => num(v), () => 'n')}
              ${yearRow('Dry days', a.dry, (v) => num(v), () => 'n')}
            </div>
            <p class="muted" style="font-size:.85rem">“Warm enough to sit out”: a dry day reaching 18 °C. “Good riding day”: dry, at least 11 °C and not too windy at the climbs' height.${a.own_weather ? '' : ' Weather borrowed from a nearby point for now; the full download finishes soon.'}</p>
          </section>
          <section class="sec">
            <h2>${ICON.mountain} Cycling</h2>
            ${rate('climbing', 'Climbing', `${a.near_n} big climbs within reach`)}
            ${rate('quiet', 'Quiet roads', `${num(a.m.quiet_km)} km of quiet roads nearby`)}
            ${rate('flat', 'Easy rides', `${num(a.m.flat_km)} km of flat or rolling road`)}
            ${rate('gravel', 'Gravel', `${num(a.m.gravel_km)} km of tracks`)}
            ${rate('weather', 'Riding weather', 'from October to May')}
            <h3>The biggest climbs nearby</h3>
            <table class="climbs"><thead><tr><th>Climb</th><th class="n">Climbing</th><th class="n">Length</th><th class="n">Average</th><th class="n">From here</th></tr></thead>
            <tbody>${a.climbs.map((c) => `<tr><td><b>${esc(c.name)}</b>${c.from && c.from !== c.name ? `<span class="from">from ${esc(c.from)}</span>` : ''}</td><td class="n">${num(c.gain)} m</td><td class="n">${num(c.km, 1)} km</td><td class="n">${num(c.grade, 1)}%</td><td class="n">${num(c.away_km)} km</td></tr>`).join('')}</tbody></table>
          </section>
        </div>
        <div>
          <section class="sec">
            <h2>${ICON.map} Where it is</h2>
            <div class="amap" id="amap" role="region" aria-label="Map of ${esc(a.name)} and its climbs"></div>
            <p class="muted" style="font-size:.85rem">The orange lines join the foot and top of each big climb (straight lines, not the road).</p>
            <div class="links">
              <a class="btn" href="https://www.google.com/maps/@${a.lat},${a.lon},14z" target="_blank" rel="noopener">Open in Google Maps</a>
              <a class="btn" href="https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${a.lat},${a.lon}" target="_blank" rel="noopener">Street View</a>
            </div>
          </section>
          <section class="sec">
            <h2>${ICON.plane} Getting there</h2>
            ${a.yr ? `<p><b>${esc(a.yr.name)}</b> is ${mins(a.yr.min)} away by car, with direct flights ${esc(flightsWord(a.yr))}.</p>` : '<p>No airport with all-year direct flights from Edinburgh or Glasgow is within easy reach.</p>'}
            ${a.any && (!a.yr || a.any.code !== a.yr.code) ? `<p><b>${esc(a.any.name)}</b> is ${mins(a.any.min)} away, with direct flights ${esc(flightsWord(a.any))}.</p>` : ''}
          </section>
          <section class="sec">
            <h2>${ICON.walk} Walking and running</h2>
            ${rate('walking', 'Walking', `${num(a.m.walk_km)} km of paths and tracks`)}
            ${a.m.peaks ? `<p>${num(a.m.peaks)} hills and peaks marked on the map within reach, to walk or run up.</p>` : ''}
          </section>
          <section class="sec">
            <h2>${ICON.fork} Eating out</h2>
            <p class="soon">Coming next: restaurants, cafés and markets within a short walk or drive.</p>
          </section>
          <section class="sec">
            <h2>${ICON.home} Homes</h2>
            ${p ? `<p>Homes in ${esc(p.name)} sold for <b>about €${num(Math.round(p.eur_m2 / 50) * 50)} per m²</b> on average over the last 12 months (all homes: flats, town houses and country houses together). A broad guide only; real prices depend on the property.</p>`
              : Object.keys(PRICE).length ? '<p>No price yet: too few sales recorded in this municipality.</p>' : '<p class="soon">Prices appear in the private family copy.</p>'}
            <div class="links">
              <a class="btn" href="https://www.google.com/search?q=${q}+casas+en+venta+idealista" target="_blank" rel="noopener">Homes for sale (Idealista)</a>
              <a class="btn" href="https://www.google.com/search?q=${q}+property+for+sale" target="_blank" rel="noopener">Search the web</a>
            </div>
          </section>
        </div>
      </div>
      <nav class="pager" aria-label="Next and previous places">
        ${prev ? `<a class="btn" href="#/area/${prev.id}">← ${prev.rank}. ${esc(prev.name)}</a>` : '<span></span>'}
        ${next ? `<a class="btn" href="#/area/${next.id}">${next.rank}. ${esc(next.name)} →</a>` : ''}
      </nav>`;
    window.scrollTo(0, 0);
    map = L.map('amap', { scrollWheelZoom: false });
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 17, attribution: '© OpenStreetMap contributors' }).addTo(map);
    const pts = [[a.lat, a.lon]];
    a.climbs.forEach((c) => {
      L.polyline([c.foot, c.top], { color: '#c4622d', weight: 4, opacity: 0.85 }).addTo(map).bindTooltip(`${c.name}: ${num(c.gain)} m`);
      L.circleMarker(c.top, { radius: 5, color: '#c4622d', fillColor: '#fff', fillOpacity: 1, weight: 2 }).addTo(map);
      pts.push(c.foot, c.top);
    });
    L.marker([a.lat, a.lon], { icon: L.divIcon({ className: '', html: `<div class="pin">${a.rank || '•'}</div>`, iconSize: [30, 30], iconAnchor: [15, 15] }), title: a.name }).addTo(map);
    map.fitBounds(L.latLngBounds(pts).pad(0.1));
  }

  // ---------- favourites ----------
  function favouritesPage() {
    rank();
    const list = favs.map((id) => byId[id]).filter(Boolean);
    app.innerHTML = `<section class="intro"><h1>Your favourites</h1>
      <p>Places you've starred. They're kept on this device. Tick up to three to compare side by side.</p></section>
      ${list.length ? `<div class="list" id="list">${list.map((a) => { a.rank = a.rank || '–'; return card(a); }).join('')}</div>
        <p style="margin-top:18px"><a class="btn primary" href="#/compare" id="cmp-favs">Compare ${list.length > 3 ? 'the first three' : list.length > 1 ? 'these' : 'with others'}</a></p>`
        : '<div class="empty">No favourites yet. Tap the ☆ on any place to add it here.</div>'}`;
    app.querySelectorAll('.card').forEach((c) => { c.onclick = (e) => { if (!e.target.closest('a,button')) location.hash = `#/area/${c.dataset.id}`; }; });
    const b = $('#cmp-favs'); if (b) b.onclick = () => { cmp = list.slice(0, 3).map((a) => a.id); store.set('dc-mock-compare', cmp); };
  }

  // ---------- compare ----------
  function comparePage() {
    rank();
    const list = cmp.map((id) => byId[id]).filter(Boolean);
    const candidates = [...favs.map((id) => byId[id]).filter(Boolean), ...ORDER.slice(0, 8)].filter((a, i, arr) => arr.indexOf(a) === i);
    const rows = [
      ['Rank (based on current priorities)', (a) => a.rank || '–', (a) => -(a.rank || 999)],
      ['January afternoons', (a) => `${winterHigh(a)}°C`, (a) => a.high[0]],
      ['Good riding days, Oct to May', (a) => winterRide(a), winterRide],
      ['Warm enough to sit out, Oct to May', (a) => Math.round(WINTER.reduce((s, m) => s + a.sit[m], 0)) + ' days', (a) => WINTER.reduce((s, m) => s + a.sit[m], 0)],
      ['Big climbs nearby', (a) => a.near_n, (a) => a.near_n],
      ['Quiet roads', (a) => level(a.c.quiet), (a) => a.c.quiet],
      ['Walking', (a) => level(a.c.walking), (a) => a.c.walking],
      ['Airport', (a) => (a.yr ? `${esc(a.yr.name)}, ${mins(a.yr.min)}` : a.any ? `${esc(a.any.name)} (summer), ${mins(a.any.min)}` : '–'), (a) => -(a.yr ? a.yr.min : 999)],
      ['Setting', (a) => `${esc(a.setting)}${a.elev != null ? `, ${num(a.elev)} m` : ''}`, null],
      ...(Object.keys(PRICE).length ? [['Homes, € per m²', (a) => (priceOf(a) ? `€${num(Math.round(priceOf(a).eur_m2 / 50) * 50)}` : '–'), (a) => (priceOf(a) ? -priceOf(a).eur_m2 : null)]] : []),
    ];
    app.innerHTML = `<section class="intro"><h1>Compare</h1><p>Up to three places side by side. The best in each row is shaded.</p></section>
      <div class="pick" role="group" aria-label="Choose places to compare">${candidates.map((a) => `<button type="button" class="chip" data-pick="${a.id}" aria-pressed="${cmp.includes(a.id)}">${favs.includes(a.id) ? '★ ' : ''}${esc(a.name)}</button>`).join('')}</div>
      ${list.length ? `<div class="cmp-wrap"><table class="cmp"><thead><tr><th></th>${list.map((a) => `<th scope="col"><a href="#/area/${a.id}">${esc(a.name)}</a><div class="muted" style="font:400 .9rem var(--sans)">${esc(a.province)}</div></th>`).join('')}</tr></thead>
        <tbody>${rows.map(([label, f, key]) => {
          const vals = key ? list.map(key) : []; const best = key && list.length > 1 ? Math.max(...vals.filter((v) => v != null)) : null;
          return `<tr><th scope="row">${label}</th>${list.map((a, i) => `<td class="${best != null && vals[i] === best ? 'best' : ''}">${f(a)}</td>`).join('')}</tr>`;
        }).join('')}</tbody></table></div>` : '<div class="empty">Choose two or three places above to compare them.</div>'}`;
    app.querySelectorAll('[data-pick]').forEach((b) => b.onclick = () => { toggleCmp(b.dataset.pick); comparePage(); });
  }

  // ---------- explore: every 5 km point in Spain, coloured by how well it suits the current choices ----------
  const FRAMES = [
    { id: 'spain', label: 'All Spain', b: [[35.9, -9.4], [43.8, 4.4]] }, { id: 'malaga', label: 'Málaga & Granada', b: [[36.55, -5.4], [37.4, -3.1]] },
    { id: 'blanca', label: 'Costa Blanca', b: [[38.3, -0.75], [39.0, 0.3]] }, { id: 'girona', label: 'Girona', b: [[41.7, 2.3], [42.45, 3.3]] },
    { id: 'pyrenees', label: 'Pyrenees', b: [[42.15, -1.6], [42.85, 2.2]] }, { id: 'mallorca', label: 'Mallorca', b: [[39.25, 2.3], [40.0, 3.5]] },
    { id: 'canaries', label: 'Canary Islands', b: [[27.6, -18.2], [29.3, -13.4]] },
  ];
  const BANDS = ['Limited', 'Fair', 'Good', 'Very good', 'Excellent'];
  const CUTS = [0.2, 0.5, 0.8, 0.95];   // share of qualifying points below each band: the top 5% are Excellent
  let G = null, GRID_P = null, GRID_EUR = null;
  const loadGrid = () => GRID_P || (GRID_P = fetch('data/grid.json').then((r) => r.json()).then((g) => { G = g; G.N = g.lat.length; return g; }));
  const gComp = (i, k) => {
    if (k !== 'airport') return G[k][i] || 0;
    const yr = airportCurve(G.ym[i]);
    return S.flights === 'seasonal' ? Math.max(yr, D.meta.seasonal_credit * airportCurve(G.am[i])) : yr;
  };
  const gPrice = (i) => (GRID_EUR ? GRID_EUR[i] : null);
  const gPasses = (i) => {
    if (G.n[i] < S.minClimbs) return 'climbs';
    if ((S.pmin || S.pmax) && GRID_EUR) {
      const p = gPrice(i);
      if (p == null || (S.pmin && p < S.pmin) || (S.pmax && p > S.pmax)) return 'price';
    }
    return '';
  };
  function gScore() {
    const tot = new Float32Array(G.N), fail = new Array(G.N);
    let wsum = 0; FACTORS.forEach((f) => { if (!(f.id === 'airport' && S.flights === 'ignore')) wsum += +S.w[f.id] || 0; });
    for (let i = 0; i < G.N; i++) {
      let s = 0;
      for (const f of FACTORS) { if (f.id === 'airport' && S.flights === 'ignore') continue; s += (+S.w[f.id] || 0) * gComp(i, f.id); }
      tot[i] = (wsum ? s / wsum * 100 : 0) * (S.quieter ? 1 - D.meta.built.strength * (G.built[i] || 0) : 1);
      fail[i] = gPasses(i);
    }
    const ok = []; for (let i = 0; i < G.N; i++) if (!fail[i]) ok.push(tot[i]);
    ok.sort((a, b) => a - b);
    const cut = CUTS.map((q) => (ok.length ? ok[Math.min(ok.length - 1, Math.floor(q * ok.length))] : Infinity));
    const band = new Int8Array(G.N);
    for (let i = 0; i < G.N; i++) band[i] = fail[i] ? -1 : cut.filter((c) => tot[i] >= c).length;
    return { tot, fail, band, n: ok.length };
  }
  const ramp = () => { const cs = getComputedStyle(document.documentElement); return [0, 1, 2, 3, 4].map((k) => cs.getPropertyValue(`--r${k}`).trim()); };

  function explorePage() {
    document.body.classList.add('exploring');
    const pre = PRESETS.find((p) => FACTORS.every((f) => (+S.w[f.id] || 0) === p.w[f.id]));
    app.innerHTML = `
      <section class="xhead">
        <div><h1>Explore the map</h1><p class="muted">Every spot in Spain, coloured by how well it suits your choices. Wander, zoom in, tap anywhere.</p></div>
        <div class="bar">
          <span class="bar-lab">Priorities</span>
          <div class="chips" role="group" aria-label="Priorities">
            ${PRESETS.map((p) => `<button type="button" class="chip" data-preset="${p.id}" aria-pressed="${pre && pre.id === p.id}">${esc(p.label)}</button>`).join('')}
          </div>
          <button type="button" class="btn ${adjustOpen ? 'primary' : ''}" id="adjust-btn" aria-expanded="${adjustOpen}">${adjustOpen ? 'Close Adjust' : 'Adjust…'}</button>
        </div>
        <div class="chips" role="group" aria-label="Go to">${FRAMES.map((f) => `<button type="button" class="chip small" data-frame="${f.id}">${esc(f.label)}</button>`).join('')}</div>
      </section>
      ${adjustOpen ? `<aside class="adjust drawer" aria-label="Adjust the colours">${adjustHtml()}</aside>` : ''}
      <div class="xwrap">
        <div id="xmap" role="region" aria-label="Map of Spain coloured by suitability"></div>
        <div class="legend" id="legend"></div>
        <div class="xinfo" id="xinfo" hidden></div>
        <div class="xloading" id="xloading">Colouring in Spain…</div>
      </div>`;
    rank();
    app.querySelectorAll('[data-preset]').forEach((b) => b.onclick = () => { S.w = { ...PRESETS.find((p) => p.id === b.dataset.preset).w }; save(); refresh(); });
    $('#adjust-btn').onclick = () => { adjustOpen = !adjustOpen; store.set('dc-mock-adjust', adjustOpen); route(); };
    if (adjustOpen) wireAdjust();
    // the map fills the rest of the screen, whatever the header and chips take (they wrap on an upright iPad)
    const fit = () => { const w = $('.xwrap'); if (w) { w.style.height = `${Math.max(420, innerHeight - w.getBoundingClientRect().top - window.scrollY - 16)}px`; if (map) map.invalidateSize(); } };
    fit(); window.onresize = fit;
    const view = store.get('dc-mock-view', null);
    map = L.map('xmap', { zoomSnap: 0.5, preferCanvas: true, zoomControl: false });
    L.control.zoom({ position: 'topright' }).addTo(map);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 17, attribution: '© OpenStreetMap contributors' }).addTo(map);
    if (view) map.setView(view.c, view.z); else map.fitBounds(FRAMES[0].b);
    map.on('moveend', () => store.set('dc-mock-view', { c: map.getCenter(), z: map.getZoom() }));
    app.querySelectorAll('[data-frame]').forEach((b) => b.onclick = () => map.flyToBounds(FRAMES.find((f) => f.id === b.dataset.frame).b, { duration: 1.2 }));
    const thisMap = map;
    loadGrid().then(() => { if (map === thisMap) drawGrid(); });
  }

  function drawGrid() {
    const renderer = L.canvas({ padding: 0.3 });
    const dots = new Array(G.N);
    let R = gScore(), colours = ramp(), sel = null;
    $('#xloading').remove();
    const rad = () => Math.max(2, Math.min(40, 2700 / (156543 * Math.cos(40 * Math.PI / 180) / 2 ** map.getZoom())));
    const style = (i) => (R.band[i] < 0 ? { fillColor: '#8a9097', fillOpacity: 0.18 } : { fillColor: colours[R.band[i]], fillOpacity: 0.85 });
    const order = [...Array(G.N).keys()].sort((a, b) => R.tot[a] - R.tot[b]);
    for (const i of order) dots[i] = L.circleMarker([G.lat[i], G.lon[i]], { renderer, radius: rad(), stroke: false, interactive: false, ...style(i) }).addTo(map);
    map.on('zoomend', () => { const r = rad(); dots.forEach((d) => d.setRadius(r)); });
    const pinLayer = L.layerGroup().addTo(map);
    const drawTop = () => {
      pinLayer.clearLayers();
      ORDER.slice(0, 12).forEach((a) => L.marker([a.lat, a.lon], { icon: L.divIcon({ className: '', html: `<div class="pin">${a.rank}</div>`, iconSize: [30, 30], iconAnchor: [15, 15] }), title: `${a.rank}. ${a.name}`, zIndexOffset: 1000 })
        .on('click', () => { location.hash = `#/area/${a.id}`; }).addTo(pinLayer));
    };
    const legend = () => {
      $('#legend').innerHTML = `<b>How well it suits you</b>
        <div class="lg-row">${BANDS.map((b, k) => `<span><i style="background:${colours[k]}"></i>${b}</span>`).join('')}</div>
        <div class="lg-row"><span><i style="background:#8a9097;opacity:.4"></i>Doesn't meet your must-haves</span><span><span class="pin mini">1</span> Top 12 places</span></div>
        <p>Colours compare places with each other: the best 5% are “Excellent”.</p>`;
    };
    // nearest point to a screen position, within reach of a finger
    const nearest = (latlng, px) => {
      const p0 = map.latLngToContainerPoint(latlng); let best = -1, bd = px * px;
      const b = map.getBounds().pad(0.05);
      for (let i = 0; i < G.N; i++) {
        if (G.lat[i] < b.getSouth() || G.lat[i] > b.getNorth() || G.lon[i] < b.getWest() || G.lon[i] > b.getEast()) continue;
        const p = map.latLngToContainerPoint([G.lat[i], G.lon[i]]); const d = (p.x - p0.x) ** 2 + (p.y - p0.y) ** 2;
        if (d < bd) { bd = d; best = i; }
      }
      return best;
    };
    const tip = L.tooltip({ direction: 'top', offset: [0, -6], className: 'xtip' });
    let raf = 0;
    if (matchMedia('(hover: hover)').matches) map.on('mousemove', (e) => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        if (!map) return;
        const i = nearest(e.latlng, Math.max(10, rad() + 4));
        if (i < 0) { map.closeTooltip(tip); return; }
        tip.setLatLng([G.lat[i], G.lon[i]]).setContent(`<b>${esc(G.names[G.nm[i]])}</b> · ${R.band[i] < 0 ? 'must-haves not met' : BANDS[R.band[i]]}`);
        if (!map.hasLayer(tip)) tip.addTo(map);
      });
    });
    map.on('mouseout', () => map.closeTooltip(tip));
    const ring = L.circleMarker([0, 0], { radius: 12, color: '#1d2126', weight: 3, fill: false, interactive: false });
    const close = () => { $('#xinfo').hidden = true; ring.remove(); sel = null; };
    map.on('click', (e) => { const i = nearest(e.latlng, Math.max(18, rad() + 6)); if (i >= 0) info(i); else close(); });
    function info(i) {
      sel = i; ring.setLatLng([G.lat[i], G.lon[i]]).addTo(map);
      const m = G.mu[i] >= 0 ? G.munis[G.mu[i]] : null;
      const sub = [m && m[0] !== G.names[G.nm[i]] ? m[0] : null, m ? m[1] : null].filter(Boolean).join(', ');
      const apc = (k) => (k >= 0 ? G.codes[k] : null);
      const yr = apc(G.yc[i]), any = apc(G.ac[i]);
      const ap = yr ? { ...D.meta.airports[yr], min: G.ym[i] } : any ? { ...D.meta.airports[any], min: G.am[i] } : null;
      const p = gPrice(i);
      const tags = FACTORS.filter((f) => f.id !== 'airport' && (G[f.id][i] || 0) >= 0.6).sort((x, y) => G[y.id][i] - G[x.id][i]).slice(0, 3)
        .map((f) => ({ climbing: 'Great climbing', weather: 'Sunny riding winters', quiet: 'Quiet roads', walking: 'Good walking', flat: 'Easy rides', gravel: 'Gravel tracks' }[f.id]));
      let near = null, nd = 1e9;
      A.forEach((a) => { const d = Math.hypot(a.lat - G.lat[i], (a.lon - G.lon[i]) * Math.cos(G.lat[i] * Math.PI / 180)) * 111.2; if (d < nd) { nd = d; near = a; } });
      const band = R.band[i];
      $('#xinfo').innerHTML = `
        <button type="button" class="xclose" aria-label="Close">×</button>
        <h2>${esc(G.names[G.nm[i]])}</h2>
        ${sub ? `<div class="sub muted">${esc(sub)}</div>` : ''}
        <div class="band" style="${band >= 0 ? `background:${colours[band]};color:${band >= 3 ? '#fff' : '#1d2126'}` : ''}">${band >= 0 ? BANDS[band] : R.fail[i] === 'climbs' ? `Only ${G.n[i]} big climb${G.n[i] === 1 ? '' : 's'} within reach` : 'Outside your price range'}</div>
        <ul class="xfacts">
          <li>${ICON.mountain}<span><b>${G.n[i]} big climbs</b> within 26 km</span></li>
          ${G.wr[i] != null ? `<li>${ICON.sun}<span><b>${num(G.wr[i])} good riding days</b> a year</span></li>` : ''}
          <li>${ICON.plane}<span>${ap ? `<b>${esc(ap.name)}, ${mins(ap.min)}</b> · ${esc(flightsWord(ap))}` : 'No airport with direct flights near'}</span></li>
          ${GRID_EUR ? `<li>${ICON.home}<span>${p ? `<b>About €${num(Math.round(p / 50) * 50)} per m²</b>` : 'No price looked up here yet'}</span></li>` : ''}
        </ul>
        ${tags.length ? `<div class="tags">${tags.map((t) => `<span class="tag">${t}</span>`).join('')}</div>` : ''}
        <div class="xlinks">
          ${near && nd < 25 ? `<a class="btn primary" href="#/area/${near.id}">${nd < 2 ? `Open ${esc(near.name)}` : `Nearest listed place: ${esc(near.name)}, ${num(nd)} km`} →</a>` : '<span class="muted" style="font-size:.9rem">Not near any of the listed places yet.</span>'}
          <a class="btn" href="https://www.google.com/maps/@${G.lat[i]},${G.lon[i]},13z" target="_blank" rel="noopener">Google Maps</a>
        </div>`;
      $('#xinfo').hidden = false;
      $('.xclose').onclick = close;
    }
    legend(); drawTop();
    redraw = () => {
      R = gScore(); colours = ramp();
      for (let i = 0; i < G.N; i++) dots[i].setStyle(style(i));
      legend(); drawTop(); if (sel != null) info(sel);
    };
  }

  // ---------- about ----------
  function aboutPage() {
    app.innerHTML = `<section class="prose">
      <h1>About this site</h1>
      <p>It helps us find areas of Spain that suit our cycling holidays, and perhaps a holiday home. Every place is judged the same way, from open data, so the list is a fair starting point for a closer look, not a verdict.</p>
      <h2>How places are judged</h2>
      <ul>
        <li><b>Climbing:</b> climbs of 300 m or more whose foot is within 26 km by road.</li>
        <li><b>Riding weather:</b> days that are dry, at least 11 °C and not too windy, at the height of those climbs, mostly October to May.</li>
        <li><b>Flights:</b> the drive to an airport with direct flights from Edinburgh or Glasgow.</li>
        <li><b>Quiet roads, walking, easy rides and gravel:</b> how much of each lies within reach, from OpenStreetMap.</li>
        <li><b>Quieter surroundings:</b> places in or beside big towns and resort strips move down a little.</li>
      </ul>
      <p>In this mock-up the list holds the best ${A.length} areas under the agreed balance; the real site will rank every area of Spain.</p>
      <h2>Sources</h2>
      <p>Map data © OpenStreetMap contributors (ODbL). Terrain: Copernicus DEM GLO-30. Land cover: ESA WorldCover 2021. Weather: Open-Meteo historical archive (2017–2025). Flights checked ${esc(D.meta.airports_status.slice(8, 19))}.${Object.keys(PRICE).length ? ' Home prices: Portal Estadístico del Notariado, for personal and family use only.' : ''}</p>
    </section>`;
  }

  // ---------- start ----------
  Promise.all([
    fetch('data/areas.json').then((r) => r.json()),
    fetch('data/prices.json').then((r) => (r.ok ? r.json() : null)).catch(() => null),
  ]).then(([d, pr]) => {
    D = d; A = d.areas; A.forEach((a) => { byId[a.id] = a; });
    if (pr && pr.prices) PRICE = pr.prices;
    if (pr && pr.grid_eur) GRID_EUR = pr.grid_eur;
    favs = favs.filter((id) => byId[id]); cmp = cmp.filter((id) => byId[id]);
    window.addEventListener('hashchange', route);
    route();
  }).catch((e) => { app.innerHTML = `<p class="loading">Couldn't load the places (${esc(e.message)}).</p>`; });
})();
