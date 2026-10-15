"""Real-data checks for navigation, picker feedback and recoverable roster actions."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ORIGIN = (sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8775').rstrip('/')
OUTPUT = Path(sys.argv[2] if len(sys.argv) > 2 else '/tmp/site-ux-browser')
OUTPUT.mkdir(parents=True, exist_ok=True)


def no_overflow(page):
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')


def open_editor(page, name):
    editor = page.locator('#' + name)
    if not editor.evaluate('(e) => e.open'):
        editor.locator('summary').click()


def base_state(page):
    return {
        'players': page.locator('#base-list [data-player-id]').evaluate_all('(els) => els.map(e => e.dataset.playerId)'),
        'name': page.locator('#base-roster-name').input_value(),
        'active': page.locator('#base-roster-select').input_value(),
        'outgoing': page.locator('[data-outgoing]:checked').evaluate_all('(els) => els.map(e => e.dataset.outgoing)'),
        'incoming': page.locator('#incoming-list [data-player-id]').evaluate_all('(els) => els.map(e => e.dataset.playerId)'),
    }


def undo(page):
    control = page.locator('#status button[data-undo]')
    expect(control).to_be_visible()
    control.click()


def pick(page, pid, checked=True):
    name = page.evaluate('(id) => ROTO_DATA.players[id].name', pid)
    page.locator('#player-search').fill(name)
    box = page.locator('#roto-player-table tbody input[data-roto-pick="' + pid + '"]')
    box.set_checked(checked)


def main():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'), args=['--no-sandbox'])
        for width, height in [(1500, 1000), (390, 844), (360, 800), (320, 740)]:
            print(f'Checking {width}px', flush=True)
            errors, console_errors, external = [], [], []
            context = browser.new_context(viewport={'width': width, 'height': height}, is_mobile=width < 600, has_touch=width < 600, reduced_motion='reduce')
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda message: console_errors.append(message.text) if message.type == 'error' else None)
            page.on('request', lambda request: external.append(request.url) if not request.url.startswith(ORIGIN + '/') and not request.url.startswith('data:') else None)

            assert page.goto(ORIGIN + '/', wait_until='load').status == 200
            no_overflow(page)
            expect(page.locator('.site-nav a[aria-current="page"]')).to_have_text('球員與賽程')
            expect(page.locator('.site-nav a[href="roto.html"]')).to_be_visible()
            page.locator('#jump-players').click()
            active_heading = page.locator('.tabcontent:visible .player-section h3').first
            expect(active_heading).to_be_focused()
            # The comparison entry remains reachable while selecting deep in the table.
            first = page.locator('.tabcontent:visible input[data-pick="compare"]').nth(5)
            first.check()
            expect(page.locator('#view-comparison')).to_be_visible()
            assert '1' in page.locator('#view-comparison').inner_text()
            page.locator('#view-comparison').click()
            expect(page.locator('#comparison-panel')).to_be_visible()
            no_overflow(page)
            if width in (1500, 390):
                page.screenshot(path=str(OUTPUT / f'home-comparison-{width}.png'))
            page.locator('.site-nav a[href="roto.html"]').click()
            expect(page).to_have_url(ORIGIN + '/roto.html')
            page.wait_for_load_state('load')
            expect(page.locator('#search-count')).to_contain_text('正在編輯')
            expect(page.locator('.site-nav a[aria-current="page"]')).to_have_text('九項配隊')
            expect(page.locator('#roster-start')).to_be_visible()
            no_overflow(page)
            if width in (1500, 390):
                page.screenshot(path=str(OUTPUT / f'roto-start-{width}.png'))

            # Empty-state action gives an unambiguous selection target and keyboard focus.
            page.locator('#roster-start [data-pick-target="base"]').click()
            expect(page.locator('#add-target')).to_have_value('base')
            expect(page.locator('#player-search')).to_be_focused()
            assert page.locator('#player-search').bounding_box()['y'] >= 0
            pick(page, '1966')
            pick(page, '3195')
            expect(page.locator('#base-count')).to_have_text('2 人')
            expect(page.locator('#picker-feedback')).to_contain_text('已勾選')
            page.locator('#clear-search').click()
            expect(page.locator('#player-search')).to_have_value('')
            page.locator('#selected-only').click()
            expect(page.locator('#selected-only')).to_have_attribute('aria-pressed', 'true')
            assert page.locator('#roto-player-table tbody input[data-roto-pick]').count() == 2
            page.locator('#roto-player-table tbody input[data-roto-pick="3195"]').click()
            expect(page.locator('#picker-feedback')).to_contain_text('已解除')
            assert page.locator('#roto-player-table tbody input[data-roto-pick]').count() == 1
            page.locator('#selected-only').click()
            pick(page, '3195')
            page.locator('#player-search').fill('no-player-will-match-zzzz')
            assert page.locator('#roto-player-table tbody input[data-roto-pick]').count() == 0
            page.locator('#clear-search').click()
            assert page.locator('#roto-player-table tbody input[data-roto-pick]').count() > 2
            no_overflow(page)
            if width in (1500, 390):
                page.screenshot(path=str(OUTPUT / f'roto-picker-{width}.png'))

            # Every work-area navigation entry lands with an accessible focus destination.
            for target in ['roster-editors', 'comparison-overview', 'saved-panel', 'player-picker']:
                page.locator('[data-jump="' + target + '"]').click()
                destination = page.locator('#' + target)
                expect(destination).to_be_focused()
                bounds = destination.bounding_box()
                assert 0 <= bounds['y'] < height, (target, bounds)
            open_editor(page, 'base-editor')
            page.locator('#base-roster-name').fill('A盟')
            page.locator('#save-base-roster').click()
            a = page.locator('#base-roster-select').input_value()
            page.locator('#base-roster-name').fill('B盟')
            page.locator('#save-base-roster').click()
            b = page.locator('#base-roster-select').input_value()
            assert a and b and a != b
            saved_before = page.evaluate('JSON.parse(localStorage.getItem(RotoCore.storageKey))')
            page.locator('#base-roster-select-inline').select_option(a)
            # Unsaved name, roster and simulation are all recoverable after switching.
            page.locator('#base-list button').first.click()
            page.locator('#base-roster-name').fill('A盟未儲存的名稱')
            open_editor(page, 'simulation-editor')
            page.locator('#simulation-editor [data-pick-target="incoming"]').click()
            expect(page.locator('#add-target')).to_have_value('incoming')
            pick(page, '3195', False)
            extra = page.evaluate('Object.values(ROTO_DATA.players).find(p => !["1966","3195"].includes(p.id)).id')
            pick(page, extra)
            dirty = base_state(page)
            assert dirty['outgoing'] == ['3195'] and dirty['incoming'] == [extra]
            page.locator('#base-roster-select').select_option(b)
            assert page.locator('#base-roster-name').input_value() == 'B盟'
            undo(page)
            assert base_state(page) == dirty
            assert page.evaluate('JSON.parse(localStorage.getItem(RotoCore.storageKey))') == saved_before
            expect(page.locator('#base-roster-select-inline')).to_have_value(a)
            open_editor(page, 'base-editor')
            page.locator('#new-base-roster').click()
            expect(page.locator('#base-count')).to_have_text('0 人')
            undo(page)
            assert base_state(page) == dirty
            page.locator('#clear-base').click()
            expect(page.locator('#base-count')).to_have_text('0 人')
            undo(page)
            assert base_state(page) == dirty

            # Named opponents still auto-save; deleting one can be undone without losing members.
            open_editor(page, 'opponent-editor')
            page.locator('#add-opponent').click()
            page.locator('#opponent-name').fill('可復原對手')
            page.locator('#opponent-name').press('Tab')
            page.locator('#opponent-editor [data-pick-target="opponent"]').click()
            expect(page.locator('#add-target')).to_have_value('opponent')
            pick(page, '1966')
            opponent_id = page.locator('#active-opponent').input_value()
            page.locator('#delete-opponent').click()
            assert page.locator('#active-opponent option[value="' + opponent_id + '"]').count() == 0
            undo(page)
            expect(page.locator('#active-opponent')).to_have_value(opponent_id)
            assert page.locator('#opponent-list [data-player-id="1966"]').count() == 1
            assert any(t['id'] == opponent_id and t['players'] == ['1966'] for t in page.evaluate('JSON.parse(localStorage.getItem(RotoCore.opponentsKey)).rosters'))

            # Library deletion is also reversible and leaves unrelated saves intact.
            page.locator('#saved-rosters').select_option(b)
            page.locator('#delete-roster').click()
            assert page.locator('#saved-rosters option[value="' + b + '"]').count() == 0
            undo(page)
            assert page.locator('#saved-rosters option[value="' + b + '"]').count() == 1
            assert page.evaluate('JSON.parse(localStorage.getItem(RotoCore.storageKey))') == saved_before
            no_overflow(page)
            assert not errors and not console_errors and not external, (errors, console_errors, external)
            results.append({'width': width, 'no_document_overflow': True, 'home_navigation_and_comparison_entry': True,
                'empty_state_and_target_actions': True, 'section_focus_navigation': True, 'selected_only_uncheck_and_clear_search': True,
                'picker_feedback': True, 'unsaved_name_roster_and_simulation_undo': True,
                'new_and_clear_base_undo': True, 'opponent_delete_undo': True, 'saved_roster_delete_undo': True,
                'no_js_csp_errors_or_external_requests': True})
            context.close()
        browser.close()
    (OUTPUT / 'site-ux-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(results, ensure_ascii=False))


if __name__ == '__main__':
    main()
