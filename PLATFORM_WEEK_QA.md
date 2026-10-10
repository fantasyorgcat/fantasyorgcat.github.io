# Platform week picker validation — 2026-10-10

Base: `906579ff04e09bf68b25bfc95799c581f9e49f5b`, branch `feature/platform-week-picker-2026-10`, selected cloud executor only. No user computer was used. No local AGENTS.md or `.agents/skills` instructions were present. No production refresh, dispatch, merge or deployment was performed for this draft; tracked index.html/data_snapshot.json are unchanged.

## Calendar evidence and behavior

- Yahoo's current public [2026–27 Game Dates](https://basketball.fantasysports.yahoo.com/nba/gamedates) table was read successfully on 2026-10-10 (public page, HTTP 200). All 23 explicit periods are recorded in yahoo_game_dates_2026_27.json with source, season, timezone, verification timestamp and default playoff boundaries. Week 1 is Oct 20–25; week 7 Nov 30–Dec 13; week 17 Feb 15–28. Default fantasy playoffs are weeks 20–22, March 15–April 4; week 23 ends April 11. No next-season extrapolation.
- NBA means this site's Eastern Monday–Sunday schedule calendar, currently 25 weeks starting Oct 19. NBA event data remains from ESPN sports API when switching calendar type.
- ESPN's complete current fantasy period table has not been verified. Its visible button is disabled with “待核”; there is no cloned Yahoo/NBA calendar or inferred special week.
- Three platform buttons and one dropdown replace the expanded primary controls. Custom dates and the four original quick views remain under a closed “自訂期間／近期快捷” section. Switching uses an Eastern date anchor, retained across merged Yahoo weeks. New dropdown/custom selections reset the anchor; initial loading anchors to Eastern today.
- One shared dynamic table handles platform and custom periods. Main schedule, comparison and insights use the same dates. Static statistics and PR are retained. Search, team, stat period, AVG/TOT, metric sort, page length and cross-team comparison persist across platform switches.

## Local validation

Python 3.12.14, exact repository requirements in an isolated venv, Debian 13.6, existing Chromium 151.0.7922.173 and Playwright. GitHub workflow uses Python 3.11; this is not identical-runtime CI validation. There is no pull_request test trigger in this repository; these results are executor-local.

Passed:

- `python -m unittest test_sources test_defense test_schedule test_player_catalog`: **43 tests**, including four new calendar cases: exact Yahoo/NBA differences and special weeks, next-season Yahoo disabled, invalid gaps/overlaps/lengths/numbers rejected, and no invented NBA periods when event dates are absent. Existing UTC/Eastern/Taipei, DST, TO, PR, source failure and aggregation checks remain.
- `node --check player_tools.js` and `node --check schedule_tools.js`.
- `python security_gate.py` on the existing production report; synthetic generated preview is correctly rejected as test data. Same local resource count, CSP and integrity contract; no new runtime requests, subscription or credentials.
- `test_schedule_browser.py`, 1500px and 390px: three buttons, ESPN disabled, NBA25/Yahoo23 options; Yahoo6-day opening and both14-day long weeks; cross-year and default playoffs; date-anchored Yahoo8↔NBA9; NBA19→Yahoo17→NBA19 round trip; preserved search/team/stat mode/rank ordering/page length; comparison exact headers; custom1/7/14/31 days; invalid ranges; empty periods; remaining/B2B/light-day counts; timer across tipoff and immediate foreground refresh; week25 then empty placeholder preserves all panels; static statistics unchanged; no JS errors or failed resources.
- `test_season_browser.py`: all **25 NBA + 23 Yahoo periods** checked against fixture event dates, statuses, opponent HTML and game counts for every player row; exact full statistics/PR cells match original template in all periods; numeric counts and FG/FT sorting; filter/mode persistence, all-player reset, 390px horizontal scroll and sticky reachable platform/selector/reset controls.
- `test_dashboard_browser.py`: 605-player roster, all four original quick views, independent team filters, all/search reset, period/mode retention, numeric percentage and integer totals, collapsed controls, mobile overflow and scroll behavior; no JS errors or failed resources.
- `test_player_tools_browser.py`, 1500px and 390px: cross-team keyboard selection, every NBA week comparison, invariant global ranks and numeric sorting, missing values, safe text, removal/clear, zero application storage calls and preserved existing browser data; no JS errors, failed or external requests.

Browser tests use an isolated **605-player / 578-last-season, 9-event synthetic fixture**, clearly labelled UI TEST ONLY with fixture=true provenance. It does not claim fresh upstream availability, production rendering, real player projections or live acceptance. Screenshots and JSON outputs are review evidence and must not be deployed.

## Size and remaining limitations

Real checked-in main index.html: **33,074,512 bytes**. Identical old/new synthetic fixture: **30,165,745 → 24,166,200 bytes** (5,999,545 bytes, about19.9% smaller). Removal of an extra complete season player panel and repeated rich season HTML avoids another Yahoo table copy. No performance profile or speed guarantee; final production-generated size has not been measured.

The Library reference screenshot `libfile_4e64515b8a2c819192a976d0486ecaa1` was resolved. Both the initial supported materialization and the single consumer-local retry failed to download; both expected files were confirmed absent. Native image read returned a pointer/caption without pixels, so the provided reference was **not visually inspected**. This draft follows the explicit three-button/dropdown request independently; it does not claim visual matching. Generated draft screenshots were inspected locally at desktop/mobile sizes.

Latest real snapshot and source are October10 11:28 UTC / `906579f`. Existing [Daily run #11](https://github.com/fantasyorgcat/fantasyorgcat.github.io/actions/runs/38048334584) completed successfully October10 11:28:55 UTC, including deployment of the report commit. Direct Pages readback from this executor is blocked by network proxy403; the parent thread verified the live11:28 timestamp. This does not mean this new draft UI is already deployed.

ESPN full fantasy weeks remain unverified. Yahoo public defaults are not a private league's settings. Event postponements are current-snapshot states, not complete rescheduling history. Remaining games do not incorporate health, lineup eligibility, acquisitions or GP caps. Data capture and league-state expansion options are documented in DATA_CAPABILITIES.md, not added to this schedule PR.

## Review and release

Review the draft source/explicit calendar and evidence first. A merge alone would stage the existing checked-in page; it does not regenerate the UI. Following acceptance, the existing Daily NBA Fantasy Update path must generate real non-fixture data, pass units and `security_gate.py --generated`, commit the real index/snapshot and deploy that exact report SHA. Check completed generation/deployment jobs and then the actual Pages timestamp/content and platform UI. No workflow dispatch, auth change, new credential or paid API is needed in this draft.
