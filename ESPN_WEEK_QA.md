# ESPN Weekly calendar — source and draft QA

Base: `101f9661d2127ef9aa1b93c94b1435d46415ed87` in `fantasyorgcat/fantasyorgcat.github.io`. This draft enables the existing ESPN button through the same dynamic schedule/comparison view. NBA event/statistics providers, Yahoo/NBA dates, and workflows are retained.

## Official source and scope

Public season-level URLs, without a league ID, credentials, or login:

- [Season metadata](https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/2027?view=chui_default)
- [Pro-team schedules](https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/2027?view=proTeamSchedules_wl)

Both were independently read through the connected Firecrawl app with maxAge=0 and HTTP 200 on 2026-10-10. Direct executor HTTP reads were blocked by its proxy; no proxy/credential bypass was used. Normal public Git transport restored the exact main checkout. Verification completed at 2026-10-10T16:16:14Z.

The raw JSON text returned by these reads has SHA256:

- metadata: `96b6b8380b3f82d3f6e3ebeae653b883be4ac1b5e6593fef2b0eb8f253e7e441`
- schedules: `356e2532ed2e4c0fedd80e4c566579a492c9adf0877e708a79f7fc4d031b4c4f`

The metadata text hash differs from the earlier research receipt `06867744f9a3db9f90d40d0e2e469e59097d50a9c27b8a1d5438bef1c799cc0c`. No byte-identical claim is made; this independent response was verified directly for source season, period type, each weekly boundary, and the full scoring-period/date mapping. The checked source is a mutable public API; pins identify the actual text read in this executor.

Source season `2027` is 2026–27. `segments[0]` has ID 0; its period type ID 2 / description Weekly provides the weekly scoring-period boundaries. Deduplicating `settings.proTeams[*].proGamesByScoringPeriod` from the schedule view yields 1,200 unique games, no duplicate conflicts, and no period-key/ID conflicts.

Games in scoring period 1 all fall on 2026-10-20 in America/New_York. For every one of the 1,200 games, converting its UTC timestamp to that timezone equals that date plus `scoringPeriodId - 1` days: zero mismatches. This independently supplies the date anchor; metadata's broad season startDate is not treated as the first scoring date.

All daily entries for SP1–174 have source season 2027 and preSeason/postSeason false. Weekly period 25 contains SP175, whose postSeason flag is true, so it is excluded. The committed normalized calendar contains exactly 24 regular NBA-season weeks:

| Period | Eastern dates | Meaning |
|---|---|---|
| ESPN 1 | 2026-10-20–2026-10-25 | Six-day opening |
| ESPN 7 | 2026-11-30–2026-12-06 | Cup first week |
| ESPN 8 | 2026-12-07–2026-12-13 | Cup second week, separate |
| ESPN 11 | 2026-12-28–2027-01-03 | Continuous across New Year |
| ESPN 18 | 2027-02-15–2027-02-28 | Fourteen-day All-Star period |
| ESPN 24 | 2027-04-05–2027-04-11 | Final regular week, SP168–174 |

This is the official full-season Weekly calendar. A private league's matchup, custom start/end dates, or fantasy playoff rounds can differ. The UI note and provenance state that scope; no default 2026–27 fantasy playoff rounds are claimed. Existing custom date inputs remain the manual override.

## Implementation and regression scope

`espn_weekly_dates_2026_27.json` stores explicit dates, source season, scoring-period boundaries, URLs, checked time, response text hashes, and mapping evidence. `fantasy_periods.py` validates calendar continuity, source season/type, the regular SP range, and date/SP agreement. It enables ESPN only when the requested season exactly matches this verified calendar; future seasons retain the disabled “待核” control. There is no new runtime request or dependency.

The existing schedule renderer is shared by all three platforms. Continuous-switch testing exposed an existing retention issue: the removed DataTable still had jQuery data/custom handlers (`$.hasData(retiredTable) === true`), and an initial browser run was stopped when its renderer reached about 7 GB. A one-line `destroy(true)` change removes the retired table through DataTables' cleanup path. [DataTables' API documentation](https://datatables.net/reference/api/destroy%28%29) specifies that removal clears custom events. Regression now asserts the retired node is disconnected and no longer has jQuery data on every ESPN week switch. No general speed or memory bound is promised.

Tests use the isolated, watermarked UI TEST ONLY fixture: 605 roster players, 578 prior-season players, 12 dated events and one undated event. Separate events in each Cup and All-Star half verify aggregation and splitting; this fixture is not real published NBA data.

Final local validation completed 2026-10-10T16:36:41Z. The candidate source is commit `8d239d850723e009bf76e95f1bb8f02a316038a6`; the subsequent QA update changes documentation only.

- 45 unit tests pass; both JavaScript syntax checks pass.
- The real checked-in report security gate passes. The isolated fixture is correctly refused with `Test fixture cannot be published`.
- `test_schedule_browser.py` passes at 1500/390px: all ESPN24 weeks, four three-platform anchor round trips, Cup splitting, All-Star merging, cleared jQuery data on every retired table, filter/search/mode/order preservation, custom ranges, timer/foreground refresh, and empty-selection preservation.
- `test_season_browser.py` passes all NBA25/Yahoo23/ESPN24 periods: every roster row's dates, counts and matchup HTML; unchanged statistics/PR; sorting, filters/modes, mobile scrolling and sticky controls.
- `test_player_tools_browser.py` passes all 72 periods at both 1500/390px: cross-team schedule/date/opponent synchronization, keyboard selection, global ranks, independent comparison period/mode controls, zero/missing schedules, no storage calls and preserved existing storage. No external requests, JS errors or failed resources.
- `test_dashboard_browser.py` passes the existing 605-player dashboard, independent team/search/period/mode controls, numeric percentages/integer totals, collapsed details, mobile page width and reachable columns.

All four browser suites report no JS errors or failed requests. These are executor-local checks, not GitHub CI or live-site acceptance. The new calendar has not been generated or deployed to production, and the PR remains draft awaiting review of its exact final head. No performance bound is claimed from fixture tests.

## Reproduction

Repository-pinned dependencies remain in the existing venv. Playwright, pyee, greenlet and typing_extensions are linked from already-installed executor libraries into `/tmp/fantasy-espn-browser-deps`; no downloads or new credentials were used. Chromium is `/usr/bin/chromium`.

```sh
python -m unittest test_sources test_defense test_schedule test_player_catalog
node --check schedule_tools.js
node --check player_tools.js
python security_gate.py
python test_schedule_browser.py /tmp/fantasy-espn-preview
python test_season_browser.py <local-fixture-url>
python test_player_tools_browser.py <local-fixture-url>
python test_dashboard_browser.py <local-fixture-url>
```

The schedule suite covers all ESPN24 weeks at 1500/390px; Cup halves each have one game in ESPN7/8, Yahoo7 combines both; All-Star halves each have one NBA game, ESPN18/Yahoo17 combine both. Four anchor cases traverse NBA→ESPN→Yahoo→ESPN→NBA, preserving the original NBA half.

The season suite covers NBA25/Yahoo23/ESPN24: all player rows' event dates, game counts and matchup HTML, exact statistics/PR invariance, numeric sorting, filter/mode preservation and mobile scroll/sticky controls. The cross-team comparison suite covers all 72 periods at both widths with two players, ranks, independent period/mode controls, keyboard selection, and storage preservation. Existing custom ranges, timer/foreground refresh, last-week empty selection and quick-view tests remain.

No workflow edits, main/report writes, dispatch, merge, deployment, private league IDs, credentials, or new payments are part of this draft.
