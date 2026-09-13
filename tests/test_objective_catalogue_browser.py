"""Production catalogue HTML/JS, including optional/unknown and historical records."""
from pathlib import Path
from urllib.parse import urlsplit
import json

import pytest
from playwright.sync_api import expect
from test_objective_pool_browser import browser
from test_objective_catalogue import catalogue, render_catalogue, fixture, fixture_view

ROOT = Path(__file__).resolve().parents[1]


def mount(page, view=None, url='http://127.0.0.1:8123/objective_pool/'):
    html = render_catalogue(view).replace('<script src="../assets/javascripts/objective_pool.js" defer></script>', '')
    # Keep navigation offline. Only the query-string boundary is stubbed; production
    # DOM, controls, hash events and the application source execute unchanged.
    page.set_content(html)
    page.add_style_tag(content=(ROOT/'assets/stylesheets/objective_pool.css').read_text())
    source = (ROOT/'assets/javascripts/objective_pool.js').read_text()
    search = '?' + urlsplit(url).query if urlsplit(url).query else ''
    window_proxy = ('{location: {get search(){return ' + json.dumps(search) + ';}, '
                    'get hash(){return globalThis.location.hash;}}, '
                    'addEventListener: globalThis.addEventListener.bind(globalThis)}')
    page.add_script_tag(content='(function(window){' + source + '})(' + window_proxy + ');')


@pytest.fixture
def page(browser):
    context = browser.new_context()
    page = context.new_page()
    mount(page)
    yield page
    context.close()


def test_all_microscope_spare_optional_and_history_filters(page):
    expect(page.locator('.pool-item:visible')).to_have_count(135)
    page.get_by_label('Catalogue view').select_option('instrument')
    expect(page.locator('.pool-item:visible')).to_have_count(100)
    page.get_by_label('Installation status').select_option('installed')
    expect(page.locator('.pool-item:visible')).to_have_count(90)
    page.get_by_label('Installation status').select_option('not_installed')
    expect(page.locator('.pool-item:visible')).to_have_count(10)
    page.get_by_label('Microscope', exact=True).select_option('scope-olympus-bx60')
    expect(page.locator('.pool-item:visible')).to_have_count(1)
    expect(page.locator('.pool-item:visible')).to_contain_text('Optional objective')
    page.get_by_label('Catalogue view').select_option('spare_pool')
    expect(page.locator('.pool-item:visible')).to_have_count(35)
    expect(page.get_by_label('Installation status')).to_be_disabled()
    expect(page.get_by_label('Microscope', exact=True)).to_be_disabled()
    page.locator('[data-pool-reset]').first.click()
    page.get_by_label('Include historical / retired microscope records').check()
    expect(page.locator('.pool-item:visible')).to_have_count(137)


def test_deep_links_reveal_instrument_or_historical_record(browser):
    context = browser.new_context()
    page = context.new_page()
    mount(page, url='http://127.0.0.1:8123/objective_pool/?instrument=scope-3i-csu-w1-spinning-disk')
    expect(page.locator('.pool-item:visible')).to_have_count(7)
    expect(page.get_by_label('Catalogue view')).to_have_value('instrument')
    expect(page.locator('.pool-item:visible [data-copy-enquiry]')).to_have_count(0)
    retired_id = next(row['id'] for row in catalogue()['items'] if row['retired'])
    page.evaluate('(id) => window.location.hash = id', retired_id)
    expect(page.locator('[data-retired="true"].pool-item:visible')).to_have_count(2)
    expect(page.get_by_label('Include historical / retired microscope records')).to_be_checked()
    expect(page.locator('[id="'+retired_id+'"] details')).to_have_attribute('open','')
    context.close()


def test_retired_microscope_query_and_unknown_link(browser):
    context = browser.new_context()
    page = context.new_page()
    mount(page, url='http://127.0.0.1:8123/objective_pool/?instrument=scope-leica-tcs-sp5-multiphoton')
    expect(page.locator('.pool-item:visible')).to_have_count(2)
    expect(page.get_by_label('Include historical / retired microscope records')).to_be_checked()
    page2 = context.new_page()
    mount(page2, url='http://127.0.0.1:8123/objective_pool/?instrument=scope-testx1')
    expect(page2.locator('#pool-link-feedback')).to_contain_text('not in this catalogue')
    expect(page2.locator('.pool-item:visible')).to_have_count(135)
    context.close()


def test_unconfirmed_not_spare_and_missing_units_are_visible(browser):
    context = browser.new_context()
    page = context.new_page()
    mount(page, fixture_view(fixture()))
    page.get_by_label('Installation status').select_option('unconfirmed')
    expect(page.locator('.pool-item:visible')).to_have_count(1)
    expect(page.locator('.pool-item:visible')).to_contain_text('Installation unconfirmed')
    expect(page.locator('.pool-item:visible')).to_contain_text('0.62 mm')
    assert page.locator('.pool-item:visible').get_attribute('data-source_kind') == 'instrument'
    context.close()


def test_old_pool_permalink_and_mobile_view(page):
    page.set_viewport_size({'width':375,'height':812})
    page.get_by_label('Catalogue view').select_option('instrument')
    page.evaluate("window.location.hash='pool-leica-506007'")
    expect(page.locator('#pool-leica-506007')).to_be_visible()
    expect(page.locator('#pool-leica-506007 textarea')).to_contain_text('iris diaphragm stuck')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.get_by_label('Search objectives').fill('63x water')
    assert page.locator('.pool-item:visible').count() > 0


def test_no_javascript_includes_labelled_history_and_microscope_links(browser):
    context = browser.new_context(java_script_enabled=False)
    page = context.new_page()
    page.set_content(render_catalogue())
    expect(page.locator('.pool-item')).to_have_count(137)
    expect(page.locator('[data-retired="true"].pool-item').first).to_contain_text('Historical record')
    expect(page.locator('[data-source_kind="instrument"] a').first).to_have_attribute('href', '../instruments/scope-3i-csu-w1-spinning-disk/#objectives')
    expect(page.locator('#pool-controls')).to_be_hidden()
    context.close()


def test_record_permalink_handles_reserved_characters_in_source_id(browser):
    context = browser.new_context()
    page = context.new_page()
    view = fixture_view(fixture(True, identifier='40x/water % test'))
    row = view['items'][0]
    mount(page, view)
    card = page.locator('[id="'+row['id']+'"]')
    card.locator('summary').click()
    link = card.get_by_role('link', name='Link to this record', exact=True)
    expect(link).to_have_attribute('href', '#'+row['anchor'])
    card.locator('summary').click()
    page.get_by_label('Catalogue view').select_option('spare_pool')
    page.evaluate('(hash) => window.location.hash = hash', row['anchor'])
    expect(card).to_be_visible()
    expect(card.locator('details')).to_have_attribute('open', '')
    context.close()
