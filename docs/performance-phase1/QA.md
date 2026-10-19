# Phase 1 performance work

Base: `8fd07540415da196afe18f7d664f1c55224d3b05` (2026-10-16 snapshot). No data refresh, layout redesign, storage migration, deployment, workflow change or new network request is included.

## Changes

- Give DataTables the intended initial column visibility, avoiding measurement of every inactive period/mode and schedule column. The generated HTML, all rows, four quick views and custom-period template remain present; this is not the later single-table rewrite.
- Cache rank-cell updates per period/mode header and selected-category signature, so revisiting a view does not rewrite every rank cell. Category changes invalidate the relevant header, and a new page snapshot naturally gets fresh caches.
- Prepare rank, schedule visibility and ordering before one final adjust/draw. Hidden views do not receive display updates; rebuilt quick/custom views receive the current preferences before their final draw.
- Batch fixed-width sizing in one animation frame and disconnect the observer when a table is destroyed. Font, spacing and day-width controls no longer redraw the data when only geometry changed.
- Cache at most 16 date-range selections within the immutable page snapshot; share daily game counts and table-specific team fixtures with player comparison. Teams with no games retain real zero and empty dates.
- Refresh insights on period/team-filter/preference/minute/foreground changes, not on every table search/sort/page event. Filter changes have an explicit event. Skip duplicate work for the same inputs within the same minute.
- Restrict comparison draw updates to the active table; collapse overlapping translation mutation roots to avoid walking the same subtree multiple times.

## Correctness and UI

- All embedded player/stat catalogs, events, platform and quick calendars, source timestamps, ROTO data/core/UI and CSS are unchanged. The published HTML body is byte-identical; only its inline script changed. Standalone JavaScript changes are mirrored in the published report and its Python generator.
- `test_phase1_performance_browser.py`: all four periods x AVG/TOT, full-list numeric/order values and ranks, one draw per combined view change, no unnecessary insights replacement, shared schedule including zero-game teams, custom PR rank, comparison across weeks/quick tabs, date-header synchronization after deferred sizing, filter changes, released resize observations and unchanged data/storage. Real snapshot, 1440/390px.
- `test_table_preferences_browser.py`: 1327/1500/390/320px fixed geometry, full Rank access, custom ranking, missing values, persistent display preferences and blocked storage. Player columns remain 160,64,11x88/98px as applicable.
- `test_schedule_locale_browser.py`: 1440/390px Yahoo/Taipei defaults, six rows, compact schedule, local clocks/date columns, language roundtrip, ROTO controls and existing roster preservation.
- `test_sticky_headers_browser.py`: 1500/390px real snapshot, sticky header below responsive navigation, horizontal/touch scrolling, sorting, rebuilt periods/modes, palette and data preservation.
- Python suite: 68 tests. Node suites: table tools, site UI, ROTO core and team tools. Public resource/security staging gate and `git diff --check`.
- Two population-dependent tests were made snapshot-independent: active list count uses the catalog length; archived-source mapping counts are checked by one-to-one source identity and conservation of source/catalog counts. Before this change, the unchanged base failed the old 481-player assertion because the latest catalog has 483 matched players. Numeric/source integrity checks remain in place.

## Performance method

Run `python test_performance_benchmark.py /path/to/exported-base /path/to/output` with Chromium installed. The script serves the exported base and current checkout locally, sequentially, with the same data snapshot. Each version/viewport has five new-context cold and five same-context warm navigations. Desktop:1440px/normal CPU; mobile simulation:390px/CPU4x. Each mode/period/page/search/week operation has 30 samples, including its first use, and waits for two animation frames to include queued layout/localization work.

These are laboratory results, not official-site TTFB, field INP, or measurements from a particular phone. The official URL is blocked by this environment's CONNECT proxy (403). Network compression and edge caching are not measured here. Phase 1 intentionally retains the ~27 MB decoded HTML and its parsing cost.

The sequential measurements below contain 40 navigations and 600 interactions. Completed baseline groups were reused across interrupted candidate diagnostics; final candidate results all use the same frozen HTML hash.

## Measured results (milliseconds)

Five cold and five warm samples per version/device; medians below. 390px uses CPU4x simulation.

| Setup | Metric | Before | After | Reduction |
|---|---|---:|---:|---:|
| Desktop cold | long-task total | 6396.0 | 3605.0 | 43.6% |
| Desktop cold | last initial long-task end | 7105.6 | 4384.4 | 38.3% |
| Desktop cold | FCP | 344.0 | 400.0 | -16.3% |
| Desktop warm | long-task total | 6418.0 | 3286.0 | 48.8% |
| Desktop warm | last initial long-task end | 7187.9 | 4144.5 | 42.3% |
| Desktop warm | FCP | 132.0 | 132.0 | 0.0% |
| 390px CPU4x cold | long-task total | 34708.0 | 19022.0 | 45.2% |
| 390px CPU4x cold | last initial long-task end | 35580.5 | 20045.1 | 43.7% |
| 390px CPU4x cold | FCP | 1096.0 | 1228.0 | -12.0% |
| 390px CPU4x warm | long-task total | 34841.0 | 18508.0 | 46.9% |
| 390px CPU4x warm | last initial long-task end | 35653.2 | 19289.3 | 45.9% |
| 390px CPU4x warm | FCP | 456.0 | 456.0 | 0.0% |

Interaction duration includes two animation frames; this is not field INP. All 30 samples include the first switch.

| Setup | Operation | First before → after | p95 before → after | Worst before → after |
|---|---|---:|---:|---:|
| Desktop | mode | 441.7 → 334.7 | 500.8 → 153.9 | 552.9 → 334.7 |
| Desktop | period | 405.5 → 259.0 | 444.0 → 219.0 | 593.2 → 259.0 |
| Desktop | page | 38.4 → 33.2 | 55.4 → 37.8 | 56.0 → 40.8 |
| Desktop | search | 35.1 → 30.2 | 58.6 → 42.5 | 60.7 → 44.2 |
| Desktop | week | 2033.8 → 941.6 | 3033.1 → 1107.1 | 3501.4 → 1130.7 |
| 390px CPU4x | mode | 2475.4 → 1565.6 | 2686.2 → 824.1 | 2797.0 → 1565.6 |
| 390px CPU4x | period | 2079.5 → 1499.0 | 2482.6 → 992.7 | 2836.3 → 1499.0 |
| 390px CPU4x | page | 304.3 → 232.0 | 282.4 → 249.5 | 304.3 → 254.6 |
| 390px CPU4x | search | 165.4 → 156.4 | 291.8 → 289.5 | 312.8 → 289.8 |
| 390px CPU4x | week | 11673.2 → 4955.3 | 16774.8 → 5415.0 | 16994.5 → 5770.5 |

## Limits and stage gate

- Initialization and interactions improved, but the proposed 50% reduction and universal 200ms/500ms interaction goals are not fully met. Read the first/worst samples alongside p95.
- FCP did not improve in this run. The HTML remains ~27 MB decoded; do not describe the result as a download-size optimization or a speedup in every loading metric.
- Week changes still clone and initialize the full player table. This is the main remaining interaction cost and supports evaluating the planned data-driven table stage separately.
- No official-site network/real-phone performance acceptance or production deployment was performed.
- Raw data: [benchmark-results.json](benchmark-results.json); aggregates: [benchmark-summary.json](benchmark-summary.json).
- Data preservation: [data-preservation.json](data-preservation.json); functional checks: [functional-results.json](functional-results.json).
