(() => {
  const MEASURES = [
    { id: 'tmax', label: 'Daytime high', short: 'High', unit: '°C', temp: true, def: 'Average of the daily maximum temperature.' },
    { id: 'tmin', label: 'Night low', short: 'Low', unit: '°C', temp: true, def: 'Average of the daily minimum temperature.' },
    { id: 'ride', label: 'Rideable days', short: 'Rideable', unit: 'days', def: 'Dry (under 1 mm), gusts under 50 km/h and a high of 11°C or more.' },
    { id: 'warm', label: 'Warm riding days', short: 'Warm ride', unit: 'days', def: 'Dry, gusts under 50 km/h and a high between 14°C and 30°C.' },
    { id: 'rain', label: 'Rainfall', short: 'Rain', unit: 'mm', def: 'Total rain and snow, as water.' },
    { id: 'wet', label: 'Wet days', short: 'Wet', unit: 'days', def: 'Days with 1 mm of rain or more.' },
    { id: 'tram', label: 'North-wind days', short: 'N wind', unit: 'days', def: 'Days with gusts of 50 km/h or more from the north or north-west (the Tramuntana on the Costa Brava and in Mallorca).' },
    { id: 'hot', label: 'Hot days', short: 'Hot', unit: 'days', def: 'Days with a high of 30°C or more.' },
    { id: 'frost', label: 'Frost nights', short: 'Frost', unit: 'days', def: 'Nights with a low of 0°C or below.' },
  ];
  const BY = Object.fromEntries(MEASURES.map((m) => [m.id, m]));
  const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const MONTH = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const YEARS = ['2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025'];
  const PERIODS = MON.map((_, i) => String(i + 1));
  const DEFAULTS = { place: 'begur', compare: 'dunning', measure: 'tmax', year: 'all', period: '1', frame: 'auto', region: 'all' };
  const REGIONS = ['Costa Brava', 'Costa del Sol', 'Costa Blanca', 'Mallorca', 'UK'];
  const REGION_FRAME = { 'Costa Brava': 'brava', 'Costa del Sol': 'sol', 'Costa Blanca': 'blanca', 'Mallorca': 'mallorca', 'UK': 'spain' };
  const FRAMES = [['spain', 'All Spain'], ['brava', 'Costa Brava'], ['sol', 'Costa del Sol'], ['blanca', 'Costa Blanca'], ['mallorca', 'Mallorca']];
  const FRAME_NAME = Object.fromEntries(FRAMES);
  const FRAME_LABELS = {
    brava: [[24, 40, 'FRANCE'], [24, 735, 'BARCELONA PROVINCE'], [850, 420, 'Mediterranean', 'end', true]],
    spain: [[40, 330, 'PORTUGAL'], [560, 40, 'FRANCE'], [30, 560, 'Atlantic', 'start', true], [690, 470, 'Mediterranean', 'end', true]],
    sol: [[40, 40, 'MÁLAGA PROVINCE'], [420, 380, 'Mediterranean', 'middle', true]],
    blanca: [[40, 40, 'VALENCIA REGION'], [660, 520, 'Mediterranean', 'middle', true]],
    mallorca: [[60, 120, 'Mediterranean', 'start', true]],
  };
  const LABEL_SIDE = { brava: { figueres: 'left', tossa: 'left', palamos: 'left' }, sol: { torrox: 'left', frigiliana: 'top' }, blanca: { javea: 'left', altea: 'left' }, mallorca: {} };
  const REGION_TAGS = [['Costa Brava', 'brava', -40, -46, 'end'], ['Costa del Sol', 'sol', 0, 44, 'middle'], ['Costa Blanca', 'blanca', -26, 6, 'end'], ['Mallorca', 'mallorca', 0, -34, 'middle']];
  const sortState = { field: 'tmax', dir: -1 };
  let drawTable = () => {};

  const $ = (s) => document.querySelector(s);
  const params = () => ({ ...DEFAULTS, ...Object.fromEntries(Object.entries(dash.params() || {}).filter(([, v]) => v != null && v !== '')) });
  const set = (o) => dash.setParams(o);

  const isAvg = (P) => P.year === 'all';
  const fmt = (m, v, avg) => {
    if (v == null || Number.isNaN(v)) return '—';
    if (m === 'rain') return d3.format(',.0f')(v);
    if (BY[m] && BY[m].temp) return d3.format('.1f')(v);
    return avg ? d3.format('.1f')(v) : d3.format(',.0f')(v);
  };
  const unitOf = (m, period) => {
    const u = BY[m].unit;
    if (u === '°C') return '°C';
    return period === 'year' ? u + ' a year' : u;
  };
  const periodName = (p) => (p === 'year' ? 'the whole year' : MONTH[+p - 1]);
  const periodShort = (p) => (p === 'year' ? 'Whole year' : MONTH[+p - 1]);
  const yearName = (y) => (y === 'all' ? '2017–2025 average' : y);
  const resolve = (c) => {
    const s = document.createElement('span');
    s.style.color = c;
    s.style.display = 'none';
    document.getElementById('dash-root').appendChild(s);
    const v = getComputedStyle(s).color;
    s.remove();
    return v;
  };
  const mark = (el, place, year, period, field) => {
    el.dataset.source = 'periods';
    el.dataset.field = field;
    el.dataset.where = 'place=' + encodeURIComponent(place) + '&year=' + encodeURIComponent(year) + '&period=' + encodeURIComponent(period);
  };
  const textWidth = (svg, texts, size) => {
    const t = svg.append('text').attr('font-size', size).attr('visibility', 'hidden');
    let w = 0;
    for (const s of texts) { t.text(s); w = Math.max(w, t.node().getComputedTextLength()); }
    t.remove();
    return w;
  };
  const failBox = (el, st) => {
    el.classList.remove('dash-skeleton');
    if (st === 'error' || st === 'connect' || st === 'declined' || st === 'missing') {
      el.replaceChildren();
      const d = document.createElement('div');
      d.className = 'cb-fail';
      d.textContent = 'Failed to load';
      el.appendChild(d);
    } else {
      el.replaceChildren();
      el.classList.add('dash-skeleton');
    }
  };

  // ---------- controls (built once) ----------
  const seg = $('#cb-measure');
  for (const m of MEASURES) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = m.label;
    b.dataset.m = m.id;
    b.addEventListener('click', () => set({ measure: m.id }));
    seg.appendChild(b);
  }
  $('#cb-place').addEventListener('change', (e) => set({ place: e.target.value, frame: 'auto' }));
  const frameSeg = $('#cb-frames');
  for (const [id, name] of FRAMES) {
    const b = document.createElement('button');
    b.type = 'button'; b.textContent = name; b.dataset.f = id;
    b.addEventListener('click', () => set({ frame: id }));
    frameSeg.appendChild(b);
  }
  const regSeg = $('#cb-regions');
  for (const id of ['all'].concat(REGIONS)) {
    const b = document.createElement('button');
    b.type = 'button'; b.textContent = id === 'all' ? 'All regions' : id; b.dataset.r = id;
    b.addEventListener('click', () => set({ region: id }));
    regSeg.appendChild(b);
  }
  $('#cb-compare').addEventListener('change', (e) => set({ compare: e.target.value || 'none' }));
  $('#cb-month').addEventListener('input', (e) => { stopPlay(); set({ period: e.target.value === '13' ? 'year' : e.target.value }); });
  $('#cb-year').addEventListener('input', (e) => set({ year: e.target.value === '2016' ? 'all' : e.target.value }));
  let timer = null;
  const playBtn = $('#cb-play');
  function stopPlay() { if (timer) { clearInterval(timer); timer = null; playBtn.textContent = 'Play'; } }
  playBtn.addEventListener('click', () => {
    if (timer) { stopPlay(); return; }
    playBtn.textContent = 'Stop';
    const step = () => {
      const p = params().period;
      set({ period: p === 'year' || p === '12' ? '1' : String(+p + 1) });
    };
    step();
    timer = setInterval(step, 1300);
  });

  // shared tooltip helper
  const tipFor = (box) => {
    let tip = box.querySelector('.cb-tip');
    if (!tip) { tip = document.createElement('div'); tip.className = 'cb-tip'; tip.hidden = true; box.appendChild(tip); }
    return {
      show(ev, lines) {
        tip.replaceChildren();
        lines.forEach((l, i) => {
          const d = document.createElement('div');
          if (i === 0) d.className = 'cb-tip-h';
          if (l.color) { const s = document.createElement('span'); s.className = 'cb-sw'; s.style.background = l.color; d.appendChild(s); }
          d.appendChild(document.createTextNode(l.text));
          tip.appendChild(d);
        });
        tip.hidden = false;
        const r = box.getBoundingClientRect();
        const tw = tip.offsetWidth, th = tip.offsetHeight;
        let x = ev.clientX - r.left + 12, y = ev.clientY - r.top + 12;
        if (x + tw > r.width) x = Math.max(0, ev.clientX - r.left - tw - 12);
        if (y + th > r.height) y = Math.max(0, ev.clientY - r.top - th - 12);
        tip.style.left = x + 'px';
        tip.style.top = y + 'px';
      },
      hide() { tip.hidden = true; },
    };
  };

  // ---------- draw ----------
  dash.onData(() => {
    const P = params();
    const M = BY[P.measure] || BY.tmax;
    const pl = dash.data('places');
    const pe = dash.data('periods');
    const ou = dash.data('outlines');

    // controls state
    seg.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.m === M.id)));
    $('#cb-def').textContent = M.label + ': ' + M.def;
    $('#cb-month').value = P.period === 'year' ? '13' : P.period;
    $('#cb-month-out').textContent = periodShort(P.period);
    $('#cb-year').value = P.year === 'all' ? '2016' : P.year;
    $('#cb-year-out').textContent = P.year === 'all' ? 'All (average)' : P.year;
    const accent = resolve(dash.colors[0]);
    const muted = resolve('var(--cds-chart-muted)');
    $('#cb-month').style.accentColor = accent;
    $('#cb-year').style.accentColor = accent;

    const places = pl.status === 'ok' ? pl.data : [];
    const placeSel = $('#cb-place'), cmpSel = $('#cb-compare');
    if (places.length) {
      const groups = () => REGIONS.map((reg) => {
        const og = document.createElement('optgroup');
        og.label = reg;
        places.filter((p) => p.region === reg).forEach((p) => og.appendChild(new Option(p.name, p.place)));
        return og;
      });
      placeSel.replaceChildren(...groups());
      cmpSel.replaceChildren(new Option('Nothing', 'none'), ...groups());
      placeSel.value = P.place;
      cmpSel.value = P.compare;
    }

    const ok = pe.status === 'ok' && pl.status === 'ok';
    const els = ['#cb-take', '#cb-map', '#cb-season', '#cb-heat', '#cb-years'];
    if (!ok) {
      const st = pe.status === 'ok' ? pl.status : pe.status;
      els.forEach((s) => failBox($(s), st));
      $('#headline').replaceChildren();
      $('#cb-tbody').replaceChildren();
      return;
    }
    els.forEach((s) => $(s).classList.remove('dash-skeleton'));

    const rows = pe.data;
    const idx = new Map(rows.map((r) => [r.place + '|' + r.year + '|' + r.period, r]));
    const get = (place, year, period) => idx.get(place + '|' + year + '|' + period);
    const nameOf = Object.fromEntries(places.map((p) => [p.place, p.name]));
    const cmp = P.compare !== 'none' && P.compare !== P.place && nameOf[P.compare] ? P.compare : null;
    const avg = isAvg(P);

    // ---- takeaway ----
    {
      const el = $('#cb-take');
      el.replaceChildren();
      const r = get(P.place, P.year, P.period);
      const add = (t) => el.appendChild(document.createTextNode(t));
      const num = (place, field) => {
        const b = document.createElement('b');
        const row = get(place, P.year, P.period);
        b.textContent = fmt(field, row ? row[field] : null, avg);
        mark(b, place, P.year, P.period, field);
        el.appendChild(b);
      };
      const when = P.period === 'year' ? (avg ? 'Over a typical year' : 'In ' + P.year) : (avg ? 'In a typical ' + MONTH[+P.period - 1] : 'In ' + MONTH[+P.period - 1] + ' ' + P.year);
      if (r) {
        add(when + ', ' + nameOf[P.place] + (avg ? ' averages a high of ' : ' had an average high of '));
        num(P.place, 'tmax');
        add('°C and ');
        num(P.place, 'ride');
        add(' rideable days');
        if (cmp) {
          add('; ' + nameOf[cmp] + (avg ? ' gets ' : ' got '));
          num(cmp, 'tmax');
          add('°C and ');
          num(cmp, 'ride');
          add(' rideable days');
        }
        add('.');
      }
    }

    // ---- headline tiles ----
    {
      const box = $('#headline');
      box.replaceChildren();
      const winter = P.period !== 'year' && (+P.period <= 4 || +P.period >= 10);
      const list = ['tmax', 'tmin', 'ride', 'wet', 'tram', P.period === 'year' ? 'hot' : winter ? 'frost' : 'hot'];
      if (P.period === 'year') list.push('frost');
      for (const f of list) {
        const m = BY[f];
        const t = document.createElement('div');
        t.className = 'cb-tile';
        t.id = 'tile-' + f;
        const lab = document.createElement('div');
        lab.className = 'cb-tile-lab';
        lab.textContent = m.label + ' · ' + periodShort(P.period) + (avg ? '' : ' ' + P.year);
        const val = document.createElement('div');
        val.className = 'cb-tile-val';
        const v = document.createElement('span');
        const r = get(P.place, P.year, P.period);
        v.textContent = fmt(f, r ? r[f] : null, avg);
        mark(v, P.place, P.year, P.period, f);
        const u = document.createElement('span');
        u.className = 'cb-tile-unit';
        u.textContent = unitOf(f, P.period);
        val.append(v, u);
        t.append(lab, val);
        if (cmp) {
          const c = document.createElement('div');
          c.className = 'cb-tile-cmp';
          const cv = document.createElement('span');
          const cr = get(cmp, P.year, P.period);
          cv.textContent = fmt(f, cr ? cr[f] : null, avg);
          mark(cv, cmp, P.year, P.period, f);
          c.append(document.createTextNode(nameOf[cmp] + ' '), cv, document.createTextNode(m.unit === '°C' ? '°C' : ''));
          t.appendChild(c);
        }
        box.appendChild(t);
      }
    }

    // colour ramp for the chosen measure
    const bg = resolve('var(--color-bg)');
    const ramp = (t) => d3.interpolateRgb(d3.interpolateRgb(bg, accent)(0.12), accent)(Math.max(0, Math.min(1, t)));
    const inkOn = (t) => (t > 0.55 ? 'var(--color-bg)' : 'var(--color-fg)');

    // ---- map ----
    {
      const box = $('#cb-map');
      const regionOf = Object.fromEntries(places.map((p) => [p.place, p.region]));
      const frame = P.frame && P.frame !== 'auto' ? P.frame : (REGION_FRAME[regionOf[P.place]] || 'spain');
      $('#cb-frames').querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.f === frame)));
      $('#cb-map-title').textContent = M.label + ' · ' + periodShort(P.period) + ' · ' + yearName(P.year);
      if (ou.status !== 'ok') { failBox(box, ou.status); }
      else {
        box.replaceChildren();
        const rowsF = ou.data.filter((r) => r.frame === frame);
        const layers = Object.fromEntries(rowsF.map((r) => [r.layer, r]));
        const f = rowsF[0];
        const overview = frame === 'spain';
        const VW = Number(f.width) + 70, VH = Number(f.height);
        const proj = (lon, lat) => [(lon - f.W) * f.k * f.scale, (f.N - lat) * f.scale];
        const svg = d3.select(box).append('svg').attr('viewBox', `0 0 ${VW} ${VH}`).attr('width', '100%').attr('role', 'img').attr('aria-label', 'Map of ' + FRAME_NAME[frame] + ' with the places compared');
        svg.append('rect').attr('width', VW).attr('height', VH).attr('rx', 6).attr('fill', 'var(--cds-chart-grid)');
        svg.append('rect').attr('width', VW).attr('height', VH).attr('rx', 6).attr('fill', accent).attr('fill-opacity', 0.1);
        if (layers.others) svg.append('path').attr('d', layers.others.path).attr('fill', 'var(--color-panel)').attr('stroke', 'var(--cds-chart-axis)').attr('stroke-width', 0.8);
        if (layers.spain) svg.append('path').attr('d', layers.spain.path).attr('fill', 'var(--color-bg)').attr('stroke', 'var(--cds-chart-axis)').attr('stroke-width', 1).attr('stroke-linejoin', 'round');
        if (layers.borders) svg.append('path').attr('d', layers.borders.path).attr('fill', 'none').attr('stroke', 'var(--cds-chart-reference)').attr('stroke-width', 1.2).attr('stroke-dasharray', '5 4');
        if (layers.land) svg.append('path').attr('d', layers.land.path).attr('fill', 'var(--color-bg)').attr('stroke', frame === 'brava' ? 'none' : 'var(--cds-chart-axis)').attr('stroke-width', 1.2).attr('stroke-linejoin', 'round');
        if (layers.coast) svg.append('path').attr('d', layers.coast.path).attr('fill', 'none').attr('stroke', 'var(--cds-chart-axis)').attr('stroke-width', 1.2).attr('stroke-linejoin', 'round');
        if (layers.border) svg.append('path').attr('d', layers.border.path).attr('fill', 'none').attr('stroke', 'var(--cds-chart-reference)').attr('stroke-width', 1.5).attr('stroke-dasharray', '7 5');
        if (layers.prov) svg.append('path').attr('d', layers.prov.path).attr('fill', 'none').attr('stroke', 'var(--cds-chart-reference)').attr('stroke-width', 1).attr('stroke-dasharray', '2 4');
        const lbl = (x, y, t, anchor, italic) => svg.append('text').attr('x', x).attr('y', y).attr('text-anchor', anchor || 'start').attr('font-size', 18).attr('letter-spacing', '.12em').attr('font-style', italic ? 'italic' : null).attr('fill', 'var(--color-fg-muted)').text(t);
        for (const [x, y, t, a, i] of FRAME_LABELS[frame] || []) lbl(x, y, t, a, i);

        const homes = places.filter((p) => p.region === 'UK');
        const inMap = places.filter((p) => p.region !== 'UK' && p.lon >= f.W && p.lon <= f.E && p.lat >= f.S && p.lat <= f.N);
        const vals = inMap.map((p) => { const r = get(p.place, P.year, P.period); return r ? r[M.id] : null; }).filter((v) => v != null);
        const homeVals = homes.filter((h) => h.place === P.place || h.place === cmp).map((h) => get(h.place, P.year, P.period)).filter(Boolean).map((r) => r[M.id]);
        const ext = d3.extent(vals.concat(homeVals));
        const sc = d3.scaleLinear().domain(ext[0] === ext[1] ? [ext[0] - 1, ext[1] + 1] : ext).range([0, 1]);
        const tip = tipFor(box);
        const unitTag = M.unit === '°C' ? '°C' : ' ' + (M.unit === 'mm' ? 'mm' : 'd');
        const showTip = (ev, p) => {
          const r = get(p.place, P.year, P.period);
          tip.show(ev, [
            { text: p.name + ' · ' + p.region + ', ' + p.elevation_m + ' m' },
            { text: M.label + ': ' + fmt(M.id, r ? r[M.id] : null, avg) + ' ' + unitOf(M.id, P.period), color: ramp(sc(r ? r[M.id] : 0)) },
            { text: p.note },
          ]);
        };
        const dotR = overview ? 8 : 14;
        for (const p of inMap) {
          const [x, y] = proj(p.lon, p.lat);
          const r = get(p.place, P.year, P.period);
          const v = r ? r[M.id] : null;
          const g = svg.append('g').attr('class', 'cb-dot').attr('tabindex', 0).attr('role', 'button').attr('aria-label', p.name + ': ' + fmt(M.id, v, avg) + ' ' + unitOf(M.id, P.period));
          const sel = p.place === P.place, isC = p.place === cmp;
          if (sel) g.append('circle').attr('cx', x).attr('cy', y).attr('r', dotR + 7).attr('fill', 'none').attr('stroke', 'var(--color-fg)').attr('stroke-width', 2.5);
          if (isC) g.append('circle').attr('cx', x).attr('cy', y).attr('r', dotR + 7).attr('fill', 'none').attr('stroke', 'var(--color-fg-muted)').attr('stroke-width', 2).attr('stroke-dasharray', '4 3');
          g.append('circle').attr('cx', x).attr('cy', y).attr('r', dotR).attr('fill', v == null ? 'var(--cds-chart-muted)' : ramp(sc(v))).attr('stroke', 'var(--color-fg)').attr('stroke-opacity', 0.35).attr('stroke-width', 1);
          if (!overview || sel || isC) {
            const side = (LABEL_SIDE[frame] || {})[p.place];
            const left = side === 'left', top = side === 'top';
            const off = dotR + 12;
            const tx = top ? x : left ? x - off : x + off;
            const anchor = top ? 'middle' : left ? 'end' : 'start';
            const y1 = top ? y - dotR - 32 : y - 2, y2 = top ? y - dotR - 12 : y + 20;
            g.append('text').attr('x', tx).attr('y', y1).attr('text-anchor', anchor).attr('font-size', 19).attr('font-weight', sel ? 600 : 400).attr('fill', 'var(--color-fg)').text(p.name);
            g.append('text').attr('x', tx).attr('y', y2).attr('text-anchor', anchor).attr('font-size', 17).attr('fill', 'var(--color-fg-muted)').text(fmt(M.id, v, avg) + unitTag);
          }
          g.on('click', () => set({ place: p.place, frame: 'auto' }))
            .on('keydown', (ev) => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); set({ place: p.place, frame: 'auto' }); } })
            .on('mousemove', (ev) => showTip(ev, p)).on('mouseleave', () => tip.hide());
        }
        if (overview) {
          // region names beside each cluster, clickable to zoom in
          for (const [reg, fr, dx, dy, anchor] of REGION_TAGS) {
            const ps = inMap.filter((p) => p.region === reg);
            if (!ps.length) continue;
            const cx = d3.mean(ps, (p) => proj(p.lon, p.lat)[0]), cy = d3.mean(ps, (p) => proj(p.lon, p.lat)[1]);
            const t = svg.append('text').attr('x', cx + dx).attr('y', cy + dy).attr('text-anchor', anchor).attr('font-size', 18).attr('font-weight', 500).attr('fill', 'var(--color-fg)').style('cursor', 'pointer').text(reg + ' ›');
            t.on('click', () => set({ frame: fr }));
          }
        }
        // UK baselines inset
        if (homes.length) {
          const rowH = 46, bh = 18 + rowH * homes.length, bx = VW - 250, by = VH - 20 - bh;
          svg.append('rect').attr('x', bx).attr('y', by).attr('width', 232).attr('height', bh).attr('rx', 8).attr('fill', 'var(--color-panel)').attr('stroke', 'var(--color-border-line)');
          homes.forEach((h, i) => {
            const r = get(h.place, P.year, P.period);
            if (!r) return;
            const cy = by + 9 + rowH * i + rowH / 2;
            const sel = h.place === P.place, isC = h.place === cmp;
            const g = svg.append('g').attr('class', 'cb-dot').attr('tabindex', 0).attr('role', 'button').attr('aria-label', h.name + ': ' + fmt(M.id, r[M.id], avg));
            if (sel || isC) g.append('circle').attr('cx', bx + 30).attr('cy', cy).attr('r', 19).attr('fill', 'none').attr('stroke', sel ? 'var(--color-fg)' : 'var(--color-fg-muted)').attr('stroke-width', sel ? 2.5 : 2).attr('stroke-dasharray', isC ? '4 3' : null);
            g.append('circle').attr('cx', bx + 30).attr('cy', cy).attr('r', 13).attr('fill', ramp(sc(r[M.id]))).attr('stroke', 'var(--color-fg)').attr('stroke-opacity', 0.35);
            g.append('text').attr('x', bx + 56).attr('y', cy - 3).attr('font-size', 18).attr('font-weight', sel ? 600 : 400).attr('fill', 'var(--color-fg)').text(h.name);
            g.append('text').attr('x', bx + 56).attr('y', cy + 17).attr('font-size', 16).attr('fill', 'var(--color-fg-muted)').text(fmt(M.id, r[M.id], avg) + unitTag + ' · ' + h.area);
            g.on('click', () => set({ place: h.place })).on('mousemove', (ev) => showTip(ev, h)).on('mouseleave', () => tip.hide());
          });
        }
        // legend
        const lg = svg.append('g').attr('transform', `translate(${VW - 250},${VH - 20 - (18 + 46 * homes.length) - 58})`);
        const gid = 'cbgrad' + Math.random().toString(36).slice(2, 7);
        const grad = svg.append('defs').append('linearGradient').attr('id', gid);
        [0, 0.5, 1].forEach((o) => grad.append('stop').attr('offset', o).attr('style', 'stop-color:' + ramp(o)));
        lg.append('rect').attr('width', 232).attr('height', 12).attr('rx', 6).attr('fill', `url(#${gid})`);
        lg.append('text').attr('y', 34).attr('font-size', 16).attr('fill', 'var(--color-fg-muted)').text('Less · ' + fmt(M.id, sc.domain()[0], avg));
        lg.append('text').attr('x', 232).attr('y', 34).attr('text-anchor', 'end').attr('font-size', 16).attr('fill', 'var(--color-fg-muted)').text(fmt(M.id, sc.domain()[1], avg) + ' · More');
      }
    }

    // ---- seasonal chart ----
    {
      const box = $('#cb-season');
      box.replaceChildren();
      $('#cb-season-title').textContent = M.label + ' through the year';
      $('#cb-season-note').textContent = (avg ? 'Line: 2017–2025 average. ' : 'Line: ' + P.year + '. Dashed: 2017–2025 average. ') + 'Shading: lowest to highest year.' + (cmp ? ' Grey: ' + nameOf[cmp] + '.' : '') + ' Click a month to select it.';
      const W = Math.max(300, box.clientWidth || 600), H = 290;
      const m = M.id;
      const aRows = PERIODS.map((p) => get(P.place, 'all', p));
      const yRows = avg ? null : PERIODS.map((p) => get(P.place, P.year, p));
      const cRows = cmp ? PERIODS.map((p) => get(cmp, 'all', p)) : null;
      const vals = aRows.flatMap((r) => [r[m + '_lo'], r[m + '_hi']]).concat(yRows ? yRows.map((r) => r[m]) : [], cRows ? cRows.map((r) => r[m]) : []);
      const y = d3.scaleLinear().domain([Math.min(0, d3.min(vals)), d3.max(vals)]).nice();
      const svg = d3.select(box).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('width', '100%');
      const ticks = y.ticks(5);
      const ml = textWidth(svg, ticks.map((t) => d3.format(',')(t)), 12) + 10;
      const endLabels = [nameOf[P.place]].concat(cmp ? [nameOf[cmp]] : []);
      const mr = textWidth(svg, endLabels, 12) + 14;
      const mt = 10, mb = 26;
      y.range([H - mb, mt]);
      const x = d3.scaleBand().domain(PERIODS).range([ml, W - mr]).padding(0.2);
      const cx = (p) => x(p) + x.bandwidth() / 2;
      svg.append('g').selectAll('line').data(ticks).join('line').attr('x1', ml).attr('x2', W - mr).attr('y1', y).attr('y2', y).attr('stroke', 'var(--cds-chart-grid)');
      svg.append('g').selectAll('text').data(ticks).join('text').attr('x', ml - 6).attr('y', (d) => y(d) + 4).attr('text-anchor', 'end').attr('font-size', 12).attr('fill', 'var(--color-fg-muted)').text((d) => d3.format(',')(d));
      if (P.period !== 'year') svg.append('rect').attr('x', x(P.period) - x.step() * x.paddingInner() / 2).attr('width', x.step()).attr('y', mt).attr('height', H - mb - mt).attr('fill', 'var(--cds-chart-grid)');
      svg.append('g').selectAll('text').data(PERIODS).join('text').attr('x', cx).attr('y', H - 8).attr('text-anchor', 'middle').attr('font-size', 12).attr('fill', 'var(--color-fg-muted)').text((p) => (W < 420 ? MON[+p - 1][0] : MON[+p - 1]));
      const val = (r) => r[m];
      if (M.temp) {
        svg.append('path').datum(aRows).attr('d', d3.area().x((r) => cx(r.period)).y0((r) => y(r[m + '_lo'])).y1((r) => y(r[m + '_hi']))).attr('fill', accent).attr('fill-opacity', 0.14);
        if (cRows) svg.append('path').datum(cRows).attr('d', d3.line().x((r) => cx(r.period)).y((r) => y(val(r)))).attr('fill', 'none').attr('stroke', muted).attr('stroke-width', 2).attr('stroke-linecap', 'round').attr('stroke-linejoin', 'round');
        svg.append('path').datum(aRows).attr('d', d3.line().x((r) => cx(r.period)).y((r) => y(val(r)))).attr('fill', 'none').attr('stroke', accent).attr('stroke-width', yRows ? 1.5 : 2.5).attr('stroke-dasharray', yRows ? '5 4' : null).attr('stroke-linecap', 'round').attr('stroke-linejoin', 'round');
        if (yRows) svg.append('path').datum(yRows).attr('d', d3.line().x((r) => cx(r.period)).y((r) => y(val(r)))).attr('fill', 'none').attr('stroke', accent).attr('stroke-width', 2.5).attr('stroke-linecap', 'round').attr('stroke-linejoin', 'round');
        const main = yRows || aRows;
        svg.append('g').selectAll('circle').data(main).join('circle').attr('cx', (r) => cx(r.period)).attr('cy', (r) => y(val(r))).attr('r', (r) => (r.period === P.period ? 5 : 3)).attr('fill', accent);
      } else {
        const main = yRows || aRows;
        svg.append('g').selectAll('rect').data(main).join('rect').attr('x', (r) => x(r.period)).attr('width', x.bandwidth()).attr('y', (r) => y(Math.max(0, val(r)))).attr('height', (r) => Math.max(1, Math.abs(y(val(r)) - y(0)))).attr('rx', 4).attr('fill', accent).attr('fill-opacity', (r) => (P.period === 'year' || r.period === P.period ? 1 : 0.7));
        svg.append('g').selectAll('line').data(aRows).join('line').attr('x1', (r) => cx(r.period)).attr('x2', (r) => cx(r.period)).attr('y1', (r) => y(r[m + '_lo'])).attr('y2', (r) => y(r[m + '_hi'])).attr('stroke', 'var(--color-fg)').attr('stroke-opacity', 0.45).attr('stroke-width', 1.5);
        if (yRows) svg.append('g').selectAll('line').data(aRows).join('line').attr('x1', (r) => x(r.period)).attr('x2', (r) => x(r.period) + x.bandwidth()).attr('y1', (r) => y(val(r))).attr('y2', (r) => y(val(r))).attr('stroke', 'var(--color-fg)').attr('stroke-width', 1.5).attr('stroke-dasharray', '3 2');
        if (cRows) svg.append('path').datum(cRows).attr('d', d3.line().x((r) => cx(r.period)).y((r) => y(val(r)))).attr('fill', 'none').attr('stroke', muted).attr('stroke-width', 2).attr('stroke-linecap', 'round').attr('stroke-linejoin', 'round');
        if (cRows) svg.append('g').selectAll('circle').data(cRows).join('circle').attr('cx', (r) => cx(r.period)).attr('cy', (r) => y(val(r))).attr('r', 3).attr('fill', muted);
      }
      svg.append('line').attr('x1', ml).attr('x2', W - mr).attr('y1', y(0)).attr('y2', y(0)).attr('stroke', 'var(--cds-chart-axis)');
      // end labels, nudged apart
      const ends = [{ t: nameOf[P.place], v: val((yRows || aRows)[11]), c: accent }];
      if (cRows) ends.push({ t: nameOf[cmp], v: val(cRows[11]), c: muted });
      ends.forEach((e) => (e.y = y(e.v)));
      if (ends.length === 2 && Math.abs(ends[0].y - ends[1].y) < 15) {
        const mid = (ends[0].y + ends[1].y) / 2, up = ends[0].y <= ends[1].y ? 0 : 1;
        ends[up].y = mid - 8; ends[1 - up].y = mid + 8;
      }
      svg.append('g').selectAll('text').data(ends).join('text').attr('x', W - mr + 8).attr('y', (e) => e.y + 4).attr('font-size', 12).attr('font-weight', 500).attr('fill', (e) => e.c).text((e) => e.t);
      const tip = tipFor(box);
      svg.append('g').selectAll('rect').data(PERIODS).join('rect').attr('x', (p) => x(p) - x.step() * x.paddingInner() / 2).attr('width', x.step()).attr('y', mt).attr('height', H - mb - mt).attr('fill', 'transparent').style('cursor', 'pointer')
        .on('click', (ev, p) => { stopPlay(); set({ period: p }); })
        .on('mousemove', (ev, p) => {
          const a = get(P.place, 'all', p);
          const lines = [{ text: MONTH[+p - 1] }];
          if (!avg) lines.push({ text: nameOf[P.place] + ' ' + P.year + ': ' + fmt(m, get(P.place, P.year, p)[m], false) + ' ' + unitOf(m, p), color: accent });
          lines.push({ text: nameOf[P.place] + ' average: ' + fmt(m, a[m], true) + ' ' + unitOf(m, p) + ' (range ' + fmt(m, a[m + '_lo'], false) + '–' + fmt(m, a[m + '_hi'], false) + ')', color: avg ? accent : null });
          if (cmp) lines.push({ text: nameOf[cmp] + ' average: ' + fmt(m, get(cmp, 'all', p)[m], true) + ' ' + unitOf(m, p), color: muted });
          tip.show(ev, lines);
        })
        .on('mouseleave', () => tip.hide());
    }

    // ---- heatmap ----
    {
      const box = $('#cb-heat');
      box.replaceChildren();
      $('#cb-heat-title').textContent = M.label + ' in ' + nameOf[P.place] + ', every month';
      const narrow = (box.clientWidth || 600) < 520;
      box.style.gridTemplateColumns = `${narrow ? '2.6rem' : '4.2rem'} repeat(12, minmax(1.9rem, 1fr)) minmax(2.6rem, 1.2fr)`;
      const head = (t) => { const d = document.createElement('div'); d.className = 'cb-hh'; d.textContent = t; box.appendChild(d); };
      head('');
      MON.forEach((mn) => head(narrow ? mn[0] : mn));
      head('Year');
      const mv = YEARS.flatMap((yr) => PERIODS.map((p) => get(P.place, yr, p)[M.id]));
      const yv = YEARS.map((yr) => get(P.place, yr, 'year')[M.id]);
      const sm = d3.scaleLinear().domain(d3.extent(mv)).range([0, 1]);
      const sy = d3.scaleLinear().domain(d3.extent(yv)).range([0, 1]);
      const cell = (yr, p) => {
        const r = get(P.place, yr, p);
        const v = r[M.id];
        const t = p === 'year' ? (sy.domain()[0] === sy.domain()[1] ? 0.5 : sy(v)) : (sm.domain()[0] === sm.domain()[1] ? 0.5 : sm(v));
        const b = document.createElement('button');
        b.type = 'button';
        b.textContent = fmt(M.id, v, yr === 'all');
        b.style.background = ramp(t);
        b.style.color = inkOn(t);
        b.setAttribute('aria-label', (p === 'year' ? 'Whole year' : MONTH[+p - 1]) + ' ' + (yr === 'all' ? 'average' : yr) + ': ' + b.textContent);
        if (yr === P.year && p === P.period) b.classList.add('cb-on');
        b.addEventListener('click', () => { stopPlay(); set({ year: yr, period: p }); });
        box.appendChild(b);
      };
      for (const yr of YEARS) {
        const l = document.createElement('div'); l.className = 'cb-hy'; l.textContent = narrow ? "'" + yr.slice(2) : yr; box.appendChild(l);
        PERIODS.forEach((p) => cell(yr, p));
        cell(yr, 'year');
      }
      const gap = document.createElement('div'); gap.className = 'cb-gap'; box.appendChild(gap);
      const l = document.createElement('div'); l.className = 'cb-hy'; l.textContent = narrow ? 'Avg' : 'Average'; box.appendChild(l);
      PERIODS.forEach((p) => cell('all', p));
      cell('all', 'year');
    }

    // ---- year by year ----
    {
      const box = $('#cb-years');
      box.replaceChildren();
      $('#cb-year-title').textContent = M.label + ' in ' + periodName(P.period) + ', year by year';
      $('#cb-year-note').textContent = 'Bars: ' + nameOf[P.place] + '. Dashed line: its 2017–2025 average.' + (cmp ? ' Grey marks: ' + nameOf[cmp] + '.' : '') + ' Click a bar to select that year.';
      const W = Math.max(300, box.clientWidth || 600), H = 290;
      const m = M.id;
      const pr = YEARS.map((yr) => get(P.place, yr, P.period));
      const cr = cmp ? YEARS.map((yr) => get(cmp, yr, P.period)) : null;
      const a = get(P.place, 'all', P.period);
      const vals = pr.map((r) => r[m]).concat(cr ? cr.map((r) => r[m]) : []);
      const y = d3.scaleLinear().domain([Math.min(0, d3.min(vals)), d3.max(vals)]).nice();
      const svg = d3.select(box).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('width', '100%');
      const ticks = y.ticks(5);
      const ml = textWidth(svg, ticks.map((t) => d3.format(',')(t)), 12) + 10, mr = 12, mt = 18, mb = 26;
      y.range([H - mb, mt]);
      const x = d3.scaleBand().domain(YEARS).range([ml, W - mr]).padding(0.28);
      svg.append('g').selectAll('line').data(ticks).join('line').attr('x1', ml).attr('x2', W - mr).attr('y1', y).attr('y2', y).attr('stroke', 'var(--cds-chart-grid)');
      svg.append('g').selectAll('text').data(ticks).join('text').attr('x', ml - 6).attr('y', (d) => y(d) + 4).attr('text-anchor', 'end').attr('font-size', 12).attr('fill', 'var(--color-fg-muted)').text((d) => d3.format(',')(d));
      svg.append('g').selectAll('text').data(YEARS).join('text').attr('x', (yr) => x(yr) + x.bandwidth() / 2).attr('y', H - 8).attr('text-anchor', 'middle').attr('font-size', 12).attr('fill', 'var(--color-fg-muted)').text((yr) => (W < 420 ? "'" + yr.slice(2) : yr));
      svg.append('g').selectAll('rect').data(pr).join('rect').attr('x', (r) => x(r.year)).attr('width', x.bandwidth()).attr('y', (r) => y(Math.max(0, r[m]))).attr('height', (r) => Math.max(1, Math.abs(y(r[m]) - y(0)))).attr('rx', 4).attr('fill', accent).attr('fill-opacity', (r) => (avg || r.year === P.year ? 1 : 0.45));
      svg.append('line').attr('x1', ml).attr('x2', W - mr).attr('y1', y(0)).attr('y2', y(0)).attr('stroke', 'var(--cds-chart-axis)');
      svg.append('line').attr('x1', ml).attr('x2', W - mr).attr('y1', y(a[m])).attr('y2', y(a[m])).attr('stroke', 'var(--cds-chart-reference)').attr('stroke-width', 1.5).attr('stroke-dasharray', '6 4');
      if (cr) svg.append('g').selectAll('line').data(cr).join('line').attr('x1', (r) => x(r.year) - 3).attr('x2', (r) => x(r.year) + x.bandwidth() + 3).attr('y1', (r) => y(r[m])).attr('y2', (r) => y(r[m])).attr('stroke', muted).attr('stroke-width', 3).attr('stroke-linecap', 'round');
      const tip = tipFor(box);
      svg.append('g').selectAll('rect').data(YEARS).join('rect').attr('x', (yr) => x(yr) - x.step() * x.paddingInner() / 2).attr('width', x.step()).attr('y', mt).attr('height', H - mb - mt).attr('fill', 'transparent').style('cursor', 'pointer')
        .on('click', (ev, yr) => set({ year: P.year === yr ? 'all' : yr }))
        .on('mousemove', (ev, yr) => {
          const lines = [{ text: periodShort(P.period) + ' ' + yr }, { text: nameOf[P.place] + ': ' + fmt(m, get(P.place, yr, P.period)[m], false) + ' ' + unitOf(m, P.period), color: accent }];
          if (cmp) lines.push({ text: nameOf[cmp] + ': ' + fmt(m, get(cmp, yr, P.period)[m], false) + ' ' + unitOf(m, P.period), color: muted });
          lines.push({ text: 'Average: ' + fmt(m, a[m], true) });
          tip.show(ev, lines);
        })
        .on('mouseleave', () => tip.hide());
    }

    // ---- measured vs modelled ----
    {
      const sec = $('#measured');
      const sd = dash.data('station_periods');
      const srows = sd.status === 'ok' ? sd.data : null;
      const hasAny = !!srows;
      sec.hidden = !hasAny;
      if (hasAny) {
        const withMc = srows.some((r) => r.source === 'Meteocat');
        $('#cb-meas-summary').textContent = 'At every station checked, the model counts too many wet days (by roughly a third to two-thirds), so real rideable days are as many as modelled or more. Temperatures vary by region: ' + (withMc ? 'on the Costa Brava, Costa Blanca and around Pollença' : 'on the Costa Blanca and around Pollença') + ' the model runs 1.5–3°C cool by day; on the Costa del Sol it is about right by day but overstates summer heat, with far fewer real days over 30°C than modelled.';
        const sget = (place, year, period) => srows.find((r) => r.place === place && r.year === year && r.period === period);
        const s0 = sget(P.place, P.year, P.period);
        const tb = $('#cb-meas-body');
        const chart = $('#cb-meas-chart');
        tb.replaceChildren();
        chart.replaceChildren();
        if (!s0) {
          $('#cb-meas-title').textContent = 'Measured at a weather station';
          const withSt = places.filter((p) => srows.some((r) => r.place === p.place)).map((p) => p.name);
          $('#cb-meas-note').textContent = 'Station readings are available for ' + withSt.slice(0, -1).join(', ') + (withSt.length > 1 ? ' and ' : '') + withSt.slice(-1) + '. Pick one of those to compare the model with what was actually recorded.';
          $('#cb-meas-grid').hidden = true;
        } else {
          $('#cb-meas-grid').hidden = false;
          $('#cb-meas-title').textContent = 'Modelled vs measured · ' + nameOf[P.place] + ' · ' + periodShort(P.period) + ' · ' + yearName(P.year);
          const src = s0.source === 'AEMET' ? 'Source: Agencia Estatal de Meteorología (AEMET).' : 'Source: Servei Meteorològic de Catalunya (Meteocat), used with permission.';
          const covN = PERIODS.reduce((t, p) => { const r = sget(P.place, 'all', p); return t + (r && r.tmax_n ? r.tmax_n : 0); }, 0);
          const cov = covN / 108;
          const partial = cov < 0.85 ? ' Its record covers about ' + Math.round(cov * 10) * 10 + '% of 2017\u20132025, so averages use only the months it has.' : '';
          $('#cb-meas-note').textContent = 'Measured at ' + s0.source + '\u2019s ' + s0.station_name + ' station, ' + s0.distance_km + ' km away at ' + d3.format(',.0f')(s0.elevation_m) + ' m' + (s0.gust_height_m ? '.' : '. This station has no wind sensor, so rideable days and wind can\u2019t be checked.') + partial + ' ' + src;
          const mrow = get(P.place, P.year, P.period);
          for (const mm of MEASURES) {
            const tr = document.createElement('tr');
            const mv = mrow ? mrow[mm.id] : null, sv = s0[mm.id];
            const cells = [mm.label, fmt(mm.id, mv, avg), sv == null ? '—' : fmt(mm.id, sv, avg)];
            let diff = '—';
            if (mv != null && sv != null) { const dd = sv - mv; diff = (dd > 0 ? '+' : dd < 0 ? '−' : '') + fmt(mm.id, Math.abs(dd), true); }
            cells.push(diff);
            cells.forEach((c, i) => { const td = document.createElement('td'); td.textContent = c + (i > 0 && c !== '—' && mm.unit === '°C' ? '°' : ''); tr.appendChild(td); });
            if (mm.id === M.id) tr.className = 'cb-sel';
            tb.appendChild(tr);
          }
          // seasonal chart, model vs station, chosen measure
          const m = M.id;
          const mr = PERIODS.map((p) => get(P.place, P.year, p));
          const sr = PERIODS.map((p) => sget(P.place, P.year, p));
          const pts = (rows) => rows.map((r, i) => ({ p: PERIODS[i], v: r ? r[m] : null }));
          const A = pts(mr), B = pts(sr);
          const all = A.concat(B).map((d) => d.v).filter((v) => v != null);
          const W = Math.max(300, chart.clientWidth || 520), H = 250;
          const svg = d3.select(chart).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('width', '100%');
          if (!all.length) {
            svg.append('text').attr('x', 12).attr('y', 30).attr('font-size', 13).attr('fill', 'var(--color-fg-muted)').text('This station doesn’t record ' + M.label.toLowerCase() + '.');
          } else {
            const y = d3.scaleLinear().domain([Math.min(0, d3.min(all)), d3.max(all)]).nice();
            const ticks = y.ticks(5);
            const ml = textWidth(svg, ticks.map((t) => d3.format(',')(t)), 12) + 10, mr_ = textWidth(svg, ['Modelled', 'Measured'], 12) + 14, mt = 10, mb = 26;
            y.range([H - mb, mt]);
            const x = d3.scalePoint().domain(PERIODS).range([ml + 8, W - mr_ - 8]);
            svg.append('g').selectAll('line').data(ticks).join('line').attr('x1', ml).attr('x2', W - mr_).attr('y1', y).attr('y2', y).attr('stroke', 'var(--cds-chart-grid)');
            svg.append('g').selectAll('text').data(ticks).join('text').attr('x', ml - 6).attr('y', (d) => y(d) + 4).attr('text-anchor', 'end').attr('font-size', 12).attr('fill', 'var(--color-fg-muted)').text((d) => d3.format(',')(d));
            svg.append('g').selectAll('text').data(PERIODS).join('text').attr('x', (p) => x(p)).attr('y', H - 8).attr('text-anchor', 'middle').attr('font-size', 12).attr('fill', 'var(--color-fg-muted)').text((p) => (W < 420 ? MON[+p - 1][0] : MON[+p - 1]));
            const c2 = resolve(dash.colors[1]);
            const line = d3.line().defined((d) => d.v != null).x((d) => x(d.p)).y((d) => y(d.v));
            svg.append('path').datum(A).attr('d', line).attr('fill', 'none').attr('stroke', accent).attr('stroke-width', 2.5).attr('stroke-linecap', 'round').attr('stroke-linejoin', 'round');
            svg.append('path').datum(B).attr('d', line).attr('fill', 'none').attr('stroke', c2).attr('stroke-width', 2.5).attr('stroke-dasharray', '6 4').attr('stroke-linecap', 'round');
            svg.append('g').selectAll('circle').data(B.filter((d) => d.v != null)).join('circle').attr('cx', (d) => x(d.p)).attr('cy', (d) => y(d.v)).attr('r', 3).attr('fill', c2);
            const lastA = [...A].reverse().find((d) => d.v != null), lastB = [...B].reverse().find((d) => d.v != null);
            const ends = [];
            if (lastA) ends.push({ t: 'Modelled', y: y(lastA.v), c: accent });
            if (lastB) ends.push({ t: 'Measured', y: y(lastB.v), c: c2 });
            if (ends.length === 2 && Math.abs(ends[0].y - ends[1].y) < 15) { const mid = (ends[0].y + ends[1].y) / 2, up = ends[0].y <= ends[1].y ? 0 : 1; ends[up].y = mid - 8; ends[1 - up].y = mid + 8; }
            svg.append('g').selectAll('text').data(ends).join('text').attr('x', W - mr_ + 6).attr('y', (e) => e.y + 4).attr('font-size', 12).attr('font-weight', 500).attr('fill', (e) => e.c).text((e) => e.t);
          }
        }
      }
    }

    // ---- table ----
    {
      $('#cb-table-title').textContent = 'All places · ' + periodShort(P.period) + ' · ' + yearName(P.year);
      const cols = MEASURES;
      const th = $('#cb-thead');
      if (!th.childElementCount) {
        const mk = (field, text) => {
          const h = document.createElement('th');
          h.dataset.field = field;
          h.scope = 'col';
          const b = document.createElement('button');
          b.type = 'button';
          b.textContent = text;
          b.addEventListener('click', () => {
            if (sortState.field === field) sortState.dir *= -1; else { sortState.field = field; sortState.dir = field === 'name' || field === 'region' ? 1 : -1; }
            drawTable();
          });
          h.appendChild(b);
          th.appendChild(h);
        };
        mk('name', 'Place');
        mk('region', 'Region');
        cols.forEach((c) => mk(c.id, c.short + (c.unit === '°C' ? ' °C' : c.unit === 'mm' ? ' mm' : '')));
      }
      drawTable = () => {
        const tb = $('#cb-tbody');
        tb.replaceChildren();
        const regionOf = Object.fromEntries(places.map((p) => [p.place, p.region]));
        regSeg.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.r === P.region)));
        const keep = (p) => P.region === 'all' || p.region === P.region || p.place === P.place || p.place === cmp;
        const data = places.filter(keep).map((p) => get(p.place, P.year, P.period)).filter(Boolean);
        const f = sortState.field;
        const val = (r) => (f === 'region' ? REGIONS.indexOf(regionOf[r.place]) : r[f]);
        data.sort((a, b) => (f === 'name' ? a.name.localeCompare(b.name) : (val(a) - val(b)) || a.name.localeCompare(b.name)) * sortState.dir);
        th.querySelectorAll('th').forEach((h) => {
          h.setAttribute('aria-sort', h.dataset.field === f ? (sortState.dir > 0 ? 'ascending' : 'descending') : 'none');
          h.classList.toggle('cb-col-on', h.dataset.field === M.id);
        });
        for (const r of data) {
          const tr = document.createElement('tr');
          tr.dataset.key = [r.place, r.year, r.period].map(encodeURIComponent).join(',');
          if (r.place === P.place) tr.className = 'cb-sel';
          else if (r.place === cmp) tr.className = 'cb-cmp';
          const td0 = document.createElement('td');
          td0.textContent = r.name;
          tr.appendChild(td0);
          const tdr = document.createElement('td');
          tdr.textContent = r.region;
          tdr.className = 'cb-reg';
          tr.appendChild(tdr);
          for (const c of cols) {
            const td = document.createElement('td');
            td.textContent = fmt(c.id, r[c.id], avg);
            if (c.id === M.id) td.className = 'cb-col-on';
            tr.appendChild(td);
          }
          tr.addEventListener('click', () => set({ place: r.place, frame: 'auto' }));
          tb.appendChild(tr);
        }
      };
      drawTable();
    }
  });
  const named = document.getElementById(location.hash.slice(1));
  if (named) setTimeout(() => named.scrollIntoView(), 300);
})();
