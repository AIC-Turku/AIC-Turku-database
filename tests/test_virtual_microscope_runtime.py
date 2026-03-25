import json
import shutil
import subprocess
import textwrap
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import yaml

from scripts.light_path_parser import generate_virtual_microscope_payload

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = REPO_ROOT / "scripts" / "templates" / "virtual_microscope_runtime.js"
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"


class VirtualMicroscopeRuntimeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("node") is None:
            raise unittest.SkipTest("Node.js is required for virtual microscope runtime tests.")
        if not RUNTIME_PATH.exists():
            raise unittest.SkipTest("Virtual microscope runtime script is missing.")

    def run_node_json(self, body: str) -> object:
        return self.run_node_script_json(
            f"""
            const rt = require('./scripts/templates/virtual_microscope_runtime.js');
            const result = (() => {{
            {body}
            }})();
            console.log(JSON.stringify(result));
            """
        )

    def run_node_script_json(self, script: str) -> object:
        proc = subprocess.run(
            ["node", "-"],
            cwd=REPO_ROOT,
            input=textwrap.dedent(script),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise AssertionError(f"Node runtime failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        return json.loads(proc.stdout)

    def parser_payload_for_instrument(self, instrument_name: str) -> dict:
        instrument = yaml.safe_load((REPO_ROOT / "instruments" / instrument_name).read_text(encoding="utf-8"))
        return generate_virtual_microscope_payload(instrument)

    @staticmethod
    def _find_stage_option_value(stage_rows: list[dict], target_label: str) -> dict | None:
        for mechanism in stage_rows:
            for option in mechanism.get("options") or []:
                option_label = option.get("display_label") or ""
                value = option.get("value") if isinstance(option.get("value"), dict) else {}
                value_label = value.get("display_label") or value.get("label") or value.get("name") or ""
                slot = option.get("slot")
                candidate_labels = {
                    option_label,
                    value_label,
                    f"Slot {slot}: {option_label}" if slot is not None and option_label else "",
                    f"Slot {slot}: {value_label}" if slot is not None and value_label else "",
                }
                if target_label in candidate_labels:
                    return value
        return None

    def normalized_stage_option_value(self, payload: dict, stage_role: str, target_label: str) -> dict | None:
        return self.run_node_script_json(
            f"""
            const rt = require('./scripts/templates/virtual_microscope_runtime.js');
            const payload = {json.dumps(payload)};
            const instrument = rt.normalizeInstrumentPayload(payload);
            const stageRows = instrument[{json.dumps(stage_role)}] || [];
            const targetLabel = {json.dumps(target_label)};
            function findOptionValue(rows, label) {{
              for (const mechanism of rows) {{
                for (const option of mechanism.options || []) {{
                  const optionLabel = option.display_label || '';
                  const value = option && option.value && typeof option.value === 'object' ? option.value : null;
                  const valueLabel = value ? (value.display_label || value.label || value.name || '') : '';
                  const slot = option.slot;
                  const candidateLabels = new Set([
                    optionLabel,
                    valueLabel,
                    slot !== undefined && optionLabel ? `Slot ${{slot}}: ${{optionLabel}}` : '',
                    slot !== undefined && valueLabel ? `Slot ${{slot}}: ${{valueLabel}}` : '',
                  ]);
                  if (candidateLabels.has(label)) {{
                    return value;
                  }}
                }}
              }}
              return null;
            }}
            console.log(JSON.stringify(findOptionValue(stageRows, targetLabel)));
            """
        )

    def test_fpbase_search_results_are_normalized(self) -> None:
        result = self.run_node_json(
            """
            return rt.normalizeFPbaseSearchResults({
              results: [{
                uuid: 'ZERB6',
                slug: 'mcherry',
                name: 'mCherry',
                states: [{ ex_max: 587, em_max: 610, brightness: 15.84, ext_coeff: 72000, qy: 0.22 }]
              }]
            });
            """
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["key"], "ZERB6")
        self.assertEqual(result[0]["name"], "mCherry")
        self.assertEqual(result[0]["exMax"], 587)
        self.assertEqual(result[0]["emMax"], 610)
        self.assertEqual(result[0]["brightness"], 15.84)
        self.assertEqual(result[0]["ec"], 72000)
        self.assertEqual(result[0]["qy"], 0.22)

    def test_fluorophore_detail_normalization_preserves_states_and_spectra(self) -> None:
        result = self.run_node_json(
            """
            const detail = {
              name: 'mEos',
              states: [
                {
                  name: 'green',
                  is_default: true,
                  ex_max: 506,
                  em_max: 519,
                  spectra: [
                    { spectrum_type: 'excitation', data: [[470, 0], [506, 100], [540, 0]] },
                    { spectrum_type: 'emission', data: [[490, 0], [519, 100], [560, 0]] }
                  ]
                },
                {
                  name: 'red',
                  ex_max: 573,
                  em_max: 584,
                  spectra: [
                    { spectrum_type: 'excitation', data: [[540, 0], [573, 100], [600, 0]] },
                    { spectrum_type: 'emission', data: [[560, 0], [584, 100], [620, 0]] }
                  ]
                }
              ]
            };
            return rt.normalizeFluorophoreDetail(detail, { key: 'meos', name: 'mEos' });
            """
        )

        self.assertEqual(result["name"], "mEos")
        self.assertEqual(result["activeStateName"], "green")
        self.assertEqual(len(result["states"]), 2)
        self.assertEqual(result["states"][1]["name"], "red")
        self.assertEqual(result["exMax"], 506)
        self.assertEqual(result["emMax"], 519)
        self.assertGreater(len(result["spectra"]["ex1p"]), 0)
        self.assertGreater(len(result["spectra"]["em"]), 0)

    def test_spectrascope_short_spectrum_tokens_are_normalized(self) -> None:
        result = self.run_node_json(
            """
            const detail = {
              id: 'af488',
              name: 'AF488',
              exMax: 490,
              emMax: 525,
              spectra: [
                { spectrum_type: 'ex', data: [[450, 0.1], [490, 1.0], [530, 0.0]] },
                { spectrum_type: 'em', data: [[500, 0.0], [525, 1.0], [560, 0.2]] }
              ]
            };
            return rt.normalizeFluorophoreDetail(detail, { key: 'af488', name: 'AF488', sourceOrigin: 'local' });
            """
        )

        self.assertEqual(result["name"], "AF488")
        self.assertEqual(result["spectraSource"], "local")
        self.assertGreater(len(result["spectra"]["ex1p"]), 0)
        self.assertGreater(len(result["spectra"]["em"]), 0)

    def test_fpbase_spectra_response_handles_short_tokens(self) -> None:
        result = self.run_node_json(
            """
            return rt.normalizeFPbaseSpectraResponse({
              results: [
                { protein_name: 'AF488', spectrum_type: 'ex', data: [[450, 0.1], [490, 1.0], [530, 0.0]] },
                { protein_name: 'AF488', spectrum_type: 'em', data: [[500, 0.0], [525, 1.0], [560, 0.2]] }
              ]
            });
            """
        )

        self.assertEqual([row["type"] for row in result], ["ex1p", "em"])
        self.assertTrue(all(len(row["points"]) > 0 for row in result))

    def test_source_spectrum_parses_multi_line_descriptors(self) -> None:
        """sourceCenters only uses explicit wavelength fields — never
        display_label, name, model, product_code or notes.  Multi-value
        strings in wavelength_nm are still parsed because that field is
        wavelength-semantic by definition."""
        result = self.run_node_json(
            """
            const grid = rt.wavelengthGrid({ min_nm: 380, max_nm: 760, step_nm: 2 });
            const spectrum = rt.sourceSpectrum({
              wavelength_nm: '395; 440; 475; 555; 640',
              spectral_mode: 'line'
            }, grid);
            function localPeak(target) {
              return Math.max(...grid.map((wavelength, index) => Math.abs(wavelength - target) <= 2 ? (spectrum[index] || 0) : 0));
            }
            return {
              peaks: [395, 440, 475, 555, 640].map((target) => ({
                target,
                value: localPeak(target),
              })),
              centersFromWavelengthField: rt.sourceCenters({ wavelength_nm: '395; 440; 475; 555; 640' }),
              centersFromDisplayLabel: rt.sourceCenters({ display_label: '395/25; 440/20; 475/28; 555/15; 640/30' })
            };
            """
        )

        self.assertEqual(result["centersFromWavelengthField"], [395, 440, 475, 555, 640])
        # display_label is no longer parsed for wavelengths.
        self.assertEqual(result["centersFromDisplayLabel"], [])
        bright_peaks = [entry for entry in result["peaks"] if entry["value"] >= 0.49]
        self.assertEqual(len(bright_peaks), 5)

    def test_mcherry_recorded_fpbase_bundle_normalizes_to_usable_spectra(self) -> None:
        fixture = json.loads((FIXTURE_DIR / "fpbase_mcherry_bundle.json").read_text())
        result = self.run_node_json(
            f"""
            const fixture = {json.dumps(json.loads((FIXTURE_DIR / 'fpbase_mcherry_bundle.json').read_text()))};
            const summary = rt.normalizeFPbaseSearchResults(fixture.search)[0];
            const fluor = rt.normalizeFluorophoreDetail(fixture.detail, summary, fixture.spectra);
            return {{
              name: fluor.name,
              exMax: fluor.exMax,
              emMax: fluor.emMax,
              spectraSource: fluor.spectraSource,
              exPoints: fluor.spectra.ex1p.length,
              emPoints: fluor.spectra.em.length,
              exPeak: Math.max(...fluor.spectra.ex1p.map((point) => point.y)),
              emPeak: Math.max(...fluor.spectra.em.map((point) => point.y))
            }};
            """
        )

        self.assertEqual(result["name"], "mCherry")
        self.assertEqual(result["exMax"], 587)
        self.assertEqual(result["emMax"], 610)
        self.assertEqual(result["spectraSource"], "api")
        self.assertGreater(result["exPoints"], 5)
        self.assertGreater(result["emPoints"], 5)
        self.assertGreater(result["exPeak"], 90)
        self.assertGreater(result["emPeak"], 90)

    def test_missing_fpbase_spectra_are_synthesized_from_maxima(self) -> None:
        result = self.run_node_json(
            """
            const fluor = rt.normalizeFluorophoreDetail(
              { name: 'SyntheticOnly', states: [{ name: 'default', is_default: true, ex_max: 500, em_max: 525 }] },
              { key: 'synthetic', name: 'SyntheticOnly', exMax: 500, emMax: 525 },
              null
            );
            return {
              spectraSource: fluor.spectraSource,
              exPoints: fluor.spectra.ex1p.length,
              emPoints: fluor.spectra.em.length,
              exPeak: Math.max(...fluor.spectra.ex1p.map((point) => point.y)),
              emPeak: Math.max(...fluor.spectra.em.map((point) => point.y))
            };
            """
        )

        self.assertEqual(result["spectraSource"], "synthetic")
        self.assertGreater(result["exPoints"], 10)
        self.assertGreater(result["emPoints"], 10)
        self.assertGreater(result["exPeak"], 90)
        self.assertGreater(result["emPeak"], 90)

    def test_bundled_cache_records_keep_real_bundled_spectra(self) -> None:
        result = self.run_node_json(
            """
            const fluor = rt.searchFallbackFluorophores('mCherry')[0];
            return {
              name: fluor.name,
              spectraSource: fluor.spectraSource,
              exPoints: fluor.spectra.ex1p.length,
              emPoints: fluor.spectra.em.length,
              activeStateName: fluor.activeStateName,
            };
            """
        )

        self.assertEqual(result["name"], "mCherry")
        self.assertEqual(result["spectraSource"], "bundled_cache")
        self.assertGreater(result["exPoints"], 5)
        self.assertGreater(result["emPoints"], 5)
        self.assertIn(result["activeStateName"], {"Default state", "default"})

    def test_csu_w1_projection_stage_option_values_preserve_parser_authored_spectral_ops(self) -> None:
        payload = self.parser_payload_for_instrument("3i CSU-W1 Spinning Disk.yaml")
        runtime_projection = payload["projections"]["virtual_microscope"]["stages"]

        expected_emission = self._find_stage_option_value(
            runtime_projection["emission"],
            "Slot 1: 440/25 + 521/25 + 607/25 + 700/25",
        )
        expected_dichroic = self._find_stage_option_value(
            runtime_projection["dichroic"],
            "Slot 1: Quad-band Dichroic",
        )
        self.assertIsNotNone(expected_emission)
        self.assertIsNotNone(expected_dichroic)

        normalized_emission = self.normalized_stage_option_value(
            payload,
            "emission",
            "Slot 1: 440/25 + 521/25 + 607/25 + 700/25",
        )
        normalized_dichroic = self.normalized_stage_option_value(
            payload,
            "dichroic",
            "Slot 1: Quad-band Dichroic",
        )

        self.assertEqual(normalized_emission["spectral_ops"], expected_emission["spectral_ops"])
        self.assertEqual(normalized_emission.get("routes"), expected_emission.get("routes"))
        self.assertEqual(normalized_emission.get("path"), expected_emission.get("path"))
        self.assertEqual(normalized_dichroic["spectral_ops"], expected_dichroic["spectral_ops"])
        self.assertEqual(normalized_dichroic.get("routes"), expected_dichroic.get("routes"))
        self.assertEqual(normalized_dichroic.get("path"), expected_dichroic.get("path"))

    def test_esight_projection_stage_option_values_preserve_parser_authored_cube_payload(self) -> None:
        payload = self.parser_payload_for_instrument("xCELLigence RTCA eSight.yaml")
        runtime_projection = payload["projections"]["virtual_microscope"]["stages"]

        expected_blue_channel = self._find_stage_option_value(
            runtime_projection["cube"],
            "Slot 1: Blue Channel",
        )
        self.assertIsNotNone(expected_blue_channel)

        normalized_blue_channel = self.normalized_stage_option_value(
            payload,
            "cube",
            "Slot 1: Blue Channel",
        )

        self.assertEqual(normalized_blue_channel["spectral_ops"], expected_blue_channel["spectral_ops"])
        self.assertEqual(normalized_blue_channel.get("excitation_filter"), expected_blue_channel.get("excitation_filter"))
        self.assertEqual(normalized_blue_channel.get("dichroic"), expected_blue_channel.get("dichroic"))
        self.assertEqual(normalized_blue_channel.get("emission_filter"), expected_blue_channel.get("emission_filter"))
        self.assertEqual(normalized_blue_channel.get("routes"), expected_blue_channel.get("routes"))
        self.assertEqual(normalized_blue_channel.get("path"), expected_blue_channel.get("path"))

    def test_projection_stage_option_labels_keep_spectral_ops_after_runtime_normalization(self) -> None:
        cases = [
            (
                "3i CSU-W1 Spinning Disk.yaml",
                "emission",
                "Slot 1: 440/25 + 521/25 + 607/25 + 700/25",
            ),
            (
                "3i CSU-W1 Spinning Disk.yaml",
                "dichroic",
                "Slot 1: Quad-band Dichroic",
            ),
            (
                "xCELLigence RTCA eSight.yaml",
                "cube",
                "Slot 1: Blue Channel",
            ),
        ]

        for instrument_name, stage_role, target_label in cases:
            with self.subTest(instrument=instrument_name, stage=stage_role, label=target_label):
                payload = self.parser_payload_for_instrument(instrument_name)
                runtime_projection = payload["projections"]["virtual_microscope"]["stages"]
                expected_value = self._find_stage_option_value(runtime_projection[stage_role], target_label)
                self.assertIsNotNone(expected_value)
                self.assertIsNotNone(expected_value.get("spectral_ops"))

                normalized_value = self.normalized_stage_option_value(payload, stage_role, target_label)
                self.assertIsNotNone(normalized_value)
                self.assertIsNotNone(normalized_value.get("spectral_ops"))
                self.assertEqual(normalized_value["spectral_ops"], expected_value["spectral_ops"])

    def test_branch_sequence_uses_parser_resolved_positioned_component_payload(self) -> None:
        result = self.run_node_json(
            """
            const routeSteps = [
              { step_id: 'illumination-step-0', order: 0, phase: 'illumination', kind: 'source', source_id: 'src_488', component_id: 'src_488' },
              { step_id: 'sample-step-1', order: 1, phase: 'sample', kind: 'sample', component_id: 'sample_plane' },
              { step_id: 'detection-step-2', order: 2, phase: 'detection', kind: 'optical_component', component_id: 'main_splitter', stage_role: 'splitter' },
              {
                step_id: 'detection-step-3',
                order: 3,
                phase: 'detection',
                kind: 'routing_component',
                component_id: 'confocal_branch_block_1',
                routing: {
                  selection_mode: 'exclusive',
                  branches: [
                    {
                      branch_id: 'green',
                      label: 'Green',
                      mode: 'reflected',
                      sequence: [
                        {
                          kind: 'optical_component',
                          component_id: 'wheel_1',
                          position_id: '1',
                          position_key: '1',
                          position_label: '525/50',
                          component_type: 'bandpass',
                          spectral_ops: {
                            illumination: [{ op: 'bandpass', center_nm: 525, width_nm: 50 }],
                            detection: [{ op: 'bandpass', center_nm: 525, width_nm: 50 }]
                          }
                        },
                        { kind: 'detector', detector_id: 'cam_a', endpoint_id: 'cam_a', component_id: 'cam_a' }
                      ]
                    },
                    {
                      branch_id: 'red',
                      label: 'Red',
                      mode: 'transmitted',
                      sequence: [
                        {
                          kind: 'optical_component',
                          component_id: 'wheel_1',
                          position_id: '2',
                          position_key: '2',
                          position_label: '700/75',
                          component_type: 'bandpass',
                          spectral_ops: {
                            illumination: [{ op: 'bandpass', center_nm: 700, width_nm: 75 }],
                            detection: [{ op: 'bandpass', center_nm: 700, width_nm: 75 }]
                          }
                        },
                        { kind: 'detector', detector_id: 'cam_b', endpoint_id: 'cam_b', component_id: 'cam_b' }
                      ]
                    }
                  ]
                }
              }
            ];
            const instrument = rt.normalizeInstrumentPayload({
              metadata: { simulation_mode: 'strict' },
              simulation: { default_route: 'confocal' },
              sources: [{ id: 'src_488', display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }],
              optical_path_elements: [
                { id: 'main_splitter', stage_role: 'splitter', element_type: 'splitter', display_label: 'Main splitter', selection_mode: 'exclusive' },
                {
                  id: 'wheel_1',
                  stage_role: 'emission',
                  element_type: 'filter_wheel',
                  display_label: 'Emission wheel',
                  positions: {
                    1: { component_type: 'bandpass', center_nm: 525, width_nm: 50, label: '525/50' },
                    2: { component_type: 'bandpass', center_nm: 700, width_nm: 75, label: '700/75' }
                  }
                }
              ],
              endpoints: [
                { id: 'cam_a', display_label: 'Cam A', endpoint_type: 'camera' },
                { id: 'cam_b', display_label: 'Cam B', endpoint_type: 'camera' }
              ],
              light_paths: [
                {
                  id: 'confocal',
                  illumination_sequence: [{ source_id: 'src_488' }],
                  detection_sequence: [
                    { optical_path_element_id: 'main_splitter' },
                    { branches: { selection_mode: 'exclusive', items: [
                      { branch_id: 'green', mode: 'reflected', sequence: [{ optical_path_element_id: 'wheel_1', position_id: '1' }, { endpoint_id: 'cam_a' }] },
                      { branch_id: 'red', mode: 'transmitted', sequence: [{ optical_path_element_id: 'wheel_1', position_id: '2' }, { endpoint_id: 'cam_b' }] }
                    ] } }
                  ],
                  route_steps: routeSteps,
                  selected_execution: { contract_version: 'selected_execution.v2', selected_route_steps: routeSteps }
                }
              ]
            });
            const splitters = instrument.splitters || [];
            return {
              splitterCount: splitters.length,
              centers: splitters[0].branches.map((branch) => branch.component.center_nm),
              labels: splitters[0].branches.map((branch) => branch.component.display_label || branch.component.label),
            };
            """
        )

        self.assertEqual(result["splitterCount"], 1)
        self.assertEqual(result["centers"], [525, 700])
        self.assertEqual(result["labels"], ["525/50", "700/75"])

    def test_projection_authored_splitters_are_preferred_over_raw_topology_reconstruction(self) -> None:
        result = self.run_node_json(
            """
            const payload = {
              metadata: { simulation_mode: 'strict' },
              sources: [{ id: 'src_488', display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }],
              optical_path_elements: [
                { id: 'main_splitter', stage_role: 'splitter', element_type: 'splitter', display_label: 'Main splitter', selection_mode: 'exclusive' },
                {
                  id: 'wheel_1',
                  stage_role: 'emission',
                  element_type: 'filter_wheel',
                  display_label: 'Emission wheel',
                  positions: {
                    1: { component_type: 'bandpass', center_nm: 525, width_nm: 50, label: '525/50' },
                    2: { component_type: 'bandpass', center_nm: 700, width_nm: 75, label: '700/75' }
                  }
                }
              ],
              endpoints: [
                { id: 'cam_a', display_label: 'Cam A', endpoint_type: 'camera' },
                { id: 'cam_b', display_label: 'Cam B', endpoint_type: 'camera' }
              ],
              light_paths: [
                {
                  id: 'confocal',
                  illumination_sequence: [{ source_id: 'src_488' }],
                  detection_sequence: [
                    { optical_path_element_id: 'main_splitter' },
                    { branches: { selection_mode: 'exclusive', items: [
                      { branch_id: 'green', mode: 'reflected', sequence: [{ optical_path_element_id: 'wheel_1', position_id: '1' }, { endpoint_id: 'cam_a' }] },
                      { branch_id: 'red', mode: 'transmitted', sequence: [{ optical_path_element_id: 'wheel_1', position_id: '2' }, { endpoint_id: 'cam_b' }] }
                    ] } }
                  ],
                  route_steps: []
                }
              ],
              projections: {
                virtual_microscope: {
                  splitters: [
                    {
                      id: 'main_splitter',
                      display_label: 'Main splitter',
                      routes: ['confocal'],
                      path: 'confocal',
                      branches: [
                        {
                          id: 'green',
                          label: 'Green',
                          mode: 'reflected',
                          target_ids: ['cam_a'],
                          routes: ['confocal'],
                          path: 'confocal',
                          component: {
                            component_type: 'bandpass',
                            center_nm: 610,
                            width_nm: 40,
                            display_label: '610/40',
                            spectral_ops: {
                              illumination: [{ op: 'bandpass', center_nm: 610, width_nm: 40 }],
                              detection: [{ op: 'bandpass', center_nm: 610, width_nm: 40 }]
                            }
                          }
                        },
                        {
                          id: 'red',
                          label: 'Red',
                          mode: 'transmitted',
                          target_ids: ['cam_b'],
                          routes: ['confocal'],
                          path: 'confocal',
                          component: {
                            component_type: 'bandpass',
                            center_nm: 740,
                            width_nm: 30,
                            display_label: '740/30',
                            spectral_ops: {
                              illumination: [{ op: 'bandpass', center_nm: 740, width_nm: 30 }],
                              detection: [{ op: 'bandpass', center_nm: 740, width_nm: 30 }]
                            }
                          }
                        }
                      ]
                    }
                  ]
                }
              }
            };
            const instrument = rt.normalizeInstrumentPayload(payload);
            return instrument.splitters.map((splitter) => ({
              routes: splitter.__routes || splitter.routes || [],
              branches: (splitter.branches || []).map((branch) => ({
                id: branch.id,
                target_ids: branch.target_ids,
                routes: branch.__routes || branch.routes || [],
                center_nm: branch.component && branch.component.center_nm,
                width_nm: branch.component && branch.component.width_nm,
                display_label: branch.component && branch.component.display_label,
                spectral_ops: branch.component && branch.component.spectral_ops,
              })),
            }));
            """
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["routes"], ["confocal"])
        self.assertEqual(
            result[0]["branches"],
            [
                {
                    "id": "green",
                    "target_ids": ["cam_a"],
                    "routes": ["confocal"],
                    "center_nm": 610,
                    "width_nm": 40,
                    "display_label": "610/40",
                    "spectral_ops": {
                        "illumination": [{"op": "bandpass", "center_nm": 610, "width_nm": 40}],
                        "detection": [{"op": "bandpass", "center_nm": 610, "width_nm": 40}],
                    },
                },
                {
                    "id": "red",
                    "target_ids": ["cam_b"],
                    "routes": ["confocal"],
                    "center_nm": 740,
                    "width_nm": 30,
                    "display_label": "740/30",
                    "spectral_ops": {
                        "illumination": [{"op": "bandpass", "center_nm": 740, "width_nm": 30}],
                        "detection": [{"op": "bandpass", "center_nm": 740, "width_nm": 30}],
                    },
                },
            ],
        )

    def test_parser_branch_sequence_optics_drive_splitter_paths(self) -> None:
        result = self.run_node_json(
            """
            function fluor(key, emCenter) {
              return {
                key,
                name: key,
                activeStateName: 'Default',
                spectra: {
                  ex1p: [[450, 0], [470, 30], [488, 100], [510, 20], [540, 0]],
                  ex2p: [],
                  em: [[emCenter - 25, 0], [emCenter - 10, 45], [emCenter, 100], [emCenter + 10, 50], [emCenter + 25, 0]]
                },
                exMax: 488,
                emMax: emCenter
              };
            }
            const routeSteps = [
              { step_id: 'illumination-step-0', order: 0, phase: 'illumination', kind: 'source', source_id: 'src_488', component_id: 'src_488' },
              { step_id: 'sample-step-1', order: 1, phase: 'sample', kind: 'sample', component_id: 'sample_plane' },
              { step_id: 'detection-step-2', order: 2, phase: 'detection', kind: 'optical_component', component_id: 'main_splitter', stage_role: 'splitter' },
              {
                step_id: 'detection-step-3',
                order: 3,
                phase: 'detection',
                kind: 'routing_component',
                component_id: 'confocal_branch_block_1',
                routing: {
                  selection_mode: 'exclusive',
                  branches: [
                    {
                      branch_id: 'green',
                      label: 'Green path',
                      mode: 'reflected',
                      sequence: [
                        {
                          kind: 'optical_component',
                          component_id: 'wheel_1',
                          position_id: '1',
                          position_key: '1',
                          position_label: '525/50',
                          component_type: 'bandpass',
                          spectral_ops: {
                            illumination: [{ op: 'bandpass', center_nm: 525, width_nm: 50 }],
                            detection: [{ op: 'bandpass', center_nm: 525, width_nm: 50 }]
                          }
                        },
                        { kind: 'detector', detector_id: 'cam_a', endpoint_id: 'cam_a', component_id: 'cam_a' }
                      ]
                    },
                    {
                      branch_id: 'red',
                      label: 'Red path',
                      mode: 'transmitted',
                      sequence: [
                        {
                          kind: 'optical_component',
                          component_id: 'wheel_1',
                          position_id: '2',
                          position_key: '2',
                          position_label: '700/75',
                          component_type: 'bandpass',
                          spectral_ops: {
                            illumination: [{ op: 'bandpass', center_nm: 700, width_nm: 75 }],
                            detection: [{ op: 'bandpass', center_nm: 700, width_nm: 75 }]
                          }
                        },
                        { kind: 'detector', detector_id: 'cam_b', endpoint_id: 'cam_b', component_id: 'cam_b' }
                      ]
                    }
                  ]
                }
              }
            ];
            const rawInstrument = {
              metadata: { simulation_mode: 'strict' },
              simulation: { default_route: 'confocal', wavelength_grid: { min_nm: 430, max_nm: 760, step_nm: 2 } },
              sources: [{ id: 'src_488', display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }],
              optical_path_elements: [
                { id: 'main_splitter', stage_role: 'splitter', element_type: 'splitter', display_label: 'Main splitter', selection_mode: 'exclusive' },
                {
                  id: 'wheel_1',
                  stage_role: 'emission',
                  element_type: 'filter_wheel',
                  display_label: 'Emission wheel',
                  positions: {
                    1: { component_type: 'bandpass', center_nm: 525, width_nm: 50, label: '525/50' },
                    2: { component_type: 'bandpass', center_nm: 700, width_nm: 75, label: '700/75' }
                  }
                }
              ],
              endpoints: [
                { id: 'cam_a', display_label: 'Cam A', endpoint_type: 'camera' },
                { id: 'cam_b', display_label: 'Cam B', endpoint_type: 'camera' }
              ],
              light_paths: [
                {
                  id: 'confocal',
                  illumination_sequence: [{ source_id: 'src_488' }],
                  detection_sequence: [
                    { optical_path_element_id: 'main_splitter' },
                    { branches: { selection_mode: 'exclusive', items: [
                      { branch_id: 'green', label: 'Green path', mode: 'reflected', sequence: [{ optical_path_element_id: 'wheel_1', position_id: '1' }, { endpoint_id: 'cam_a' }] },
                      { branch_id: 'red', label: 'Red path', mode: 'transmitted', sequence: [{ optical_path_element_id: 'wheel_1', position_id: '2' }, { endpoint_id: 'cam_b' }] }
                    ] } }
                  ],
                  route_steps: routeSteps,
                  selected_execution: { contract_version: 'selected_execution.v2', selected_route_steps: routeSteps }
                }
              ]
            };
            const instrument = rt.normalizeInstrumentPayload(rawInstrument);
            const split = rt.simulateInstrument(
              rawInstrument,
              {
                sources: [{ id: 'src_488', display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }],
                illuminationComponents: [{ component: { component_type: 'passthrough', spectral_ops: { illumination: [{ op: 'passthrough' }], detection: [{ op: 'passthrough' }] } }, mode: 'excitation', routeStepId: 'illumination-step-0' }],
                detectionComponents: [{ component: { component_type: 'passthrough', spectral_ops: { illumination: [{ op: 'passthrough' }], detection: [{ op: 'passthrough' }] } }, mode: 'emission', routeStepId: 'detection-step-0' }],
                excitation: [],
                dichroic: [],
                emission: [],
                splitters: [{
                  id: 'main_splitter',
                  branch_selection_required: true,
                  selected_branch_ids: ['green', 'red'],
                  branches: instrument.splitters[0].branches
                }],
                detectors: [
                  { id: 'cam_a', display_label: 'Cam A', kind: 'camera' },
                  { id: 'cam_b', display_label: 'Cam B', kind: 'camera' }
                ],
                selectionMap: {}
              },
              [fluor('green', 525), fluor('red', 670)],
              { currentRoute: 'confocal' }
            );
            const rows = split.results.map((row) => ({ fluor: row.fluorophoreKey, path: row.pathLabel, intensity: row.detectorWeightedIntensity }));
            return { rows };
            """
        )

        rows = {(row["fluor"], row["path"]): row["intensity"] for row in result["rows"]}
        self.assertGreater(rows[("green", "Main Path -> Green path -> Cam A")], rows[("green", "Main Path -> Red path -> Cam B")])
        self.assertGreater(rows[("red", "Main Path -> Red path -> Cam B")], rows[("red", "Main Path -> Green path -> Cam A")])

    def test_simulate_instrument_materializes_reused_cube_traversal_from_selection_map(self) -> None:
        result = self.run_node_json(
            """
            function fluor() {
              return {
                key: 'green',
                name: 'Green',
                activeStateName: 'Default',
                spectra: {
                  ex1p: [[450, 0], [488, 100], [530, 0]],
                  ex2p: [],
                  em: [[500, 0], [525, 100], [560, 0]]
                },
                exMax: 488,
                emMax: 525
              };
            }
            const cubePositions = {
              1: {
                slot: 1,
                position_key: '1',
                display_label: '405 cube',
                component_type: 'filter_cube',
                spectral_ops: {
                  illumination: [{ op: 'bandpass', center_nm: 405, width_nm: 20 }],
                  detection: [{ op: 'bandpass', center_nm: 450, width_nm: 30 }]
                }
              },
              2: {
                slot: 2,
                position_key: '2',
                display_label: '488 cube',
                component_type: 'filter_cube',
                spectral_ops: {
                  illumination: [{ op: 'bandpass', center_nm: 488, width_nm: 20 }],
                  detection: [{ op: 'bandpass', center_nm: 525, width_nm: 40 }]
                }
              }
            };
            const availablePositions = Object.values(cubePositions).map((entry) => ({
              position_key: entry.position_key,
              label: entry.display_label,
              component_type: entry.component_type,
              spectral_ops: entry.spectral_ops
            }));
            const routeSteps = [
              { step_id: 'illumination-source', order: 0, phase: 'illumination', kind: 'source', source_id: 'src_488', component_id: 'src_488' },
              {
                step_id: 'illumination-cube',
                order: 1,
                phase: 'illumination',
                kind: 'optical_component',
                component_id: 'filter_cube',
                mechanism_id: 'filter_cube',
                stage_role: 'cube',
                selection_state: 'unresolved',
                available_positions: availablePositions
              },
              { step_id: 'sample', order: 2, phase: 'sample', kind: 'sample', component_id: 'sample_plane' },
              {
                step_id: 'detection-cube',
                order: 3,
                phase: 'detection',
                kind: 'optical_component',
                component_id: 'filter_cube',
                mechanism_id: 'filter_cube',
                stage_role: 'cube',
                selection_state: 'unresolved',
                available_positions: availablePositions
              },
              { step_id: 'detector', order: 4, phase: 'detection', kind: 'detector', detector_id: 'cam_1', endpoint_id: 'cam_1', component_id: 'cam_1' }
            ];
            const instrument = {
              metadata: { simulation_mode: 'strict' },
              simulation: { default_route: 'confocal', wavelength_grid: { min_nm: 430, max_nm: 700, step_nm: 2 } },
              sources: [{ id: 'src_488', display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }],
              optical_path_elements: [
                {
                  id: 'filter_cube',
                  stage_role: 'cube',
                  element_type: 'filter_cube_turret',
                  display_label: 'Filter cube turret',
                  positions: cubePositions
                }
              ],
              endpoints: [{ id: 'cam_1', display_label: 'Cam 1', endpoint_type: 'camera' }],
              light_paths: [{
                id: 'confocal',
                illumination_sequence: [{ source_id: 'src_488' }, { optical_path_element_id: 'filter_cube', position_id: '2' }],
                detection_sequence: [{ optical_path_element_id: 'filter_cube', position_id: '2' }, { endpoint_id: 'cam_1' }],
                route_steps: routeSteps,
                selected_execution: { contract_version: 'selected_execution.v2', selected_route_steps: routeSteps }
              }]
            };
            function summarize(slot) {
              const simulation = rt.simulateInstrument(
                instrument,
                {
                  sources: [{ id: 'src_488', display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }],
                  detectors: [{ id: 'cam_1', display_label: 'Cam 1', endpoint_type: 'camera' }],
                  selectionMap: { filter_cube: slot }
                },
                [fluor()],
                { currentRoute: 'confocal' }
              );
              return {
                validSelection: simulation.validSelection,
                resultCount: simulation.results.length,
                intensity: simulation.results[0] ? simulation.results[0].detectorWeightedIntensity : 0
              };
            }
            return { blocked: summarize(1), open: summarize(2) };
            """
        )

        self.assertTrue(result["blocked"]["validSelection"])
        self.assertTrue(result["open"]["validSelection"])
        self.assertEqual(result["blocked"]["resultCount"], 1)
        self.assertEqual(result["open"]["resultCount"], 1)
        self.assertGreater(result["open"]["intensity"], result["blocked"]["intensity"])

    def test_optimize_light_path_materializes_traversal_for_splitter_routes(self) -> None:
        result = self.run_node_json(
            """
            function fluor() {
              return {
                key: 'green',
                name: 'Green',
                activeStateName: 'Default',
                spectra: {
                  ex1p: [[450, 0], [488, 100], [530, 0]],
                  ex2p: [],
                  em: [[500, 0], [525, 100], [560, 0]]
                },
                exMax: 488,
                emMax: 525
              };
            }
            const cubePositions = {
              1: {
                slot: 1,
                position_key: '1',
                display_label: '405 cube',
                component_type: 'filter_cube',
                spectral_ops: {
                  illumination: [{ op: 'bandpass', center_nm: 405, width_nm: 20 }],
                  detection: [{ op: 'bandpass', center_nm: 450, width_nm: 30 }]
                }
              },
              2: {
                slot: 2,
                position_key: '2',
                display_label: '488 cube',
                component_type: 'filter_cube',
                spectral_ops: {
                  illumination: [{ op: 'bandpass', center_nm: 488, width_nm: 20 }],
                  detection: [{ op: 'bandpass', center_nm: 525, width_nm: 40 }]
                }
              }
            };
            const availablePositions = Object.values(cubePositions).map((entry) => ({
              position_key: entry.position_key,
              label: entry.display_label,
              component_type: entry.component_type,
              spectral_ops: entry.spectral_ops
            }));
            const routeSteps = [
              { step_id: 'illumination-source', order: 0, phase: 'illumination', kind: 'source', source_id: 'src_488', component_id: 'src_488' },
              {
                step_id: 'illumination-cube',
                order: 1,
                phase: 'illumination',
                kind: 'optical_component',
                component_id: 'filter_cube',
                mechanism_id: 'filter_cube',
                stage_role: 'cube',
                selection_state: 'unresolved',
                available_positions: availablePositions
              },
              { step_id: 'sample', order: 2, phase: 'sample', kind: 'sample', component_id: 'sample_plane' },
              {
                step_id: 'detection-cube',
                order: 3,
                phase: 'detection',
                kind: 'optical_component',
                component_id: 'filter_cube',
                mechanism_id: 'filter_cube',
                stage_role: 'cube',
                selection_state: 'unresolved',
                available_positions: availablePositions
              },
              { step_id: 'splitter', order: 4, phase: 'detection', kind: 'optical_component', component_id: 'main_splitter', stage_role: 'splitter', component_type: 'splitter' },
              {
                step_id: 'routing',
                order: 5,
                phase: 'detection',
                kind: 'routing_component',
                component_id: 'main_splitter',
                routing: {
                  selection_mode: 'exclusive',
                  branches: [
                    { branch_id: 'green', label: 'Green path', mode: 'reflected', sequence: [{ kind: 'detector', detector_id: 'cam_a', endpoint_id: 'cam_a', component_id: 'cam_a' }] },
                    { branch_id: 'red', label: 'Red path', mode: 'transmitted', sequence: [{ kind: 'detector', detector_id: 'cam_b', endpoint_id: 'cam_b', component_id: 'cam_b' }] }
                  ]
                }
              }
            ];
            const instrument = {
              metadata: { simulation_mode: 'strict' },
              simulation: { default_route: 'confocal', wavelength_grid: { min_nm: 430, max_nm: 760, step_nm: 2 } },
              sources: [{ id: 'src_488', display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }],
              optical_path_elements: [
                {
                  id: 'filter_cube',
                  stage_role: 'cube',
                  element_type: 'filter_cube_turret',
                  display_label: 'Filter cube turret',
                  positions: cubePositions
                },
                { id: 'main_splitter', stage_role: 'splitter', element_type: 'splitter', display_label: 'Main splitter', selection_mode: 'exclusive' }
              ],
              endpoints: [
                { id: 'cam_a', display_label: 'Cam A', endpoint_type: 'camera' },
                { id: 'cam_b', display_label: 'Cam B', endpoint_type: 'camera' }
              ],
              light_paths: [{
                id: 'confocal',
                illumination_sequence: [{ source_id: 'src_488' }, { optical_path_element_id: 'filter_cube', position_id: '2' }],
                detection_sequence: [
                  { optical_path_element_id: 'filter_cube', position_id: '2' },
                  { optical_path_element_id: 'main_splitter' },
                  {
                    branches: {
                      selection_mode: 'exclusive',
                      items: [
                        { branch_id: 'green', label: 'Green path', mode: 'reflected', sequence: [{ endpoint_id: 'cam_a' }] },
                        { branch_id: 'red', label: 'Red path', mode: 'transmitted', sequence: [{ endpoint_id: 'cam_b' }] }
                      ]
                    }
                  }
                ],
                route_steps: routeSteps,
                selected_execution: { contract_version: 'selected_execution.v2', selected_route_steps: routeSteps }
              }],
              projections: {
                virtual_microscope: {
                  splitters: [{
                    id: 'main_splitter',
                    display_label: 'Main splitter',
                    routes: ['confocal'],
                    path: 'confocal',
                    branches: [
                      {
                        id: 'green',
                        label: 'Green path',
                        mode: 'reflected',
                        target_ids: ['cam_a'],
                        routes: ['confocal'],
                        path: 'confocal',
                        component: {
                          component_type: 'bandpass',
                          center_nm: 525,
                          width_nm: 40,
                          display_label: '525/40',
                          spectral_ops: {
                            illumination: [{ op: 'bandpass', center_nm: 525, width_nm: 40 }],
                            detection: [{ op: 'bandpass', center_nm: 525, width_nm: 40 }]
                          }
                        }
                      },
                      {
                        id: 'red',
                        label: 'Red path',
                        mode: 'transmitted',
                        target_ids: ['cam_b'],
                        routes: ['confocal'],
                        path: 'confocal',
                        component: {
                          component_type: 'bandpass',
                          center_nm: 700,
                          width_nm: 75,
                          display_label: '700/75',
                          spectral_ops: {
                            illumination: [{ op: 'bandpass', center_nm: 700, width_nm: 75 }],
                            detection: [{ op: 'bandpass', center_nm: 700, width_nm: 75 }]
                          }
                        }
                      }
                    ]
                  }]
                }
              }
            };
            const optimized = rt.optimizeLightPath([fluor()], instrument, { currentRoute: 'confocal' });
            return optimized ? {
              route: optimized.route,
              score: optimized.score,
              splitters: optimized.splitters,
              detectors: optimized.detectors
            } : null;
            """
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["route"], "confocal")
        self.assertGreater(result["score"], 0)
        self.assertEqual(result["splitters"][0]["mechanismId"], "main_splitter")
        self.assertEqual(result["splitters"][0]["selected_branch_ids"], ["green", "red"])
        self.assertGreaterEqual(len(result["detectors"]), 1)

    def test_normalize_terminals_preserves_undefined_default_enabled(self) -> None:
        result = self.run_node_json(
            """
            const terminals = rt.normalizeTerminals([
              { id: 'cam_default', display_label: 'Default Camera', endpoint_type: 'camera' },
              { id: 'cam_false', display_label: 'Disabled Camera', endpoint_type: 'camera', default_enabled: false },
              { id: 'cam_true', display_label: 'Enabled Camera', endpoint_type: 'camera', default_enabled: true }
            ]);
            return terminals.map((terminal) => ({
              id: terminal.id,
              defaultEnabledType: typeof terminal.default_enabled,
              defaultEnabled: terminal.default_enabled === undefined ? null : terminal.default_enabled
            }));
            """
        )

        by_id = {row["id"]: row for row in result}
        self.assertEqual(by_id["cam_default"]["defaultEnabledType"], "undefined")
        self.assertIsNone(by_id["cam_default"]["defaultEnabled"])
        self.assertFalse(by_id["cam_false"]["defaultEnabled"])
        self.assertTrue(by_id["cam_true"]["defaultEnabled"])

    def test_simulate_instrument_allows_zero_selected_detectors(self) -> None:
        result = self.run_node_json(
            """
            function fluor() {
              return {
                key: 'green',
                name: 'Green',
                activeStateName: 'Default',
                spectra: {
                  ex1p: [[450, 0], [488, 100], [530, 0]],
                  ex2p: [],
                  em: [[500, 0], [520, 100], [560, 0]]
                },
                exMax: 488,
                emMax: 520
              };
            }
            const routeSteps = [
              { step_id: 'illumination-step-0', order: 0, phase: 'illumination', kind: 'source', source_id: 'src_488', component_id: 'src_488' },
              { step_id: 'sample-step-1', order: 1, phase: 'sample', kind: 'sample', component_id: 'sample_plane' },
              { step_id: 'detection-step-2', order: 2, phase: 'detection', kind: 'detector', detector_id: 'cam_1', endpoint_id: 'cam_1', component_id: 'cam_1' }
            ];
            const instrument = {
              metadata: { simulation_mode: 'strict' },
              simulation: { default_route: 'confocal', wavelength_grid: { min_nm: 430, max_nm: 700, step_nm: 2 } },
              sources: [{ id: 'src_488', display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }],
              optical_path_elements: [],
              endpoints: [{ id: 'cam_1', display_label: 'Cam 1', endpoint_type: 'camera' }],
              light_paths: [{
                id: 'confocal',
                illumination_sequence: [{ source_id: 'src_488' }],
                detection_sequence: [{ endpoint_id: 'cam_1' }],
                route_steps: routeSteps,
                selected_execution: { contract_version: 'selected_execution.v2', selected_route_steps: routeSteps }
              }]
            };
            const baseSelection = {
              sources: [{ id: 'src_488', display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }],
              illuminationComponents: [{ component: { component_type: 'passthrough', spectral_ops: { illumination: [{ op: 'passthrough' }], detection: [{ op: 'passthrough' }] } }, mode: 'excitation', routeStepId: 'illumination-step-0' }],
              detectionComponents: [{ component: { component_type: 'passthrough', spectral_ops: { illumination: [{ op: 'passthrough' }], detection: [{ op: 'passthrough' }] } }, mode: 'emission', routeStepId: 'detection-step-2' }],
              excitation: [],
              dichroic: [],
              emission: [],
              splitters: [],
              selectionMap: {}
            };
            function summarize(selection) {
              const simulation = rt.simulateInstrument(
                instrument,
                selection,
                [fluor()],
                { currentRoute: 'confocal' }
              );
              return {
                selectedDetectors: simulation.selectedDetectors,
                resultsCount: simulation.results.length,
                pathSpectraCount: simulation.pathSpectra.length,
                validSelection: simulation.validSelection
              };
            }
            return {
              explicitEmpty: summarize({ ...baseSelection, detectors: [] }),
              missingDetectors: summarize(baseSelection),
              nullDetectors: summarize({ ...baseSelection, detectors: null })
            };
            """
        )

        for variant in ("explicitEmpty", "missingDetectors", "nullDetectors"):
            self.assertEqual(result[variant]["selectedDetectors"], [])
            self.assertEqual(result[variant]["resultsCount"], 0)
            self.assertEqual(result[variant]["pathSpectraCount"], 0)
            self.assertTrue(result[variant]["validSelection"])

    def test_live_fpbase_mcherry_search_smoke(self) -> None:
        url = "https://www.fpbase.org/api/proteins/?name__iexact=mCherry&format=json"
        try:
            with urllib.request.urlopen(url, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            self.skipTest(f"Live FPbase API unavailable in this environment: {exc}")

        rows = payload if isinstance(payload, list) else payload.get("results", [])
        match = next((row for row in rows if row.get("name") == "mCherry"), None)
        self.assertIsNotNone(match)
        state = (match.get("states") or [{}])[0]
        self.assertEqual(state.get("ex_max"), 587)
        self.assertEqual(state.get("em_max"), 610)

    def test_route_sort_order_is_exported_and_matches_python(self) -> None:
        result = self.run_node_json(
            """
            return rt.ROUTE_SORT_ORDER;
            """
        )

        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 5, "ROUTE_SORT_ORDER should contain all route tags, not just 5")
        self.assertIn("confocal", result)
        self.assertIn("confocal_point", result)
        self.assertIn("confocal_spinning_disk", result)
        self.assertIn("widefield_fluorescence", result)
        self.assertIn("tirf", result)
        self.assertIn("light_sheet", result)
        self.assertIn("flim", result)
        self.assertIn("ism", result)
        self.assertIn("transmitted_brightfield", result)
        self.assertIn("darkfield", result)
        self.assertIn("phase_contrast", result)
        self.assertIn("dic", result)

    def test_all_route_tags_accepted_by_normalize(self) -> None:
        result = self.run_node_json(
            """
            const allRoutes = [
              'epi', 'widefield_fluorescence', 'tirf', 'confocal', 'confocal_point',
              'confocal_spinning_disk', 'multiphoton', 'light_sheet', 'transmitted',
              'transmitted_brightfield', 'phase_contrast', 'darkfield', 'dic',
              'reflected_brightfield', 'optical_sectioning', 'spectral_imaging',
              'flim', 'fcs', 'ism', 'smlm', 'spt', 'fret'
            ];
            const normalized = rt.normalizeRouteTags(allRoutes);
            return { input: allRoutes, output: normalized };
            """
        )

        input_set = set(result["input"])
        output_set = set(result["output"])
        dropped = input_set - output_set
        self.assertEqual(len(result["input"]), len(result["output"]),
                         f"All route tags should be accepted; dropped: {dropped}")

    def test_eyepiece_detector_response_honors_dto_bounds(self) -> None:
        result = self.run_node_json(
            """
            const grid = rt.wavelengthGrid({ min_nm: 350, max_nm: 800, step_nm: 2 });
            const defaultResponse = rt.detectorResponse(
              { kind: 'eyepiece', endpoint_type: 'eyepiece' },
              grid
            );
            const customResponse = rt.detectorResponse(
              { kind: 'eyepiece', endpoint_type: 'eyepiece', collection_min_nm: 350, collection_max_nm: 750 },
              grid
            );
            // Default eyepiece should not respond much at 370nm (below 390)
            const idx370 = grid.indexOf(370);
            const idx500 = grid.indexOf(500);
            // Custom eyepiece with 350-750 range should have response at 370nm
            return {
              defaultAt370: defaultResponse[idx370],
              defaultAt500: defaultResponse[idx500],
              customAt370: customResponse[idx370],
              customAt500: customResponse[idx500],
            };
            """
        )

        self.assertGreater(result["defaultAt500"], result["defaultAt370"],
                           "Default eyepiece should have lower response at 370nm than 500nm")
        self.assertGreater(result["customAt370"], result["defaultAt370"],
                           "Custom eyepiece with 350-750 bounds should have higher response at 370nm")

    # ── VM-005: Filter cube composite modeling ──────────────────────────

    # ── VM-006: Unsupported component surfacing ─────────────────────────

    # ── VM-006: analyzer stage flows through normalizeInstrumentPayload ──

    # ── VM-007: sequential acquisition detection ──

    def test_optimizer_filters_incomplete_cube_options_in_source(self) -> None:
        """Runtime optimizer should filter incomplete/unsupported cube options before scoring."""
        source = Path("scripts/templates/virtual_microscope_runtime.js").read_text(encoding="utf-8")
        self.assertIn("option.value._cube_incomplete", source)
        self.assertIn("option.value._unsupported_spectral_model", source)

    def test_optimizer_scores_cubes_directly_via_composite_spectral_ops(self) -> None:
        """Optimizer should score cubes via composite spectral_ops, not sub-component expansion."""
        source = Path("scripts/templates/virtual_microscope_runtime.js").read_text(encoding="utf-8")
        # expandCubeSelectionForOptimization must be deleted — Python owns optical meaning.
        self.assertNotIn("expandCubeSelectionForOptimization", source)
        # Cube scoring uses pointMaskScore directly on the cube composite.
        self.assertIn("pointMaskScore(option.value, exTargets, 'excitation')", source)
        self.assertIn("pointMaskScore(option.value, emTargets, 'emission')", source)
        # Selection building uses canonical parser field names (CUBE_LINK_KEYS).
        self.assertIn("cube.excitation_filter", source)
        self.assertIn("cube.dichroic", source)
        self.assertIn("cube.emission_filter", source)

    def test_runtime_cube_selection_building_uses_only_canonical_parser_field_names(self) -> None:
        source = Path("scripts/templates/virtual_microscope_runtime.js").read_text(encoding="utf-8")

        runtime_cube_block = source.split("cubeCombo.forEach(({ mechanism, option }) => {", 1)[1].split("exCombo.forEach", 1)[0]
        self.assertIn("cube.excitation_filter", runtime_cube_block)
        self.assertIn("cube.dichroic", runtime_cube_block)
        self.assertIn("cube.emission_filter", runtime_cube_block)
        self.assertNotRegex(runtime_cube_block, r"cube\.(?:ex|excitation|di|dichroic_filter|em|emission)\b")

    # ── executeSpectralOps tests ──────────────────────────────────────

    def test_execute_spectral_ops_bandpass(self) -> None:
        """executeSingleSpectralOp should produce a bandpass mask from an op spec."""
        result = self.run_node_json(
            """
            const grid = rt.wavelengthGrid({ min_nm: 400, max_nm: 700, step_nm: 2 });
            const mask = rt.executeSingleSpectralOp({ op: 'bandpass', center_nm: 525, width_nm: 50 }, grid);
            const peakIdx = grid.reduce((best, w, i) => Math.abs(w - 525) < Math.abs(grid[best] - 525) ? i : best, 0);
            const offIdx = grid.reduce((best, w, i) => Math.abs(w - 400) < Math.abs(grid[best] - 400) ? i : best, 0);
            return { peak: mask[peakIdx], off: mask[offIdx] };
            """
        )
        self.assertGreater(result["peak"], 0.9, "bandpass peak should be near 1.0")
        self.assertLess(result["off"], 0.01, "bandpass off-peak should be near 0")

    def test_execute_spectral_ops_dichroic_reflect_vs_transmit(self) -> None:
        """Dichroic reflect and transmit should be complementary."""
        result = self.run_node_json(
            """
            const grid = rt.wavelengthGrid({ min_nm: 400, max_nm: 700, step_nm: 2 });
            const reflect = rt.executeSingleSpectralOp({ op: 'dichroic_reflect', cut_on_nm: 505 }, grid);
            const transmit = rt.executeSingleSpectralOp({ op: 'dichroic_transmit', cut_on_nm: 505 }, grid);
            const below = grid.reduce((best, w, i) => Math.abs(w - 470) < Math.abs(grid[best] - 470) ? i : best, 0);
            const above = grid.reduce((best, w, i) => Math.abs(w - 560) < Math.abs(grid[best] - 560) ? i : best, 0);
            return {
              reflectBelow: reflect[below],
              reflectAbove: reflect[above],
              transmitBelow: transmit[below],
              transmitAbove: transmit[above],
            };
            """
        )
        self.assertGreater(result["reflectBelow"], 0.5, "below cut-on should reflect")
        self.assertLess(result["reflectAbove"], 0.5, "above cut-on should not reflect")
        self.assertLess(result["transmitBelow"], 0.5, "below cut-on should not transmit")
        self.assertGreater(result["transmitAbove"], 0.5, "above cut-on should transmit")

    def test_execute_spectral_ops_sequence(self) -> None:
        """executeSpectralOps should multiply ops sequentially."""
        result = self.run_node_json(
            """
            const grid = rt.wavelengthGrid({ min_nm: 400, max_nm: 700, step_nm: 2 });
            const ops = [
              { op: 'bandpass', center_nm: 525, width_nm: 50 },
              { op: 'longpass', cut_on_nm: 500 },
            ];
            const mask = rt.executeSpectralOps(ops, grid);
            const atCenter = grid.reduce((best, w, i) => Math.abs(w - 525) < Math.abs(grid[best] - 525) ? i : best, 0);
            const below = grid.reduce((best, w, i) => Math.abs(w - 480) < Math.abs(grid[best] - 480) ? i : best, 0);
            return { center: mask[atCenter], below: mask[below] };
            """
        )
        self.assertGreater(result["center"], 0.8, "center of combined bandpass+longpass should pass")
        self.assertLess(result["below"], 0.1, "below longpass cut-on should be blocked")

    def test_component_mask_prefers_spectral_ops_over_type(self) -> None:
        """When spectral_ops is present, componentMask should use it instead of the type."""
        result = self.run_node_json(
            """
            const grid = rt.wavelengthGrid({ min_nm: 400, max_nm: 700, step_nm: 2 });
            // Component has type=bandpass but spectral_ops says longpass —
            // spectral_ops should win.
            const component = {
              component_type: 'bandpass',
              center_nm: 525,
              width_nm: 50,
              spectral_ops: {
                illumination: [{ op: 'longpass', cut_on_nm: 500 }],
                detection: [{ op: 'longpass', cut_on_nm: 500 }],
              }
            };
            const mask = rt.componentMask(component, grid, { mode: 'excitation' });
            const below = grid.reduce((best, w, i) => Math.abs(w - 470) < Math.abs(grid[best] - 470) ? i : best, 0);
            const above = grid.reduce((best, w, i) => Math.abs(w - 550) < Math.abs(grid[best] - 550) ? i : best, 0);
            return { below: mask[below], above: mask[above] };
            """
        )
        # If spectral_ops wins, this is a longpass at 500nm, so below=0, above=1
        self.assertLess(result["below"], 0.1, "longpass should block below cut-on")
        self.assertGreater(result["above"], 0.9, "longpass should pass above cut-on")

    def test_source_centers_no_longer_parses_display_label(self) -> None:
        """sourceCenters must NOT parse wavelengths from display_label."""
        result = self.run_node_json(
            """
            return {
              fromLabel: rt.sourceCenters({ display_label: '488nm Laser' }),
              fromName: rt.sourceCenters({ name: '488nm Laser' }),
              fromExplicit: rt.sourceCenters({ wavelength_nm: 488 }),
            };
            """
        )
        self.assertEqual(result["fromLabel"], [], "display_label should not be parsed")
        self.assertEqual(result["fromName"], [], "name should not be parsed")
        self.assertEqual(result["fromExplicit"], [488])

if __name__ == "__main__":
    unittest.main()
