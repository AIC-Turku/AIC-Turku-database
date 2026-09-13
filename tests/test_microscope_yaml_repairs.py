"""Evidence-backed ledger repairs must survive canonical export without hiding gaps."""
from pathlib import Path
import json
import shutil
import subprocess

import pytest
import yaml

from scripts.light_path_parser import generate_virtual_microscope_payload

ROOT = Path(__file__).resolve().parents[1]


def ledger(name):
    return yaml.safe_load((ROOT / 'instruments' / name).read_text(encoding='utf-8'))


def position(name, stage, mechanism_id, index):
    payload = generate_virtual_microscope_payload(ledger(name))
    mechanisms = payload['projections']['virtual_microscope']['stages'][stage]
    mechanism = next(item for item in mechanisms if item['id'] == mechanism_id)
    return mechanism['options'][index]['value']


def test_native_sensor_sizes_are_not_acquisition_output_sizes():
    nikon = ledger('Nikon Eclipse Ti2-E.yaml')['hardware']['detectors'][0]
    assert nikon['sensor_format_px'] == '2048 x 2048'
    assert 'hamamatsu.com' in nikon['url']
    dp71 = ledger('Olympus BX60.yaml')['hardware']['detectors'][0]
    assert dp71['sensor_format_px'] == '1360 x 1024'
    assert '4080 x 3072' in dp71['notes']
    assert 'pixel-shift' in dp71['notes'].lower()
    assert 'olympus.co.jp' in dp71['url']


@pytest.mark.parametrize('index, cutoff', [(1, 500), (2, 570)])
def test_aurora_longpass_values_reach_runtime_as_executable_ops(index, cutoff):
    pos = position('MSquared Aurora Airy Beam.yaml', 'emission', 'emission_wheel', index)
    assert pos['spectral_ops']['detection'] == [{'op': 'longpass', 'cut_on_nm': float(cutoff)}]
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node.js is required to execute the exported spectral operation')
    script = '''
const rt = require(process.argv[1]);
const component = JSON.parse(process.argv[2]);
const edge = Number(process.argv[3]);
const mask = rt.componentMask(component, [edge - 50, edge + 50], {mode: 'emission'});
if (!(mask[0] < 0.001 && mask[1] > 0.999)) throw new Error(JSON.stringify(mask));
'''
    result = subprocess.run([node, '-e', script,
                             str(ROOT / 'scripts/templates/virtual_microscope_runtime.js'),
                             json.dumps(pos), str(cutoff)],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_nir_dichroic_is_unknown_not_empty_or_unqualified_passthrough():
    pos = position('3i CSU-W1 Spinning Disk.yaml', 'dichroic', 'csu_w1_dichroic_slider', 1)
    assert pos['component_type'] == 'dichroic'
    for phase in ('illumination', 'detection'):
        assert any(op.get('unsupported_reason') for op in pos['spectral_ops'][phase])
    assert not pos.get('cut_on_nm')
    assert not pos.get('transmission_bands')


@pytest.mark.parametrize('index, ex, di, em', [
    (0, (470, 40), 495, (525, 50)),
    (1, (550, 25), 570, (605, 70)),
])
def test_named_zeiss_filter_sets_have_phase_specific_composite_ops(index, ex, di, em):
    pos = position('Zeiss TIRF.yaml', 'cube', 'epi_turret', index)
    assert not pos.get('_cube_incomplete')
    ops = pos['spectral_ops']
    assert [op['op'] for op in ops['illumination']] == ['bandpass', 'dichroic_reflect']
    assert [op['op'] for op in ops['detection']] == ['dichroic_transmit', 'bandpass']
    assert ops['illumination'][0]['center_nm'] == ex[0]
    assert ops['illumination'][0]['width_nm'] == ex[1]
    assert ops['illumination'][1]['cut_on_nm'] == di
    assert ops['detection'][1]['center_nm'] == em[0]
    assert ops['detection'][1]['width_nm'] == em[1]
    assert not any(op.get('unsupported_reason') for phase in ops.values() for op in phase)


@pytest.mark.parametrize('name, mechanism, count', [
    ('3i CSU-W1 Spinning Disk Med C.yaml', 'zeiss_widefield_fluorescence_positions', 3),
    ('Leica Thunder.yaml', 'filter_turret', 2),
    ('xCELLigence RTCA eSight.yaml', 'internal_filter_turret', 3),
])
def test_partial_cube_repairs_preserve_missing_dichroic_diagnostics(name, mechanism, count):
    for index in range(count):
        pos = position(name, 'cube', mechanism, index)
        assert pos.get('_cube_incomplete')
        assert any(op.get('unsupported_reason') for op in pos['spectral_ops']['illumination'])
    source = next(item for item in ledger(name)['hardware']['optical_path_elements']
                  if item['id'] == mechanism)
    for index in range(count):
        cube = source['positions'][f'Pos_{index + 1}']
        assert cube['emission_filter']
        assert 'dichroic' not in cube
        if name != 'Leica Thunder.yaml':
            assert 'excitation_filter' not in cube


def test_remaining_zeiss_multiband_cubes_are_not_falsely_completed():
    for index in (2, 3):
        assert position('Zeiss TIRF.yaml', 'cube', 'epi_turret', index).get('_cube_incomplete')


def test_review_covers_every_real_microscope_and_excludes_fixture_from_slack():
    review = (ROOT / 'docs/microscope_yaml_review_2026-09-13.md').read_text(encoding='utf-8')
    slack = (ROOT / 'docs/slack_microscope_questions_2026-09-13.md').read_text(encoding='utf-8')
    real_count = 0
    for path in (ROOT / 'instruments').rglob('*.yaml'):
        inst = yaml.safe_load(path.read_text(encoding='utf-8'))['instrument']
        assert inst['instrument_id'] in review
        if inst['instrument_id'] == 'scope-testx1':
            assert '*Test Scope X1' not in slack
        else:
            real_count += 1
            assert f"*{inst['display_name']}" in slack
    assert slack.count('```text\n') == real_count == 23
