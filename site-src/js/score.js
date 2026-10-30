// Cycling-base score explorer (docs/cycling-score-spec.md section 7a). Components are precomputed per base
// (pipeline/score/score_export.py); this page applies the weights, the gate and the flights mode, live.
(() => {
  const CFG = window.DC_SCORE;
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
  const num = (x, d = 0) => (x == null ? '–' : x.toLocaleString('en-GB', { maximumFractionDigits: d, minimumFractionDigits: d }));
  const COMPS = [
    { id: 'climbing', label: 'Climbing' }, { id: 'weather', label: 'Weather at the climbs' }, { id: 'airport', label: 'Airport' },
    { id: 'quiet', label: 'Quiet roads' }, { id: 'walking', label: 'Walking' }, { id: 'flat', label: 'Flat / rolling' }, { id: 'gravel', label: 'Gravel' },
  ];
  const AGREED = { climbing: 35, weather: 20, airport: 13, quiet: 12, walking: 10, flat: 5, gravel: 5 };
  const PRESETS = [
    { id: 'agreed', label: 'Agreed defaults', w: AGREED },
    { id: 'weather', label: 'Weather first', w: { climbing: 20, weather: 35, airport: 15, quiet: 12, walking: 10, flat: 4, gravel: 4 } },
    { id: 'climbing', label: 'Climbing only', w: { climbing: 100, weather: 0, airport: 0, quiet: 0, walking: 0, flat: 0, gravel: 0 } },
  ];
  const FLIGHTS = [
    { id: 'year_round', label: 'Year-round direct only', def: 'The agreed rule: only airports with direct flights all year count. Palma is seasonal, so Mallorca gets the minimum.' },
    { id: 'seasonal', label: 'Seasonal at half credit', def: 'Airports with summer-only direct flights count at half (e.g. Palma, Girona, Reus).' },
    { id: 'ignore', label: 'Ignore flights', def: 'The airport factor is left out of the total.' },
  ];
  const FRAMES = [
    { id: 'spain', label: 'All Spain', b: [[35.9, -9.4], [43.8, 4.4]] }, { id: 'mallorca', label: 'Mallorca', b: [[39.25, 2.3], [40.0, 3.5]] },
    { id: 'girona', label: 'Girona', b: [[41.7, 2.3], [42.45, 3.3]] }, { id: 'pyrenees', label: 'Pyrenees', b: [[42.15, -1.6], [42.85, 2.2]] },
    { id: 'blanca', label: 'Costa Blanca', b: [[38.3, -0.75], [39.0, 0.3]] }, { id: 'malaga', label: 'Málaga & Granada', b: [[36.55, -5.4], [37.4, -3.1]] },
    { id: 'canaries', label: 'Canaries', b: [[27.6, -18.2], [29.3, -13.4]] },
  ];
  const DEFAULTS = { w: AGREED, on: Object.fromEntries(COMPS.map((c) => [c.id, true])), flights: 'year_round', gate: true, gateN: 3, built: true, builtS: 20, pmin: null, pmax: null, ponly: false, spread: true, frame: 'spain', sel: null };
  const KEY = 'dc-score-' + CFG.region;

  // ---------- params (remembered in this browser only) ----------
  let P;
  try { P = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { P = {}; }
  P = { ...DEFAULTS, ...P, w: { ...AGREED, ...(P.w || {}) }, on: { ...DEFAULTS.on, ...(P.on || {}) } };
  if (!FLIGHTS.some((f) => f.id === P.flights)) P.flights = DEFAULTS.flights;
  if (!FRAMES.some((f) => f.id === P.frame)) P.frame = DEFAULTS.frame;
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(P)); } catch (e) { /* private mode: not remembered */ } };

  let PR = null, PM = null;   // private prices (CFG.prices only): municipality slot per base, and the municipalities
  let D, B, C, N, comp, order = [], rankOf, total, eligible, map, markers = [], selLayer, frameShown = null;

  const airportCurve = (m) => (m == null ? 0.15 : m <= 60 ? 1 : m <= 120 ? 1 - 0.5 * (m - 60) / 60 : 0.15 + 0.35 * Math.exp(-(m - 120) / 60));
  const priceOf = (i) => (PR && PR[i] >= 0 ? PM[PR[i]] : null);
  const priceOk = (i) => {
    if (!PR) return true;
    const m = priceOf(i);
    if (!m) return !P.ponly;
    return (P.pmin == null || m.eur_m2 >= P.pmin) && (P.pmax == null || m.eur_m2 <= P.pmax);
  };
  const builtF = () => (P.built ? P.builtS / 100 : 0);   // largest built-up penalty, as a fraction of the score
  const weights = () => Object.fromEntries(COMPS.map((c) => [c.id, P.on[c.id] && !(c.id === 'airport' && P.flights === 'ignore') ? +P.w[c.id] : 0]));
  const kmBetween = (i, j) => Math.hypot(B.lat[i] - B.lat[j], (B.lon[i] - B.lon[j]) * Math.cos(B.lat[i] * Math.PI / 180)) * 111.2;

  // ---------- scoring ----------
  const score = () => {
    const air = new Float64Array(N);
    for (let i = 0; i < N; i++) {
      const yr = airportCurve(B.yr_min[i]);
      air[i] = P.flights === 'seasonal' ? Math.max(yr, D.seasonal_credit * airportCurve(B.any_min[i])) : yr;
    }
    comp = { ...comp, airport: air };
    const w = weights(), wsum = Object.values(w).reduce((a, b) => a + b, 0);
    total = new Float64Array(N); eligible = new Uint8Array(N);
    for (let i = 0; i < N; i++) {
      let s = 0;
      for (const c of COMPS) if (w[c.id]) s += w[c.id] * (comp[c.id][i] || 0);
      total[i] = (wsum ? (s / wsum) * 100 : 0) * (1 - builtF() * (B.c_built[i] || 0));
      eligible[i] = (!P.gate || B.near[i].length >= P.gateN) && priceOk(i) ? 1 : 0;
    }
    order = [];
    for (let i = 0; i < N; i++) if (eligible[i]) order.push(i);
    order.sort((a, b) => total[b] - total[a]);
    rankOf = new Int32Array(N).fill(0);
    order.forEach((i, r) => { rankOf[i] = r + 1; });
  };

  // ---------- colours ----------
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  let RAMP = [];
  const hex = (h) => [1, 3, 5].map((k) => parseInt(h.slice(k, k + 2), 16));
  const ramp = (t) => {
    t = Math.max(0, Math.min(1, t)); const x = t * (RAMP.length - 1), k = Math.min(Math.floor(x), RAMP.length - 2), f = x - k;
    const a = RAMP[k], b = RAMP[k + 1];
    return `rgb(${a.map((v, j) => Math.round(v + (b[j] - v) * f)).join(',')})`;
  };
  let lo = 0, hi = 100;
  const colourScale = () => {
    const v = order.map((i) => total[i]);
    hi = v.length ? v[0] : 100; lo = v.length ? v[Math.floor(v.length * 0.9)] ?? v[v.length - 1] : 0;
    if (hi - lo < 1) lo = hi - 1;
  };
  const colourOf = (i) => ramp((total[i] - lo) / (hi - lo));

  // ---------- controls ----------
  const buildControls = () => {
    $('#sc-presets').innerHTML = PRESETS.map((p) => `<button type="button" data-p="${p.id}">${esc(p.label)}</button>`).join('');
    $('#sc-presets').addEventListener('click', (e) => {
      const p = PRESETS.find((x) => x.id === e.target.dataset.p); if (!p) return;
      P.w = { ...p.w }; P.on = Object.fromEntries(COMPS.map((c) => [c.id, p.w[c.id] > 0])); update();
    });
    $('#sc-weights').innerHTML = COMPS.map((c) => `
      <div class="sc-w" data-c="${c.id}">
        <label class="sc-check"><input type="checkbox" data-on="${c.id}"> ${esc(c.label)}</label>
        <input type="range" min="0" max="100" step="1" data-w="${c.id}" aria-label="${esc(c.label)} weight">
        <output data-out="${c.id}"></output>
        <button type="button" class="cb-btn" data-only="${c.id}" aria-label="Rank by ${esc(c.label)} only">only</button>
      </div>`).join('');
    $('#sc-weights').addEventListener('input', (e) => {
      const t = e.target;
      if (t.dataset.w) { P.w[t.dataset.w] = +t.value; if (+t.value > 0) P.on[t.dataset.w] = true; update(); }
      if (t.dataset.on) { P.on[t.dataset.on] = t.checked; update(); }
    });
    $('#sc-weights').addEventListener('click', (e) => {
      const id = e.target.dataset.only; if (!id) return;
      P.on = Object.fromEntries(COMPS.map((c) => [c.id, c.id === id])); if (!+P.w[id]) P.w[id] = 50;
      if (id === 'airport' && P.flights === 'ignore') P.flights = 'year_round';
      update();
    });
    $('#sc-flights').innerHTML = FLIGHTS.map((f) => `<button type="button" data-f="${f.id}">${esc(f.label)}</button>`).join('');
    $('#sc-flights').addEventListener('click', (e) => { if (e.target.dataset.f) { P.flights = e.target.dataset.f; update(); } });
    $('#sc-gate').addEventListener('change', (e) => { P.gate = e.target.checked; update(); });
    $('#sc-gate-n').addEventListener('input', (e) => { P.gateN = +e.target.value; P.gate = true; update(); });
    $('#sc-spread').addEventListener('change', (e) => { P.spread = e.target.checked; update(); });
    const pnum = (v) => (v === '' || isNaN(+v) ? null : Math.max(0, +v));
    $('#sc-pmin').addEventListener('change', (e) => { P.pmin = pnum(e.target.value); update(); });
    $('#sc-pmax').addEventListener('change', (e) => { P.pmax = pnum(e.target.value); update(); });
    $('#sc-ponly').addEventListener('change', (e) => { P.ponly = e.target.checked; update(); });
    $('#sc-pclear').addEventListener('click', () => { P.pmin = P.pmax = null; P.ponly = false; update(); });
    $('#sc-chart').addEventListener('click', (e) => { const c = e.target.closest('[data-i]'); if (c) select(+c.dataset.i, true); });
    $('#sc-built').addEventListener('change', (e) => { P.built = e.target.checked; update(); });
    $('#sc-built-s').addEventListener('input', (e) => { P.builtS = +e.target.value; P.built = true; update(); });
    $('#sc-frames').innerHTML = FRAMES.map((f) => `<button type="button" data-fr="${f.id}">${esc(f.label)}</button>`).join('');
    $('#sc-frames').addEventListener('click', (e) => { if (e.target.dataset.fr) { P.frame = e.target.dataset.fr; frameShown = null; update(); } });
    const pickRow = (e) => {
      const tr = e.target.closest('tr[data-i]'); if (!tr) return;
      if (e.type === 'keydown' && e.key !== 'Enter' && e.key !== ' ') return;
      e.preventDefault(); select(+tr.dataset.i, true);
    };
    for (const t of ['#sc-top', '#sc-known']) { $(t).addEventListener('click', pickRow); $(t).addEventListener('keydown', pickRow); }
  };

  const syncControls = () => {
    const presetOn = PRESETS.find((p) => COMPS.every((c) => (p.w[c.id] > 0) === P.on[c.id] && (!P.on[c.id] || +P.w[c.id] === p.w[c.id])));
    $('#sc-presets').querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(!!presetOn && b.dataset.p === presetOn.id)));
    const w = weights(), wsum = Object.values(w).reduce((a, b) => a + b, 0);
    for (const c of COMPS) {
      const row = $(`.sc-w[data-c="${c.id}"]`);
      row.querySelector('[data-on]').checked = P.on[c.id];
      row.querySelector('[data-w]').value = P.w[c.id];
      row.querySelector('[data-out]').textContent = w[c.id] && wsum ? `${P.w[c.id]} · ${Math.round(w[c.id] / wsum * 100)}%` : 'off';
      row.classList.toggle('sc-off', !w[c.id]);
    }
    $('#sc-flights').querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.f === P.flights)));
    $('#sc-flights-def').textContent = FLIGHTS.find((f) => f.id === P.flights).def;
    $('#sc-gate').checked = P.gate; $('#sc-gate-n').value = P.gateN;
    $('#sc-gate-out').textContent = P.gate ? `${P.gateN} near climb${P.gateN > 1 ? 's' : ''} · ${num(order.length)} bases` : `off · ${num(order.length)} bases`;
    $('#sc-spread').checked = P.spread;
    if (PR) {
      $('#sc-pmin').value = P.pmin ?? ''; $('#sc-pmax').value = P.pmax ?? ''; $('#sc-ponly').checked = P.ponly;
      const nb = PR.filter((x) => x >= 0).length;
      $('#sc-pdef').textContent = `Prices for ${num(PM.length)} municipalities so far (${num(nb)} bases). Bases without one are kept unless you tick the box. Your range is remembered in this browser only.`;
    }
    $('#sc-built').checked = P.built; $('#sc-built-s').value = P.builtS;
    $('#sc-built-out').textContent = P.built ? `${P.builtS}% of the score` : 'off';
    $('#sc-frames').querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.fr === P.frame)));
  };

  // ---------- map ----------
  const radius = () => Math.max(2, Math.min(7, map.getZoom() - 3.5));
  const initMap = () => {
    map = L.map('sc-map', { scrollWheelZoom: false, dragging: !L.Browser.mobile, zoomSnap: 0.25, preferCanvas: true }).setView([40, -3], 5);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);
    const renderer = L.canvas({ padding: 0.3 });
    for (let i = 0; i < N; i++) {
      const mk = L.circleMarker([B.lat[i], B.lon[i]], { renderer, weight: 0, fillOpacity: 0.9, radius: 3, bubblingMouseEvents: false });
      mk.on('click', () => select(i, false));
      mk.bindTooltip(() => tipText(i), { sticky: true, className: 'cb-maplabel', direction: 'top', offset: [0, -6] });
      mk.addTo(map); markers.push(mk);
    }
    selLayer = L.layerGroup().addTo(map);
    map.on('zoomend', () => { const r = radius(); markers.forEach((mk, i) => mk.setRadius(eligible[i] ? r : r * 0.6)); });
  };
  const tipText = (i) => `${esc(B.name[i] || 'Base')}: ${eligible[i] ? `#${num(rankOf[i])} · ${num(total[i], 0)}` : 'fails the gate'} · ${B.near[i].length} near climbs`;

  const drawMap = () => {
    if (frameShown !== P.frame) {
      map.invalidateSize();
      map.fitBounds(FRAMES.find((f) => f.id === P.frame).b, { animate: false });
      frameShown = P.frame;
    }
    const r = radius(), grey = css('--cds-chart-muted'), ring = css('--color-fg');
    const top = new Set(topList().slice(0, 20));
    for (let i = 0; i < N; i++) {
      const mk = markers[i];
      if (eligible[i]) mk.setStyle({ fillColor: colourOf(i), fillOpacity: 0.9, radius: r, weight: top.has(i) ? 2 : 0, color: ring });
      else mk.setStyle({ fillColor: grey, fillOpacity: 0.35, radius: r * 0.6, weight: 0 });
    }
    top.forEach((i) => markers[i].bringToFront());
    const ends = `<div class="cb-mapkey-ends"><span>${num(lo)}</span><span>${num(hi)}</span></div>`;
    $('#sc-key').innerHTML = `<div class="cb-mapkey-scale"><div class="cb-mapkey-bar" style="background:linear-gradient(90deg,${[0, .25, .5, .75, 1].map(ramp).join(',')})"></div>${ends}</div>`
      + `<span class="cb-note">Score out of 100, from the 90th percentile of ranked bases (left) to the best (right); lower scores share the left colour.</span>`;
  };

  // ---------- lists ----------
  const topList = () => {
    if (!P.spread) return order.slice(0, 25);
    const out = [];
    for (const i of order) {
      if (out.every((j) => kmBetween(i, j) > 15)) out.push(i);
      if (out.length >= 25) break;
    }
    return out;
  };
  const climbName = (c) => C.top_name[c] || `climb to ${num(C.top_z[c])} m`;
  const airText = (i) => {
    const yr = B.yr_min[i] == null ? 'none reachable by road' : `${num(B.yr_min[i])} min to ${airportName(B.yr_code[i])}`;
    const sea = B.any_code[i] && B.any_code[i] !== B.yr_code[i] ? `; seasonal ${airportName(B.any_code[i])} ${num(B.any_min[i])} min` : '';
    return `year-round: ${yr}${sea}`;
  };
  const AIRPORTS = {};
  const airportName = (code) => (AIRPORTS[code] ? AIRPORTS[code].name : code);

  const drawTop = () => {
    const rows = topList();
    $('#sc-top').innerHTML = `<thead><tr><th>Base</th><th>Rank</th><th>Score</th><th>Climbs</th><th>${PR ? 'Ride days' : 'Rideable days'}</th><th>Airport</th>${PR ? '<th>€/m²</th>' : ''}</tr></thead><tbody>`
      + rows.map((i) => `<tr data-i="${i}" tabindex="0" class="${i === P.sel ? 'cb-sel' : ''}"><td>${esc(B.name[i] || '–')}</td><td>${num(rankOf[i])}</td><td>${num(total[i], 1)}</td>`
        + `<td>${B.near[i].length}</td><td>${num(B.w_ride[i])}</td><td>${B.yr_min[i] == null ? '–' : num(B.yr_min[i]) + ' min'}</td>${PR ? `<td>${priceOf(i) ? num(priceOf(i).eur_m2) : '–'}</td>` : ''}</tr>`).join('') + '</tbody>';
  };

  let known = [];
  const drawKnown = () => {
    $('#sc-known').innerHTML = `<thead><tr><th>Place</th><th>Expected</th><th>Gate</th><th>Rank</th><th>Score</th>${PR ? '<th>€/m²</th>' : ''}</tr></thead><tbody>`
      + known.map(({ p, i }) => {
        const gate = B.near[i].length >= D.gate_n;
        return `<tr data-i="${i}" tabindex="0" class="${i === P.sel ? 'cb-sel' : ''}"><td>${esc(p.name)}</td><td>${p.expect === '?' ? '–' : p.expect}</td>`
          + `<td class="${(gate ? 'pass' : 'fail') === p.expect || p.expect === '?' ? '' : 'sc-miss'}">${gate ? 'pass' : 'fail'} (${B.near[i].length})</td>`
          + `<td>${eligible[i] ? num(rankOf[i]) : '–'}</td><td>${num(total[i], 1)}</td>${PR ? `<td>${priceOf(i) ? num(priceOf(i).eur_m2) : '–'}</td>` : ''}</tr>`;
      }).join('') + '</tbody>';
  };

  // ---------- breakdown ----------
  const select = (i, pan) => {
    P.sel = i; save();
    if (pan) { map.setView([B.lat[i], B.lon[i]], Math.max(map.getZoom(), 10), { animate: false }); }
    drawDetail(); drawTop(); drawKnown(); drawSel(); drawChart();
  };
  const drawSel = () => {
    selLayer.clearLayers();
    const i = P.sel; if (i == null || i >= N) return;
    const fg = css('--color-fg'), c1 = css('--dash-c1'), c0 = css('--dash-c0');
    for (const [c] of B.near[i]) {
      L.polyline([[C.foot_lat[c], C.foot_lon[c]], [C.top_lat[c], C.top_lon[c]]], { color: c1, weight: 3, opacity: 0.9, interactive: false }).addTo(selLayer);
      L.circleMarker([C.top_lat[c], C.top_lon[c]], { radius: 3, color: c1, fillColor: c1, fillOpacity: 1, weight: 1, interactive: false }).addTo(selLayer);
    }
    for (const [c] of B.onward[i]) {
      L.polyline([[C.foot_lat[c], C.foot_lon[c]], [C.top_lat[c], C.top_lon[c]]], { color: c0, weight: 2, opacity: 0.8, dashArray: '4 4', interactive: false }).addTo(selLayer);
    }
    L.circleMarker([B.lat[i], B.lon[i]], { radius: 9, color: fg, weight: 3, fill: false, interactive: false }).addTo(selLayer);
  };
  const months = 'JFMAMJJASOND';
  const drawDetail = () => {
    const box = $('#sc-detail'), i = P.sel;
    if (i == null || i >= N) { box.innerHTML = '<h2>Breakdown</h2><p class="cb-note">Choose a base on the map or in a list.</p>'; return; }
    const w = weights(), wsum = Object.values(w).reduce((a, b) => a + b, 0);
    const facts = {
      climbing: `${B.near[i].length} near and ${B.onward[i].length} onward climbs`,
      weather: B.w_ride[i] == null ? 'no weather yet' : `${num(B.w_ride[i])} rideable days a year at about ${num(B.w_height[i])} m${B.w_own[i] ? '' : ' (borrowed from the nearest point fetched so far)'}`,
      airport: airText(i),
      quiet: `${num(B.m_quiet_km[i])} km of minor roads (weighted), ${num(B.m_loops[i])} junctions within 20 km; ${num(B.land20[i])}% of that circle is land, and the score is per km² of land`,
      walking: `${num(B.m_walk_km[i])} km of paths (weighted) within 15 km; peaks ${num(B.m_peaks[i])}`,
      flat: `${num(B.m_flat_km[i])} km of minor roads under 2% within 20 km`,
      gravel: `${num(B.m_gravel_km[i])} km of gravel tracks (countryside-weighted) within 15 km`,
    };
    const rows = COMPS.map((c) => {
      const v = comp[c.id][i] || 0, pts = wsum ? w[c.id] * v / wsum * 100 : 0;
      return `<div class="sc-bar ${w[c.id] ? '' : 'sc-off'}"><span class="sc-bar-l">${esc(c.label)}</span>`
        + `<span class="sc-bar-t"><span style="width:${(v * 100).toFixed(1)}%"></span></span><span class="sc-bar-v">${v.toFixed(2)}</span>`
        + `<span class="sc-bar-p">${w[c.id] ? '+' + pts.toFixed(1) : 'off'}</span><span class="sc-bar-f">${esc(facts[c.id])}</span></div>`;
    }).join('') + (() => {
      const pen = builtF() * (B.c_built[i] || 0), before = pen < 1 ? total[i] / (1 - pen) : 0;
      return `<div class="sc-bar ${P.built ? '' : 'sc-off'}"><span class="sc-bar-l">Built-up base</span>`
        + `<span class="sc-bar-t sc-pen"><span style="width:${((B.c_built[i] || 0) * 100).toFixed(1)}%"></span></span><span class="sc-bar-v">${(B.c_built[i] || 0).toFixed(2)}</span>`
        + `<span class="sc-bar-p">${P.built ? '−' + (before - total[i]).toFixed(1) : 'off'}</span>`
        + `<span class="sc-bar-f">${num(B.built5[i])}% of the land within 5 km is built-up</span></div>`;
    })();
    const mo = B.w_month[i];
    const moMax = 31;
    const monthBars = mo ? `<div class="sc-months" aria-label="Rideable days by month">${mo.map((d, k) => `<span title="${d} days"><i style="height:${(d / moMax * 100).toFixed(0)}%"></i><b>${months[k]}</b></span>`).join('')}</div>` : '';
    const climbRow = (c, km, via) => `<tr><td><a href="https://www.openstreetmap.org/?mlat=${C.foot_lat[c]}&amp;mlon=${C.foot_lon[c]}#map=14/${C.foot_lat[c]}/${C.foot_lon[c]}" target="_blank" rel="noopener">${esc(climbName(c))}</a>`
      + `<span class="sc-from">${C.foot_name[c] ? 'from ' + esc(C.foot_name[c]) : ''}${via != null ? ' · via ' + esc(climbName(via)) : ''}</span></td>`
      + `<td>${num(km / 10, 1)}</td><td>${num(C.gain[c])}</td><td>${num(C.length_km[c], 1)}</td><td>${num(C.grade[c], 1)}</td></tr>`;
    const head = '<thead><tr><th>Climb</th><th>To foot, km</th><th>Gain, m</th><th>Length, km</th><th>Avg %</th></tr></thead>';
    const status = eligible[i] ? `Rank <b>${num(rankOf[i])}</b> of ${num(order.length)}` : `Doesn't pass the gate (${B.near[i].length} near climb${B.near[i].length === 1 ? '' : 's'})`;
    box.innerHTML = `<h2>${esc(B.name[i] || 'Base')}</h2>
      <p class="cb-note">${status} · ${B.lat[i].toFixed(3)}, ${B.lon[i].toFixed(3)}</p>
      <p class="sc-total">${num(total[i], 1)}<span class="cb-tile-unit">/ 100</span></p>
      ${PR ? `<p class="sc-price-line">${priceOf(i) ? `<b>${num(priceOf(i).eur_m2)} €/m²</b> in ${esc(priceOf(i).name)} (${esc(priceOf(i).province)}): average of notarised sales over the last 12 months, checked ${esc(priceOf(i).checked)}` : 'No price looked up yet for this municipality'}</p>` : ''}
      <div class="sc-bars">${rows}</div>
      ${monthBars ? `<p class="cb-note">Rideable days by month at the climbs' height (modelled, 2017–2025):</p>${monthBars}` : ''}
      <h3 class="sc-h3">Near climbs (foot within 26 km by road)</h3>
      <div class="cb-tablewrap sc-climbs"><table class="cb-table">${head}<tbody>${B.near[i].map(([c, km]) => climbRow(c, km)).join('')}</tbody></table></div>
      ${B.onward[i].length ? `<h3 class="sc-h3">Onward climbs (over a near climb first; distance is the whole ride to the foot)</h3>
      <div class="cb-tablewrap sc-climbs"><table class="cb-table">${head}<tbody>${B.onward[i].map(([c, km, via]) => climbRow(c, km, via)).join('')}</tbody></table></div>` : ''}
      <p class="cb-note">On the map: near climbs in solid orange (foot to top, as the crow flies), onward climbs dashed. Climb names are the nearest pass or peak to the top in OpenStreetMap, so some are approximate.</p>`;
  };


  // ---------- score against price (private copy only) ----------
  const drawChart = () => {
    if (!PR) return;
    const box = $('#sc-chart'), W = Math.max(280, box.clientWidth || 600), H = 340, m = { l: 46, r: 14, t: 12, b: 38 };
    const pts = order.filter((i) => priceOf(i)).map((i) => ({ i, x: priceOf(i).eur_m2, y: total[i] }));
    if (!pts.length) { box.innerHTML = '<p class="cb-note">No priced bases pass the current gate and price range.</p>'; return; }
    // one dot per municipality (its best base), so a town with several bases doesn't crowd the chart
    const best = new Map();
    for (const p of pts) { const k = PR[p.i]; if (!best.has(k)) best.set(k, p); }
    const shown = [...best.values()];
    const xmax = Math.max(...shown.map((p) => p.x)) * 1.05, ymin = Math.floor(Math.min(...shown.map((p) => p.y)) / 5) * 5, ymax = Math.ceil(Math.max(...shown.map((p) => p.y)) / 5) * 5 || 5;
    const X = (v) => m.l + (v / xmax) * (W - m.l - m.r), Y = (v) => H - m.b - ((v - ymin) / (ymax - ymin || 1)) * (H - m.t - m.b);
    const step = xmax > 6000 ? 2000 : 1000, ys = Math.max(5, Math.round((ymax - ymin) / 25) * 5);
    let g = '';
    for (let v = 0; v <= xmax; v += step) g += `<line x1="${X(v)}" x2="${X(v)}" y1="${m.t}" y2="${H - m.b}" class="sc-grid"/><text x="${X(v)}" y="${H - m.b + 16}" text-anchor="middle">${num(v)}</text>`;
    for (let v = ymin; v <= ymax; v += ys) g += `<line x1="${m.l}" x2="${W - m.r}" y1="${Y(v)}" y2="${Y(v)}" class="sc-grid"/><text x="${m.l - 6}" y="${Y(v) + 4}" text-anchor="end">${v}</text>`;
    const dots = shown.map((p) => `<circle data-i="${p.i}" cx="${X(p.x).toFixed(1)}" cy="${Y(p.y).toFixed(1)}" r="${p.i === P.sel ? 7 : 5}" fill="${colourOf(p.i)}" class="${p.i === P.sel ? 'sc-dot sc-dot-sel' : 'sc-dot'}"><title>${esc(priceOf(p.i).name)}: ${num(p.y, 1)} points, ${num(p.x)} €/m²</title></circle>`).join('');
    const sel = P.sel != null && PR[P.sel] >= 0 ? best.get(PR[P.sel]) : null;
    const lab = sel ? `<text x="${X(sel.x) + 9}" y="${Y(sel.y) - 8}" class="sc-dot-lab">${esc(priceOf(sel.i).name)}</text>` : '';
    box.innerHTML = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" role="img" aria-label="Score against price per square metre">${g}`
      + `<text x="${(m.l + W - m.r) / 2}" y="${H - 4}" text-anchor="middle" class="sc-axis">Price, € per m² (municipality average)</text>`
      + `<text transform="translate(12 ${(m.t + H - m.b) / 2}) rotate(-90)" text-anchor="middle" class="sc-axis">Score</text>${dots}${lab}</svg>`;
  };

  // ---------- draw everything ----------
  let pending = false;
  const update = () => {
    save();
    if (pending) return;
    pending = true;
    requestAnimationFrame(() => {
      pending = false;
      score(); colourScale(); syncControls(); drawMap(); drawTop(); drawKnown(); drawDetail(); drawSel(); drawChart();
    });
  };

  const status = () => {
    const w = D.weather, borrowed = B.w_own.filter((x) => !x).length;
    $('#sc-status').innerHTML = `<b>Prototype, data of ${esc(D.generated)}.</b> `
      + (w.points_fetched < w.points_total ? `Weather from ${w.points_fetched} of ${w.points_total} points so far: ${num(borrowed)} of ${num(N)} bases borrow the nearest fetched point for now. `
        : `Weather from all ${w.points_total} points: ${num(borrowed)} of ${num(N)} bases have no point of their own and use the nearest. `)
      + `Winter flights were checked on 27 Oct 2026 for January and February 2027. `
      + (PR ? `<b>Private copy with property prices: not for sharing.</b> The price filter is the first box below; the score-against-price chart is under the tables.` : `Nothing here includes property prices yet.`);
  };

  fetch(CFG.root + 'data/score/' + CFG.region + '.json')
    .then((r) => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(async (data) => {
      D = data; B = D.bases; C = D.climbs; N = B.lat.length;
      comp = Object.fromEntries(COMPS.filter((c) => c.id !== 'airport').map((c) => [c.id, B['c_' + c.id]]));
      for (const a of D.airports) AIRPORTS[a.code] = a;
      known = D.places.map((p) => {
        let best = 0, bd = Infinity;
        for (let i = 0; i < N; i++) { const d = (B.lat[i] - p.lat) ** 2 + ((B.lon[i] - p.lon) * Math.cos(p.lat * Math.PI / 180)) ** 2; if (d < bd) { bd = d; best = i; } }
        return { p, i: best };
      });
      if (P.sel != null && P.sel >= N) P.sel = null;
      RAMP = [0, 1, 2, 3, 4].map((k) => hex(css('--sc-r' + k)));
      if (CFG.prices) {
        const pr = await fetch(CFG.root + 'data/score/' + CFG.region + '-prices.json').then((r) => (r.ok ? r.json() : null)).catch(() => null);
        if (pr && pr.base_muni.length === N) { PR = pr.base_muni; PM = pr.munis; $('#sc-price-ctl').hidden = false; $('#sc-chart-card').hidden = false; }
      }
      status(); buildControls(); initMap();
      if (P.sel == null) { score(); P.sel = order[0] ?? null; }   // first visit: show the top base's breakdown
      update();
      matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { RAMP = [0, 1, 2, 3, 4].map((k) => hex(css('--sc-r' + k))); update(); });
    })
    .catch((e) => { $('#sc-status').textContent = 'Failed to load the score data (' + e.message + ').'; $('#sc-status').classList.add('cb-fail'); });
})();
