// Small canonical fixtures exercise the public runtime, not copies of its logic.
const assert = require('node:assert/strict');
const rt = require('../../scripts/templates/virtual_microscope_runtime.js');

function fluor(key, ex, em) {
  return { key, name: key, exMax: ex, emMax: em, spectra: {
    ex1p: [[ex - 20, 0], [ex, 100], [ex + 20, 0]], ex2p: [],
    em: [[em - 20, 0], [em, 100], [em + 20, 0]],
  }};
}
function instrument({ blocked = false, bounded = false } = {}) {
  const positions = Object.fromEntries([[1, 488, 530], [2, 561, 610]].map(([slot, ex, em]) => [slot, {
    slot, position_key: String(slot), display_label: `Cube ${slot}`, component_type: 'filter_cube',
    spectral_ops: { illumination: [{ op: 'bandpass', center_nm: ex, width_nm: 20 }],
      detection: blocked ? [{ op: 'block' }] : [{ op: 'bandpass', center_nm: em, width_nm: 40 }] },
  }]));
  const available_positions = Object.values(positions).map(value => ({
    ...value, label: value.display_label,
  }));
  const sources = [488, 561].map(wavelength_nm => ({
    id: `src_${wavelength_nm}`, display_label: `${wavelength_nm} laser`,
    kind: 'laser', role: 'excitation', wavelength_nm, spectral_mode: 'line',
  }));
  const steps = [
    ...sources.map(source => ({ step_id: source.id, phase: 'illumination', kind: 'source',
      source_id: source.id, component_id: source.id })),
    ...['illumination', 'detection'].map(phase => ({ step_id: `${phase}-cube`, phase,
      kind: 'optical_component', component_id: 'cube', mechanism_id: 'cube',
      stage_role: 'cube', selection_state: 'unresolved', available_positions })),
    { step_id: 'detector', phase: 'detection', kind: 'detector', detector_id: 'cam', endpoint_id: 'cam', component_id: 'cam' },
  ];
  return {
    metadata: { simulation_mode: 'strict' },
    simulation: { default_route: 'epi', wavelength_grid: { min_nm: 430, max_nm: 760, step_nm: 2 } },
    sources,
    optical_path_elements: [{ id: 'cube', stage_role: 'cube', element_type: 'filter_cube_turret', positions }],
    endpoints: [{ id: 'cam', display_label: 'Detector', endpoint_type: bounded ? 'pmt' : 'camera',
      ...(bounded ? { collection_min_nm: 500, collection_max_nm: 650 } : {}) }],
    light_paths: [{ id: 'epi', illumination_sequence: [...sources.map(source => ({ source_id: source.id })), { optical_path_element_id: 'cube' }],
      detection_sequence: [{ optical_path_element_id: 'cube' }, { endpoint_id: 'cam' }],
      route_steps: steps, selected_execution: { contract_version: 'selected_execution.v2', selected_route_steps: steps } }],
  };
}
const green = fluor('green', 488, 530), red = fluor('red', 561, 610), unavailable = fluor('unavailable', 900, 940);
const bounded = rt.optimizeLightPath([green], instrument({ bounded: true }), { currentRoute: 'epi' });
assert.ok(bounded && bounded.score > 0, 'Bounded detectors must not require optical-component spectral_ops');
assert.equal(rt.optimizeLightPath([green], instrument({ blocked: true }), { currentRoute: 'epi' }), null,
  'A dark path must not become a zero-score success');
const sequential = rt.optimizeLightPath([green, red], instrument(), { currentRoute: 'epi' });
assert.ok(sequential && sequential.requiresSequentialAcquisition);
assert.equal(sequential.sequentialPlan.length, 2);
assert.equal(rt.optimizeLightPath([green, red, unavailable], instrument(), { currentRoute: 'epi' }), null,
  'Two working dyes must not be advertised as a complete three-dye plan');
const pass = { spectral_ops: { illumination: [{ op: 'passthrough' }], detection: [{ op: 'passthrough' }] } };
const raw = instrument();
const simulation = rt.simulateInstrument(raw, {
  sources: [raw.sources[0]], detectors: [{ id: 'cam', kind: 'camera' }],
  illuminationComponents: [{ component: pass, mode: 'excitation' }],
  detectionComponents: [{ component: pass, mode: 'emission' }],
  splitters: ['cam', 'other'].map((target, i) => ({ id: `split-${i}`, branches: [{
    id: 'only', mode: 'transmitted', target_ids: [target], component: pass,
  }] })),
}, [green], { currentRoute: 'epi' });
assert.equal(simulation.results.length, 0, 'Disjoint explicit branch targets must terminate the path');
console.log('5 audit runtime regressions passed');
