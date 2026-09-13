"""Browser interaction tests with the production HTML and complete catalogue."""
from pathlib import Path
import shutil

import pytest
from playwright.sync_api import sync_playwright, expect

from test_objective_pool import render

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as p:
        path = shutil.which('chromium') or shutil.which('chromium-browser')
        browser = p.chromium.launch(**({'executable_path':path} if path else {}))
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context()
    page = context.new_page()
    page.set_content(render().replace('<script src="../assets/javascripts/objective_pool.js" defer></script>',''))
    page.add_style_tag(content=(ROOT/'assets/stylesheets/objective_pool.css').read_text())
    page.add_script_tag(content=(ROOT/'assets/javascripts/objective_pool.js').read_text())
    yield page
    context.close()


def test_filters_warnings_reset_and_compact_product_search(page):
    expect(page.locator('.pool-item:visible')).to_have_count(35)
    page.locator('#pool-family').select_option('leica')
    page.locator('#pool-condition').select_option('reported_issue')
    expect(page.locator('.pool-item:visible')).to_have_count(3)
    expect(page.locator('#pool-count')).to_have_text('Showing 3 of 35 records.')
    page.locator('#pool-search').fill('506007')
    expect(page.locator('.pool-item:visible')).to_have_count(1)
    expect(page.locator('.pool-item:visible')).to_contain_text('iris diaphragm stuck')
    page.locator('[data-pool-reset]').first.click()
    page.locator('#pool-search').fill('440350')
    expect(page.locator('.pool-item:visible')).to_have_count(1)
    page.locator('#pool-search').fill('63x water')
    expect(page.locator('.pool-item:visible')).to_have_count(4)
    page.locator('#pool-search').fill('does-not-exist')
    expect(page.locator('#pool-no-results')).to_be_visible()
    page.locator('[data-pool-reset]').last.click()
    expect(page.locator('.pool-item:visible')).to_have_count(35)


def test_ranges_calibration_unknown_and_sort(page):
    page.locator('#pool-kind').select_option('calibration')
    expect(page.locator('.pool-item:visible')).to_have_count(1)
    expect(page.locator('.pool-item:visible')).to_contain_text('Not recorded')
    page.locator('[data-pool-reset]').first.click()
    page.locator('#pool-sort').select_option('mag-desc')
    assert page.locator('.pool-item').first.get_attribute('data-magnification') == '100'
    assert page.locator('.pool-item').last.get_attribute('data-kind') == 'calibration'
    page.locator('#pool-sort').select_option('mag-asc')
    assert page.locator('.pool-item').first.get_attribute('data-magnification') == '1'
    assert page.locator('.pool-item').last.get_attribute('data-kind') == 'calibration'


def test_copy_success_failure_and_permalink(page):
    record = page.locator('#pool-leica-506007')
    record.locator('summary').click()
    page.evaluate("Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async t=>{window.copied=t;}}})")
    record.locator('[data-copy-enquiry]').click()
    expect(record.locator('.pool-feedback')).to_contain_text('Enquiry copied')
    assert 'iris diaphragm stuck' in page.evaluate('window.copied')
    assert 'Microscope: [please enter]' in page.evaluate('window.copied')
    page.evaluate("Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{throw Error('denied')}}})")
    record.locator('[data-copy-enquiry]').click()
    expect(record.locator('.pool-feedback')).to_contain_text('copy it manually')
    page.locator('#pool-search').fill('Nikon')
    page.evaluate("window.location.hash='pool-leica-506007'")
    expect(record).to_be_visible()
    assert record.locator('details').get_attribute('open') is not None
    expect(page.locator('#pool-count')).to_have_text('Showing 35 of 35 records.')


def test_mobile_no_overflow_and_keyboard_labels(page):
    page.set_viewport_size({'width':375,'height':812})
    page.locator('#pool-search').fill('506170')
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    expect(page.get_by_label('Manufacturer / source group')).to_be_visible()
    expect(page.get_by_label('Search objectives')).to_be_visible()
    page.locator('.pool-item:visible summary').focus()
    page.keyboard.press('Enter')
    expect(page.locator('.pool-item:visible textarea')).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')


def test_without_javascript_catalogue_and_enquiries_are_readable(browser):
    context = browser.new_context(java_script_enabled=False)
    page = context.new_page()
    page.set_content(render())
    expect(page.locator('.pool-item')).to_have_count(35)
    expect(page.locator('#pool-controls')).to_be_hidden()
    page.locator('#pool-incucyte-4628 summary').click()
    expect(page.locator('#pool-incucyte-4628 textarea')).to_be_visible()
    expect(page.locator('#pool-incucyte-4628')).to_contain_text('LENSES TOTALLY RUINED!')
    context.close()
