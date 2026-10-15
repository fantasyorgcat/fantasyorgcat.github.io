"""Browser regressions for review findings: sticky layout, paging and truthful Undo."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ORIGIN = (sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8775').rstrip('/')
OUTPUT = Path(sys.argv[2] if len(sys.argv) > 2 else '/tmp/site-ux-edges')


def open_editor(page, name):
    editor = page.locator('#' + name)
    if not editor.evaluate('(e) => e.open'):
        editor.locator('summary').click()


def undo(page):
    page.locator('#status [data-undo]').click()


def fail_writes(page):
    page.evaluate("""() => {
        window.originalStorageWrite = Storage.prototype.setItem;
        Storage.prototype.setItem = function () {
            throw new DOMException('review simulated quota', 'QuotaExceededError');
        };
    }""")


def restore_writes(page):
    page.evaluate('() => { Storage.prototype.setItem = window.originalStorageWrite; }')


def stored(page, key):
    return page.evaluate('(key) => localStorage.getItem(RotoCore[key])', key)


def seed(page, ids):
    page.evaluate("""(ids) => {
        RotoCore.saveOpponents(localStorage, [
            {id:'opponent-alpha',name:'Alpha',players:ids,savedAt:''},
            {id:'opponent-beta',name:'Beta',players:[ids[0]],savedAt:''}
        ]);
        RotoCore.save(localStorage, [
            {id:'saved-a',name:'A盟',players:ids.slice(0,2),savedAt:''},
            {id:'saved-b',name:'B盟',players:ids.slice(2,4),savedAt:''}
        ]);
    }""", ids)
    page.goto(ORIGIN + '/roto.html#players=' + ','.join(ids[:51]))
    page.reload()
    page.wait_for_selector('#roto-player-table tbody input')


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'), args=['--no-sandbox'])
        for width, height in [(1500, 1000), (390, 844)]:
            context = browser.new_context(viewport={'width': width, 'height': height}, is_mobile=width < 600,
                                          has_touch=width < 600, reduced_motion='reduce')
            page = context.new_page()
            errors, console_errors, external = [], [], []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('console', lambda m: console_errors.append(m.text) if m.type == 'error' else None)
            page.on('request', lambda r: external.append(r.url) if not r.url.startswith(ORIGIN + '/') and not r.url.startswith('data:') else None)
            page.goto(ORIGIN + '/roto.html')
            page.wait_for_selector('#roto-player-table tbody input')
            ids = page.evaluate('Object.keys(ROTO_DATA.players).slice(0,60)')
            seed(page, ids)

            # ResizeObserver measurements must reach the sticky elements through inheritance.
            page.locator('[data-jump="player-picker"]').click()
            page.evaluate('scrollBy(0, 500)')
            page.wait_for_function("""() => {
                const nav=document.querySelector('.section-nav').getBoundingClientRect();
                const controls=document.querySelector('.picker-controls').getBoundingClientRect();
                const head=document.querySelector('.dt-scroll-head').getBoundingClientRect();
                return controls.top >= nav.bottom - 1 && head.top >= controls.bottom - 1;
            }""")
            bounds = page.evaluate("""() => Object.fromEntries(['.section-nav','.picker-controls','.dt-scroll-head'].map(s => {
                const r=document.querySelector(s).getBoundingClientRect();return [s,{top:r.top,bottom:r.bottom}];
            }))""")
            page.screenshot(path=str(OUTPUT / f'sticky-{width}.png'))

            # Removing the last row of the last filtered page must reveal remaining players.
            page.locator('#selected-only').click()
            page.evaluate('jQuery("#roto-player-table").DataTable().page(2).draw(false)')
            assert page.locator('#roto-player-table tbody input').count() == 1
            last_id = page.locator('#roto-player-table tbody input').get_attribute('data-roto-pick')
            page.locator('#roto-player-table tbody input[data-roto-pick="' + last_id + '"]').click()
            assert page.locator('#roto-player-table tbody input').count() == 25
            assert page.evaluate('jQuery("#roto-player-table").DataTable().page.info().start') == 0
            open_editor(page, 'opponent-editor')
            page.locator('#active-opponent').select_option('opponent-alpha')
            page.evaluate('jQuery("#roto-player-table").DataTable().page(2).draw(false)')
            page.locator('#active-opponent').select_option('opponent-beta')
            assert page.locator('#roto-player-table tbody input').count() == 1
            assert page.evaluate('jQuery("#roto-player-table").DataTable().page.info().start') == 0
            player_name = page.evaluate('(id) => ROTO_DATA.players[id].name', ids[0])
            page.locator('#player-search').fill(player_name)
            page.locator('#add-target').select_option('base')
            expect(page.locator('#player-search')).to_have_value(player_name)
            assert page.evaluate('jQuery("#roto-player-table").DataTable().search()') == player_name
            page.locator('#clear-search').click()
            page.locator('#selected-only').click()

            # Invalidation removes the whole stale undo toast, including its unbounded lifetime.
            open_editor(page, 'base-editor')
            page.locator('#clear-base').click()
            expect(page.locator('#status [data-undo]')).to_be_visible()
            page.locator('#mode').select_option('perGame')
            expect(page.locator('#status')).to_be_hidden()

            # Undo a saved active roster deletion without replacing the current unsaved edits.
            page.locator('#base-roster-select').select_option('saved-a')
            open_editor(page, 'base-editor')
            page.locator('#base-roster-name').fill('A盟未儲存名稱')
            page.locator('#base-list button').first.click()
            edited = page.locator('#base-list [data-player-id]').evaluate_all('(els) => els.map(e => e.dataset.playerId)')
            before = stored(page, 'storageKey')
            page.locator('#saved-rosters').select_option('saved-a')
            page.locator('#delete-roster').click()
            undo(page)
            assert stored(page, 'storageKey') == before
            expect(page.locator('#base-roster-select')).to_have_value('saved-a')
            expect(page.locator('#base-roster-select-inline')).to_have_value('saved-a')
            expect(page.locator('#base-roster-name')).to_have_value('A盟未儲存名稱')
            expect(page.locator('#base-save-status')).to_contain_text('未儲存')
            assert page.locator('#base-list [data-player-id]').evaluate_all('(els) => els.map(e => e.dataset.playerId)') == edited

            # Failed durable restore must never be replaced by a generic success announcement.
            page.locator('#saved-rosters').select_option('saved-a')
            page.locator('#delete-roster').click()
            deleted_state = stored(page, 'storageKey')
            fail_writes(page)
            undo(page)
            expect(page.locator('#status')).to_contain_text('復原保存失敗')
            expect(page.locator('#status')).not_to_contain_text('已復原上一個操作')
            assert stored(page, 'storageKey') == deleted_state
            assert page.locator('#saved-rosters option[value="saved-a"]').count() == 0
            restore_writes(page)

            quota_actions = []
            for action in ['delete', 'clear', 'remove']:
                seed(page, ids)
                open_editor(page, 'opponent-editor')
                page.locator('#active-opponent').select_option('opponent-beta')
                if action == 'delete':
                    page.locator('#delete-opponent').click()
                elif action == 'clear':
                    page.locator('#clear-opponent').click()
                else:
                    page.locator('#opponent-list button').first.click()
                deleted_state = stored(page, 'opponentsKey')
                fail_writes(page)
                undo(page)
                expect(page.locator('#status')).to_contain_text('本次畫面已復原，但對手保存失敗')
                expect(page.locator('#status')).not_to_contain_text('已復原上一個操作')
                expect(page.locator('#active-opponent')).to_have_value('opponent-beta')
                assert page.locator('#opponent-list [data-player-id]').count() == 1
                assert stored(page, 'opponentsKey') == deleted_state
                restore_writes(page)
                page.reload()
                assert stored(page, 'opponentsKey') == deleted_state
                quota_actions.append(action)

            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
            assert not errors and not console_errors and not external, (errors, console_errors, external)
            results.append({'width': width, 'sticky_bounds': bounds, 'selected_last_page_removal': True,
                            'target_switch_page_clamp_and_search_consistency': True, 'stale_undo_toast_dismissed': True,
                            'saved_active_id_order_and_unsaved_edits_restored': True, 'saved_undo_quota_truthful': True,
                            'opponent_undo_quota_truthful': quota_actions, 'no_js_csp_errors_or_external_requests': True})
            context.close()
        browser.close()
    (OUTPUT / 'review-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(results, ensure_ascii=False))


if __name__ == '__main__':
    main()
