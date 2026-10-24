// The small `dash` API the dashboard code is written against (from the Claude.ai Dashboard artifact
// it was first built in). Data are fetched from the region file named by window.DC_PAGE and expanded
// from columns back into the row form the page code expects. Until they arrive, data() reports
// 'loading' (the page shows skeletons); if the fetch fails it reports 'error'.
(() => {
  const PAGE = window.DC_PAGE || {};
  const sets = {};
  let status = 'loading';
  const calcs = {};
  const cache = {};
  const listeners = [];
  const DEFAULTS = { place: 'begur', compare: 'dunning', measure: 'tmax', year: 'all', period: '1', frame: 'auto', region: 'all' };
  const KEY = 'dc-params-' + (PAGE.region || 'site');
  let params = { ...DEFAULTS };
  try { const s = JSON.parse(localStorage.getItem(KEY) || 'null'); if (s && typeof s === 'object') params = { ...params, ...s }; } catch (e) {}
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(params)); } catch (e) {} };
  let queued = false;
  const run = () => { queued = false; for (const fn of listeners) { try { fn(); } catch (e) { console.error(e); } } };
  const schedule = () => { if (!queued) { queued = true; requestAnimationFrame(run); } };
  const rowsOf = (id) => {
    if (sets[id]) return sets[id];
    if (calcs[id]) {
      const ins = calcs[id].inputs.map(rowsOf);
      if (ins.some((x) => x == null)) return null;
      if (!cache[id]) cache[id] = calcs[id].fn(...ins);
      return cache[id];
    }
    return null;
  };
  // Columnar region file -> rows. Months run year-major from the first year, January first.
  const expand = (series, years, head) => {
    const out = [];
    for (const [place, s] of Object.entries(series)) {
      const ms = s.series || s;
      for (let i = 0; i < years.length * 12; i++) {
        const row = { place, ...head(s), year: years[0] + Math.floor(i / 12), month: (i % 12) + 1 };
        for (const [m, v] of Object.entries(ms)) row[m] = v[i];
        out.push(row);
      }
    }
    return out;
  };
  const load = async () => {
    try {
      const r = await fetch(PAGE.root + 'data/regions/' + PAGE.region + '.json');
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const d = await r.json();
      sets.places = d.places;
      sets.climate = expand(d.climate, d.years, () => ({}));
      sets.stations = expand(d.stations, d.years, ({ series, ...info }) => info);
      status = 'ok';
    } catch (e) { console.error('Failed to load region data', e); status = 'error'; }
    schedule();
  };
  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  window.dash = {
    data(id) {
      const r = rowsOf(id);
      if (r == null) return { status: status === 'ok' ? 'missing' : status, data: [], columns: [], meta: [] };
      return { status: 'ok', data: r, rows: r, columns: r.length ? Object.keys(r[0]) : [], meta: [], refreshing: false };
    },
    onData(fn) { listeners.push(fn); try { fn(); } catch (e) { console.error(e); } },
    calc(id, def) { calcs[id] = def; },
    loader() {},
    params() { return { ...params }; },
    setParams(o) {
      for (const [k, v] of Object.entries(o || {})) { if (v == null) delete params[k]; else params[k] = v; }
      save(); schedule();
    },
    resetParams() { params = { ...DEFAULTS }; save(); schedule(); },
    setLink(name) { try { history.replaceState(null, '', '#' + name); } catch (e) {} },
    refresh() {},
    get colors() { return [css('--dash-c0') ? 'var(--dash-c0)' : '#2f6fb0', 'var(--dash-c1)', 'var(--dash-c2)', 'var(--dash-c3)']; },
  };
  let w = 0;
  window.addEventListener('resize', () => { const nw = document.documentElement.clientWidth; if (nw !== w) { w = nw; schedule(); } });
  load();
})();
