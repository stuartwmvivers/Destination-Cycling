#!/usr/bin/env python3
"""Fetch daily weather for the score's weather points (WORK/weather_points.json) from Open-Meteo's historical
archive: same source, period and timezone as the site's climate data (HANDOVER 4.1), but only the three variables
the rideable-day rule needs (daily high, precipitation, max gust), to stay within the free tier.

The free tier weights each request by its size: nine years of three daily variables is roughly 70 'calls', against
limits of about 600 a minute, 5,000 an hour and 10,000 a day, so only ~140 points fit in a day (~2 hours at the
pace below). Each point is saved to WORK/weather/<id>.json as it arrives: stop any time and re-run to continue.

Progress is written after every point to WORK/weather_status.json (and appended to WORK/weather_fetch.log), for the
daily check. A lock file stops two copies running at once.

Usage (score venv):
  python pipeline/score/weather_fetch.py                 run until done, waiting out each limit (interactive use)
  python pipeline/score/weather_fetch.py --until-limit   stop cleanly when the daily allowance is used up (scheduled use:
                                                         pipeline/score/run_weather_fetch.cmd, run by Windows Task Scheduler)
"""
import datetime as dt, json, os, sys, time, urllib.error, urllib.request
from common import WORK

START, END = '2017-01-01', '2025-12-31'
VARS = 'temperature_2m_max,precipitation_sum,wind_gusts_10m_max'
PACE_S = 50          # between requests: ~70 an hour, under the hourly allowance
OUT = os.path.join(WORK, 'weather')
STATUS = os.path.join(WORK, 'weather_status.json')
LOG = os.path.join(WORK, 'weather_fetch.log')
LOCK = os.path.join(WORK, 'weather_fetch.lock')

def url(p):
    return (f"https://archive-api.open-meteo.com/v1/archive?latitude={p['lat']}&longitude={p['lon']}"
            f"&start_date={START}&end_date={END}&daily={VARS}&timezone=Europe%2FMadrid")

def now():
    return dt.datetime.now().astimezone().isoformat(timespec='seconds')

def log(msg):
    line = f'{now()}  {msg}'
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f: f.write(line + '\n')

def status(total, **kw):
    s = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    done = len([f for f in os.listdir(OUT) if f.endswith('.json')])
    s.update(total=total, fetched=done, complete=done >= total, updated=now(), **kw)
    json.dump(s, open(STATUS, 'w'), indent=1)

def limit_kind(msg):
    m = msg.lower()
    return 'daily' if 'daily' in m else 'hourly' if 'hourly' in m else 'minutely'

def lock():
    """True if we got the lock. A lock older than 8 hours is treated as left over from a crash."""
    if os.path.exists(LOCK) and time.time() - os.path.getmtime(LOCK) < 8 * 3600: return False
    open(LOCK, 'w').write(str(os.getpid())); return True

def main(until_limit):
    os.makedirs(OUT, exist_ok=True)
    pts = json.load(open(os.path.join(WORK, 'weather_points.json')))['points']
    todo = [p for p in pts if not os.path.exists(os.path.join(OUT, f"{p['id']}.json"))]
    if not todo:
        status(len(pts), last_message='all weather points fetched'); log('nothing to do: all weather points fetched'); return
    if not lock():
        log('another copy is running (lock file present); exiting'); return
    try:
        log(f'start: {len(pts) - len(todo)} of {len(pts)} fetched, {len(todo)} to go')
        status(len(pts), last_run_started=now(), last_message='running')
        got = 0
        for p in todo:
            while True:
                try:
                    with urllib.request.urlopen(url(p), timeout=120) as r:
                        j = json.loads(r.read().decode('utf-8'))
                    break
                except urllib.error.HTTPError as e:
                    if e.code != 429: raise
                    kind = limit_kind(e.read().decode('utf-8', 'replace'))
                    if kind == 'daily' and until_limit:
                        log(f'daily allowance used up after {got} points this run; stopping until the next scheduled run')
                        status(len(pts), last_run_ended=now(), last_run_points=got, last_message='daily limit reached; will continue at the next scheduled run')
                        return
                    wait = {'minutely': 65, 'hourly': 3700}.get(kind)
                    if wait is None:   # daily limit, interactive mode: wait until just after midnight UTC
                        n = dt.datetime.now(dt.timezone.utc)
                        wait = ((n + dt.timedelta(days=1)).replace(hour=0, minute=10, second=0, microsecond=0) - n).total_seconds()
                    log(f'{kind} limit: waiting {wait / 60:.0f} min'); status(len(pts), last_message=f'{kind} limit: waiting')
                    time.sleep(wait)
                except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                    log(f'network problem ({e}); retrying in 60 s'); time.sleep(60)
            d = j['daily']
            assert d['time'][0] == START and len(d['time']) == 3287, f"unexpected days for point {p['id']}"
            json.dump({'id': p['id'], 'lat': p['lat'], 'lon': p['lon'], 'grid_lat': j['latitude'], 'grid_lon': j['longitude'],
                       'model_elev': j['elevation'], 'tmax': d['temperature_2m_max'], 'precip': d['precipitation_sum'],
                       'gust': d['wind_gusts_10m_max']}, open(os.path.join(OUT, f"{p['id']}.json"), 'w'), separators=(',', ':'))
            got += 1
            log(f"{p['id']} fetched (grid {j['latitude']:.3f},{j['longitude']:.3f}, {j['elevation']:.0f} m)")
            status(len(pts), last_point=p['id'], last_message='running')
            os.utime(LOCK, None)
            time.sleep(PACE_S)
        log('all weather points fetched')
        status(len(pts), last_run_ended=now(), last_run_points=got, last_message='all weather points fetched')
    except Exception as e:
        log(f'ERROR: {e!r}'); status(len(pts), last_run_ended=now(), last_message=f'error: {e!r}'); raise
    finally:
        if os.path.exists(LOCK): os.remove(LOCK)

if __name__ == '__main__':
    main('--until-limit' in sys.argv)
