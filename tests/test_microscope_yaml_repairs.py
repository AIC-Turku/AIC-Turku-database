"""Evidence-backed ledger repairs must survive canonical export without hiding gaps."""
from pathlib import Path
import json
import shutil
import subprocess

import pytest
import yaml

from scripts.lightpath.vm_payload import generate_virtual_microscope_payload

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
    assert dp71['sensor_format_px'] == '1.45 MP'
    assert 'physical array dimensions are not confirmed' in dp71['notes']
    assert '1360 x 1024' in dp71['notes']
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
    assert pos['model'] == 'T750SPXR-XT-UF1'
    assert pos['manufacturer'] == 'Chroma'
    for phase in ('illumination', 'detection'):
        assert any(op.get('unsupported_reason') for op in pos['spectral_ops'][phase])
    assert not pos.get('cut_on_nm')
    assert not pos.get('transmission_bands')
    assert not pos.get('bands')


def test_3i_visible_dichroic_identity_is_recorded_without_inverting_reflection_bands():
    pos = position('3i CSU-W1 Spinning Disk.yaml', 'dichroic', 'csu_w1_dichroic_slider', 0)
    assert pos['component_type'] == 'multiband_dichroic'
    assert pos['product_code'] == 'Di01-T405/488/568/647'
    assert pos['manufacturer'] == 'Semrock'
    # The broad 422-473 / 503-545 / 586-620 / 665-750 windows are reflection
    # bands for this laser-optimized optic. The current canonical direct-position
    # schema cannot represent their orientation separately, so they must not be
    # exported as generic transmission bands.
    assert not pos.get('bands')
    for phase in ('illumination', 'detection'):
        assert any(op.get('unsupported_reason') for op in pos['spectral_ops'][phase])


def test_3i_nir_beam_combiner_is_source_specific_inventory_not_a_shared_route_step():
    record = ledger('3i CSU-W1 Spinning Disk.yaml')
    elements = {row['id']: row for row in record['hardware']['optical_path_elements']}
    combiner = elements['csu_w1_nir_beam_combiner']
    assert combiner['element_type'] == 'fixed'
    assert combiner['positions']['Pos_1']['model'] == 'DM A660LP Beam Combiner'
    assert not any(
        step.get('optical_path_element_id') == 'csu_w1_nir_beam_combiner'
        for step in next(
            route for route in record['light_paths']
            if route['id'] == 'confocal_spinning_disk'
        )['illumination_sequence']
    )
    source = next(
        row for row in record['hardware']['sources']
        if row['id'] == 'singleline_730nm_laser_launch'
    )
    assert 'DM A660LP' in source['notes']


def test_3i_all_five_confocal_laser_sources_remain_on_the_recorded_route():
    record = ledger('3i CSU-W1 Spinning Disk.yaml')
    route = next(route for route in record['light_paths'] if route['id'] == 'confocal_spinning_disk')
    source_ids = [step['source_id'] for step in route['illumination_sequence'] if 'source_id' in step]
    assert source_ids == [
        'laserstack_v4',
        'laserstack_v4_2',
        'laserstack_v4_3',
        'laserstack_v4_4',
        'singleline_730nm_laser_launch',
    ]
    sources = {row['id']: row for row in record['hardware']['sources']}
    assert [sources[source_id]['wavelength_nm'] for source_id in source_ids] == [405, 488, 561, 640, 730]


def test_3i_confocal_camera_branches_use_separate_emission_wheels():
    record = ledger('3i CSU-W1 Spinning Disk.yaml')
    route = next(route for route in record['light_paths'] if route['id'] == 'confocal_spinning_disk')
    branch_block = next(step['branches'] for step in route['detection_sequence'] if 'branches' in step)
    assert branch_block['selection_mode'] == 'exclusive'
    branches = {branch['branch_id']: branch['sequence'] for branch in branch_block['items']}
    assert branches['to_camera_1'] == [
        {'optical_path_element_id': 'csu_w1_emission_wheel'},
        {'endpoint_id': 'detector_1'},
    ]
    assert branches['to_camera_2'] == [
        {'optical_path_element_id': 'csu_w1_emission_wheel_2'},
        {'endpoint_id': 'detector_2'},
    ]


def test_3i_emission_filters_match_confirmed_slidebook_and_filter_data():
    record = ledger('3i CSU-W1 Spinning Disk.yaml')
    elements = {row['id']: row for row in record['hardware']['optical_path_elements']}
    wheel1 = elements['csu_w1_emission_wheel']['positions']
    wheel2 = elements['csu_w1_emission_wheel_2']['positions']

    assert [(band['center_nm'], band['width_nm']) for band in wheel1['Pos_1']['bands']] == [
        (440, 40), (521, 21), (607, 34), (700, 45),
    ]
    assert wheel1['Pos_3']['bands'] == [{'center_nm': 525, 'width_nm': 50}]
    assert wheel1['Pos_6']['product_code'] == 'FF02-809/81-25'
    assert wheel1['Pos_6']['bands'] == [{'center_nm': 809, 'width_nm': 81}]
    assert set(wheel2) == {'Pos_6'}
    assert wheel2['Pos_6']['product_code'] == 'FF02-809/81-25'
    assert wheel2['Pos_6']['bands'] == [{'center_nm': 809, 'width_nm': 81}]


def test_3i_widefield_semrock_spectra_are_not_reused_from_the_old_25_nm_placeholders():
    record = ledger('3i CSU-W1 Spinning Disk.yaml')
    elements = {row['id']: row for row in record['hardware']['optical_path_elements']}
    dichroic = elements['widefield_dichroic']['positions']['Pos_1']
    emitter = elements['widefield_emission']['positions']['Pos_1']
    assert [(b['center_nm'], b['width_nm']) for b in dichroic['bands']] == [
        (440, 40), (520.5, 21), (606.5, 34), (699.5, 45),
    ]
    assert [(b['center_nm'], b['width_nm']) for b in emitter['bands']] == [
        (440, 40), (521, 21), (607, 34), (700, 45),
    ]


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
