# Schedule periods validation — 2026-10-09

Validated in the selected cloud executor. Source base: 92ff09b0e6bdf2ac66adc0434cbf6ade40731c38, branch feature/schedule-periods-2026-10. No user computer was used. Production index.html/data_snapshot.json were not regenerated or changed; the live site was not deployed.

## Passed

- Repository unit command: python -m unittest test_sources test_defense test_schedule test_player_catalog — 39 tests. Includes UTC/Eastern/Taipei date boundaries, DST, cross-year calendar continuity, undated/time-TBD events, event identity and season type, postponed/cancelled/final handling, window counts and existing PR/TO/statistics tests.
- node --check player_tools.js and node --check schedule_tools.js.
- python security_gate.py — existing tracked production report/resource integrity and provenance gate.
- The gate correctly rejects the explicitly marked offline synthetic preview as test data.
- test_schedule_browser.py on 1500px and 390px: partial four-day shortcut; 1/7/14/31-day custom periods; cross-year; invalid/reversed/32-day ranges; empty periods; Eastern/Taipei display; future remaining games; B2B and 1–5-game light days; pending source statuses; comparison synchronisation; preserved statistics, PR, filters, period/mode and rank sorting; no page horizontal overflow; no JS errors or failed resource requests.
- Existing test_season_browser.py: 25 site calendar weeks, empty and cross-year options, dates/opponents/counts, exact statistics/PR and percent sorting, team/mode preservation, quick controls and mobile horizontal scroll.
- Existing test_dashboard_browser.py: 605-player fixture, team/all/team, independent quick weeks, period/mode/search reset, sorting, collapsed details, sticky controls and 390px scroll.
- Existing test_player_tools_browser.py on 1500px and 390px: cross-team keyboard comparison; all 25 weeks; exact schedule synchronisation; invariant global PR ranks and numeric sorts; missing periods; clear/remove; no app storage calls and existing browser data preserved; no JS errors, failed or external requests.

Browser checks use an isolated 605-player synthetic fixture, not current upstream data. Opening and closing fixture dates produce 25 calendar weeks; every test-data preview is labelled UI TEST ONLY and has fixture=true provenance. This proves UI/data handling, not current ESPN/PBP availability or live site correctness.

## Environment and reproducibility

Python 3.12.14 with an isolated venv containing repository-pinned requirements; Chromium 151.0.7922.173 on Debian GNU/Linux 13. CI uses Python 3.11, so this is not an identical runtime reproduction. Playwright was already installed in the cloud environment.

Run the normal unit command and both node syntax checks. With Playwright/Chromium available, run:

```sh
CHROMIUM_PATH=/path/to/chromium python test_schedule_browser.py /tmp/fantasy-schedule-preview
python -m http.server 8765 --bind 127.0.0.1 --directory /tmp/fantasy-schedule-preview
```

Against that cloud/local fixture URL, run the three existing browser scripts with CHROMIUM_PATH set. The fixture server and artifacts are review tools and are never deployment inputs.

## Remaining gates

- Current upstream data fetches: direct ESPN teams and PBP get-games requests returned ProxyError in this executor. No live-source generation succeeded or was attempted as a full production refresh.
- Public Pages readback returned 403; no current CDN byte comparison or live new-version UI acceptance.
- Last freshly verified real snapshot: 2026-10-01 13:11 UTC. Latest readable NBA workflow 36866601567 succeeded in generation/deployment on October 1; no later schedule runs were visible. Existing YAML says 08:17 UTC, which alone does not prove daily operation.
- Official Yahoo/ESPN full current-season matchup tables are not verified. This change exposes the site calendar and custom dates and does not claim an official mapping.
- No roster/position/health/acquisition/GP-cap integration: team scheduled games and future B2B/light days are not usable fantasy starts or an optimizer.
- Existing ESPN/PBP redistribution uncertainty remains. No new provider, subscription, credentials or persistent permission was introduced.
- Merge, fresh-source production generation and production deployment require final acceptance. No performance improvement is promised; no browser profiling was performed.

Next small batch: counting-points/category preferences with explicit GP and sample-size context; preserve made/attempted denominators before percentage contribution tools. Role/usage/health causes and two-for-one open-slot value require additional data and league context.
