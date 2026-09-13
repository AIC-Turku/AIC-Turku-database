"""Exercise the built MkDocs site, not just the template or a mocked navigation."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
import shutil
import subprocess
import threading

import pytest
from playwright.sync_api import expect
from test_objective_pool_browser import browser

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which('mkdocs') is None, reason='MkDocs build dependencies are required for generated-site acceptance')
def test_generated_site_catalogue_round_trip_and_export_boundaries(browser, tmp_path):
    subprocess.run(['python', '-m', 'scripts.dashboard_builder', '--strict'], cwd=ROOT, check=True, capture_output=True)
    site = tmp_path/'site'
    subprocess.run(['mkdocs', 'build', '--strict', '--site-dir', str(site)], cwd=ROOT, check=True, capture_output=True)
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(site)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f'http://127.0.0.1:{server.server_port}'
    context = browser.new_context(viewport={'width':1440, 'height':1100})
    context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(origin + '/') else route.abort())
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    try:
        page.goto(origin + '/')
        page.get_by_role('link', name='Browse the objective catalogue', exact=True).click()
        expect(page.get_by_role('heading', name='Objectives', exact=True)).to_be_visible()
        expect(page.locator('.pool-item:visible')).to_have_count(135)
        assert page.locator('.pool-item').count() == 137
        data = context.request.get(origin+'/assets/objectives.json').json()
        assert data['current_count'] == 135 and data['historical_count'] == 2
        pool = context.request.get(origin+'/assets/objective_pool.json').json()
        assert pool['inventory_kind'] == 'objective_pool' and len(pool['items']) == 35
        methods = context.request.get(origin+'/assets/instruments_data.json').json()
        assert all(not obj.get('id','').startswith('pool-') for inst in methods['instruments']
                   for obj in inst.get('hardware',{}).get('objectives',[]))
        # Test the actual generated paths in both directions, including an objective anchor.
        page.get_by_label('Microscope', exact=True).select_option('scope-olympus-bx60')
        expect(page.locator('.pool-item:visible')).to_have_count(6)
        page.locator('.pool-item:visible').first.get_by_role('link', name='View microscope', exact=True).click()
        expect(page.locator('#objectives')).to_be_visible()
        assert page.locator('#objectives').count() == 1
        page.get_by_role('link', name="View this microscope's objectives in the catalogue", exact=True).click()
        expect(page.locator('.pool-item:visible')).to_have_count(6)
        expect(page.get_by_label('Microscope', exact=True)).to_have_value('scope-olympus-bx60')
        page.get_by_label('Installation status').select_option('not_installed')
        expect(page.locator('.pool-item:visible')).to_have_count(1)
        expect(page.locator('.pool-item:visible')).to_contain_text('Optional objective')
        page.get_by_label('Catalogue view').select_option('spare_pool')
        expect(page.locator('.pool-item:visible')).to_have_count(35)
        page.goto(origin+'/objective_pool/?instrument=scope-leica-tcs-sp5-multiphoton')
        expect(page.locator('.pool-item:visible')).to_have_count(2)
        expect(page.get_by_label('Include historical / retired microscope records')).to_be_checked()
        page.goto(origin+'/objective_pool/?view=instrument#pool-leica-506007')
        expect(page.locator('#pool-leica-506007')).to_be_visible()
        expect(page.locator('#pool-leica-506007 textarea')).to_be_visible()
        page.locator('[data-pool-reset]').first.click()
        proof = Path(os.environ.get('AIC_OBJECTIVE_PROOF_DIR', str(tmp_path/'proof')))
        proof.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(proof/'unified-objectives-desktop.png'))
        page.set_viewport_size({'width':375, 'height':812})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.get_by_label('Catalogue view').select_option('spare_pool')
        page.screenshot(path=str(proof/'unified-objectives-mobile.png'))
        assert errors == []
    finally:
        context.close()
        server.shutdown()
        thread.join()
        server.server_close()
