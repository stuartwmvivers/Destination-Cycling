@echo off
rem Run by Windows Task Scheduler (task "Destination Cycling weather fetch"): fetches weather points until the
rem day's Open-Meteo allowance is used up, then exits. Progress: %DC_CACHE%\work\weather_status.json and weather_fetch.log.
set DC_CACHE=C:\ai-projects\DestinationCyclingCache
cd /d "%~dp0..\.."
"%DC_CACHE%\venv\Scripts\python.exe" pipeline\score\weather_fetch.py --until-limit >> "%DC_CACHE%\work\weather_fetch_console.log" 2>&1
