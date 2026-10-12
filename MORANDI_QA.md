# Morandi palette review

Base: `e297ca272591b4689e421ba8902caf14ac68bab9` in `fantasyorgcat/fantasyorgcat.github.io` (repository ID 1101177706). The verified Daily run [38072033267](https://github.com/fantasyorgcat/fantasyorgcat.github.io/actions/runs/38072033267) succeeded on 2026-10-10 at 17:34:51 UTC. Its real report has 610 roster players and NBA25/Yahoo23/ESPN24 available periods. The October 11 08:17 UTC scheduled run had not yet been due during this review; no schedule success is assumed.

## Palette and persistent sources

| Role | Colour | Use |
|---|---|---|
| Warm beige | `#E7E0D4` | Page and sticky toolbar |
| Soft ivory | `#F6F1E8` | Tables, controls, scroll surfaces |
| Warm panel | `#F1ECE4` | Cards, comparison and alternate rows |
| Deep gray blue | `#35434B` | Body, numbers and identity |
| Warm gray | `#5E6364` | Supporting labels and PR |
| Muted blue | `#516A78` | Primary buttons, active platform, sorting |
| Blue gray tint | `#D7E0E1` | Selected controls and teams |
| Soft orange | `#E4CFBB` | Mildly difficult matchup band |
| Dusty rose | `#DFC5C8` | Difficult matchup band |
| Muted blue tint | `#C5D5DC` | Easier matchup band |

`dashboard.css` changes surfaces, hero, controls, headers, rows, comparison, hover, focus, disabled and sorting states. Its existing dimensions and scroll behaviour are retained. `generate_report.py` uses the shared muted text colour for team/PR labels and derives legend colours from `utils.get_color_for_rank`. The existing five rank bands keep the same thresholds; `utils.py` changes only their colours. Badges now state 較難打／稍難打／中段／稍好打／較好打 alongside the original rank/population and game sample. Missing defense remains neutral and explicitly says 防守暫缺. Comparison sorting gets an arrow using its existing accessible sort label; no ranking or JavaScript data logic changes.

These sources are read by every report generation. The draft does not replace the tracked production `index.html` or `data_snapshot.json`. A separately saved interactive review restyles the exact real published report without fetching new data or changing its data timestamp. The next report generation from the reviewed source will embed the palette; publishing requires separate approval.

Additional surface values: control borders `#818B88`; primary hover `#435B69`; orange ink `#735238`; rose ink `#845D64`; keyboard focus `#856044`; error ink `#885058`; table headers `#D7DEDF` / text `#354952`; active stat text `#354D5A`; details `#EAE4DA`; unselected hover `#E2E8E6`; reset hover `#E7DFD4`; disabled surface/text `#DED9D1` / `#555D62`; row dividers `#DED7CC`; hero gradient `#DDD4C5` to `#D9E0DF`. Alpha values are sticky surface `#E7E0D4F5`, hero ornament `#516A7812`, shadows `#516A781C` and matchup border `#35434B18`. The five difficult-to-easy heat colours are `#DFC5C8`, `#E4CFBB`, `#E7DFCF`, `#D7E0DF`, `#C5D5DC`; missing data is `#DEDBD5`.

## Real preview and data preservation

The real review retains `2026-10-10 17:34 UTC`. The snapshot is byte-identical to main, SHA256 `6cde860d32e31b257ab739c2b06072903e59bf237d28a59d2e4ce01a1ace1894`.

A normalization comparison removes only the CSS block, the specified heat/label colours and the added difficulty wording. The complete before/after report is then identical, covering inline scripts, player statistics, PR/Rank, events, periods, timestamps and other markup. The final restyled preview index SHA256 is `a9f2ed3a48043fc9326420c631d7bfc0a675f38d2b0af25ac33b4cce124b905a`. It is a restyled published snapshot, not newly fetched October 11 data.

The isolated generated fixture is clearly marked UI TEST ONLY and is rejected by the publication gate. Final generation separately confirms the embedded stylesheet equals the final `dashboard.css` exactly. No fixture is substituted for the real screenshots or snapshot.

## Validation

- 45 repository unit tests pass; JavaScript syntax checks pass.
- The production and real-preview security gates pass. The synthetic fixture is correctly refused.
- `test_dashboard_browser.py` passes against the 610-player real preview: independent filters, search, period/mode preservation, numeric percentage sorting, total counts, details, mobile horizontal scroll and sticky controls.
- `test_schedule_browser.py` passes at 1500/390px against its isolated fixture: ESPN24, three-platform round trips, Cup/All-Star handling, custom windows, remaining timer/foreground refresh and blank selection preservation.
- `test_season_browser.py` passes every NBA25/Yahoo23/ESPN24 period, with exact statistics/PR invariance and schedule/date/opponent checks.
- `test_player_tools_browser.py` passes all 72 periods at both widths, comparison, ranks, sorting, independent controls and storage preservation.
- Additional real before/after checks at 1500/390px preserve 610 players and all platform counts, compare Victor Wembanyama and Nickeil Alexander-Walker through all platforms, and exercise AVG/TOT, Rank sorting, hover, 3px keyboard focus and dashed disabled state. No page-wide mobile overflow, external requests, JS errors or failed resources.

Sampled normal text contrast is 4.65–7.79; input boundary contrast 3.12 and focus contrast 4.27. An expanded check identified 4.38 for supporting text on the page background; the shared muted ink was slightly deepened to #5E6364 and final real previews were recaptured at both widths. The values now include supporting text directly on the warm page background as well as the main surfaces, selected platform/stat controls, header, PR and the darkest heat background. They are scoped palette measurements, not a complete accessibility certification. The disabled appearance was temporarily exercised in the isolated browser; all three verified production-season platforms remain enabled.

These are cloud-executor checks, not GitHub CI or new live-site acceptance. Repository requirements were installed into an isolated temporary venv; Playwright/Chromium were already present. No new credential, payment, workflow edit, dispatch, merge or public deployment was made.

Measured final contrast (both 1500/390px real previews): body 7.79; supporting text on page 4.65, on panel 5.18; hero 6.95; hero accent 4.78; active platform 5.07; active statistics 6.63; table header 6.92; PR 5.42; badge text 6.30; input boundary 3.12; focus 4.27. Additional palette pair checks: disabled text 4.78, hover text 8.23, rose metric 4.79, orange metric 5.97 and error text 5.36. Final generation embeds the corrected shared ink. The single muted-ink follow-up leaves all data and JavaScript unchanged; it received fresh real viewport/interaction checks, generation comparison and security validation. The full existing four-suite functional results remain the prior completed runs.

```sh
python -m unittest test_sources test_defense test_schedule test_player_catalog
node --check schedule_tools.js
node --check player_tools.js
python security_gate.py
CHROMIUM_PATH=/usr/bin/chromium python test_schedule_browser.py <isolated-fixture-directory>
CHROMIUM_PATH=/usr/bin/chromium python test_dashboard_browser.py <real-review-url>
CHROMIUM_PATH=/usr/bin/chromium python test_season_browser.py <fixture-url>
CHROMIUM_PATH=/usr/bin/chromium python test_player_tools_browser.py <fixture-url>
```

## Before and after

Desktop home: [before](docs/morandi/before-home-1500.png) / [after](docs/morandi/after-home-1500.png).

![After: desktop home](docs/morandi/after-home-1500.png)

Desktop schedule: [before](docs/morandi/before-schedule-1500.png) / [after](docs/morandi/after-schedule-1500.png).

![After: desktop schedule](docs/morandi/after-schedule-1500.png)

390px home: [before](docs/morandi/before-home-390.png) / [after](docs/morandi/after-home-390.png).

![After: 390px home](docs/morandi/after-home-390.png)

390px schedule: [before](docs/morandi/before-schedule-390.png) / [after](docs/morandi/after-schedule-390.png).

The cloud review bundle also contains before/after comparison and focus screenshots, the interactive real preview, fixture results, and preservation/contrast evidence. The review bundle is local/downloadable; no public preview site has been deployed.
