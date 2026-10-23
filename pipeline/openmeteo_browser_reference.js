// Reference only: the exact aggregation that produced the committed climate data (Oct 2026).
// It was run in a browser because the original cloud workspace could not reach open-meteo.com.
// Thresholds: rideable = tmax>=11, rain<1 mm, gust<50 km/h; warm ride = 14<=tmax<=30 + same;
// hot = tmax>=30; frost = tmin<=0; wet = rain>=1 mm; north-wind = gust>=50 & dominant dir >=290 or <=40.
const vars = "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_gusts_10m_max,wind_direction_10m_dominant";
// fetch(`https://archive-api.open-meteo.com/v1/archive?latitude=${lat}&longitude=${lon}&start_date=2017-01-01&end_date=2025-12-31&daily=${vars}&timezone=Europe%2FMadrid`)
function aggregate(D) {
  const M = {};
  for (let i = 0; i < D.time.length; i++) {
    const y = +D.time[i].slice(0, 4), m = +D.time[i].slice(5, 7), idx = (y - 2017) * 12 + m - 1;
    const a = M[idx] || (M[idx] = { n: 0, tx: 0, tn: 0, r: 0, wet: 0, ride: 0, comf: 0, hot: 0, fr: 0, tram: 0 });
    const tx = D.temperature_2m_max[i], tn = D.temperature_2m_min[i], p = D.precipitation_sum[i], g = D.wind_gusts_10m_max[i], dir = D.wind_direction_10m_dominant[i];
    a.n++; a.tx += tx; a.tn += tn; a.r += p; if (p >= 1) a.wet++;
    const calm = g < 50, dry = p < 1;
    if (tx >= 11 && dry && calm) a.ride++; if (tx >= 14 && tx <= 30 && dry && calm) a.comf++;
    if (tx >= 30) a.hot++; if (tn <= 0) a.fr++; if (g >= 50 && (dir >= 290 || dir <= 40)) a.tram++;
  }
  return M; // tmax/tmin = mean rounded to 0.1; rain = sum rounded to integer
}
