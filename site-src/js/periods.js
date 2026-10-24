dash.calc('periods', {
  inputs: ['climate', 'places'],
  title: 'Monthly, yearly and 9-year figures',
  description: 'Each place, with its region, by month and whole year, for each year and averaged over all years, with the lowest and highest year.',
  fn: (climate, places) => {
    const measures = ['tmax', 'tmin', 'rain', 'wet', 'ride', 'warm', 'hot', 'frost', 'tram'];
    const averaged = ['tmax', 'tmin'];
    const periods = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', 'year'];
    const round = (m, v) => (m === 'rain' ? Math.round(v) : Math.round(v * 10) / 10);
    const names = Object.fromEntries(places.map((p) => [p.place, p.name]));
    const regions = Object.fromEntries(places.map((p) => [p.place, p.region]));
    const groups = {};
    for (const d of climate) {
      const key = d.place + '|' + d.year;
      (groups[key] = groups[key] || []).push(d);
    }
    const out = [];
    const perPlace = {};
    for (const months of Object.values(groups)) {
      const place = months[0].place;
      const year = String(months[0].year);
      const list = (perPlace[place] = perPlace[place] || []);
      for (const d of months) {
        const row = { place, name: names[place], region: regions[place], year, period: String(d.month) };
        for (const m of measures) row[m] = Number(d[m]);
        out.push(row);
        list.push(row);
      }
      const whole = { place, name: names[place], region: regions[place], year, period: 'year' };
      for (const m of measures) {
        const sum = months.reduce((s, d) => s + Number(d[m]), 0);
        whole[m] = round(m, averaged.includes(m) ? sum / months.length : sum);
      }
      out.push(whole);
      list.push(whole);
    }
    for (const place of Object.keys(perPlace)) {
      for (const period of periods) {
        const same = perPlace[place].filter((r) => r.period === period);
        const avg = { place, name: names[place], region: regions[place], year: 'all', period };
        for (const m of measures) {
          const v = same.map((r) => r[m]);
          avg[m] = round(m, v.reduce((s, x) => s + x, 0) / v.length);
          avg[m + '_lo'] = Math.min(...v);
          avg[m + '_hi'] = Math.max(...v);
        }
        out.push(avg);
      }
    }
    return out;
  },
});

dash.calc('station_periods', {
  inputs: ['stations'],
  title: 'Station figures by month and year',
  description: 'Weather-station readings by month and whole year, for each year and averaged over the years with complete data.',
  fn: (stations) => {
    const measures = ['tmax', 'tmin', 'rain', 'wet', 'ride', 'warm', 'hot', 'frost', 'tram'];
    const averaged = ['tmax', 'tmin'];
    const round = (m, v) => (m === 'rain' ? Math.round(v) : Math.round(v * 10) / 10);
    const out = [];
    const byPlace = {};
    for (const d of stations) (byPlace[d.place] = byPlace[d.place] || []).push(d);
    for (const [place, list] of Object.entries(byPlace)) {
      const info = { place, source: list[0].source, station: list[0].station, station_name: list[0].station_name, distance_km: list[0].distance_km, elevation_m: list[0].elevation_m, gust_height_m: list[0].gust_height_m,
        rain_station_name: list[0].rain_station_name, rain_distance_km: list[0].rain_distance_km, rain_elevation_m: list[0].rain_elevation_m };
      const years = [...new Set(list.map((d) => String(d.year)))];
      for (const d of list) {
        const row = { ...info, year: String(d.year), period: String(d.month) };
        for (const m of measures) row[m] = d[m] == null ? null : Number(d[m]);
        out.push(row);
      }
      for (const y of years) {
        const months = list.filter((d) => String(d.year) === y);
        const row = { ...info, year: y, period: 'year' };
        for (const m of measures) {
          const v = months.map((d) => d[m]).filter((x) => x != null).map(Number);
          row[m] = v.length === 12 ? round(m, averaged.includes(m) ? v.reduce((a, b) => a + b, 0) / 12 : v.reduce((a, b) => a + b, 0)) : null;
        }
        out.push(row);
      }
      for (const period of ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', 'year']) {
        const same = out.filter((r) => r.place === place && r.period === period && r.year !== 'all');
        const row = { ...info, year: 'all', period };
        for (const m of measures) {
          const v = same.map((r) => r[m]).filter((x) => x != null);
          row[m] = v.length ? round(m, v.reduce((a, b) => a + b, 0) / v.length) : null;
          row[m + '_n'] = v.length;
        }
        out.push(row);
      }
    }
    return out;
  },
});
