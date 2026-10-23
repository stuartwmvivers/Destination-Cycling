(() => {
  const RAW = window.__CLIMATE_DATA__;
  const sets = {
    climate: { title: 'Monthly weather, 2017–2025', rows: RAW.climate },
    places: { title: 'Places compared', rows: RAW.places },
    outlines: { title: 'Map outlines', rows: RAW.outlines },
  };
  if (RAW.stations) sets.stations = { title: 'Station readings', rows: RAW.stations };
  const calcs = {};
  const cache = {};
  const listeners = [];
  const DEFAULTS = { place: 'begur', compare: 'dunning', measure: 'tmax', year: 'all', period: '1', frame: 'auto', region: 'all' };
  let params = { ...DEFAULTS };
  try { const s = JSON.parse(localStorage.getItem('spain-climate-params') || 'null'); if (s && typeof s === 'object') params = { ...params, ...s }; } catch (e) {}
  const save = () => { try { localStorage.setItem('spain-climate-params', JSON.stringify(params)); } catch (e) {} };
  let queued = false;
  const run = () => { queued = false; for (const fn of listeners) { try { fn(); } catch (e) { console.error(e); } } };
  const schedule = () => { if (!queued) { queued = true; requestAnimationFrame(run); } };
  const rowsOf = (id) => {
    if (sets[id]) return sets[id].rows;
    if (calcs[id]) {
      const ins = calcs[id].inputs.map(rowsOf);
      if (ins.some((x) => x == null)) return null;
      if (!cache[id]) cache[id] = calcs[id].fn(...ins);
      return cache[id];
    }
    return null;
  };
  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  window.dash = {
    data(id) {
      const r = rowsOf(id);
      if (r == null) return { status: 'missing', data: [], columns: [], meta: [] };
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
})();
