import json
import shutil
import subprocess
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = REPO_ROOT / "scripts" / "templates" / "virtual_microscope_runtime.js"


class VirtualMicroscopeRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("node") is None:
            raise unittest.SkipTest("Node.js is required for virtual microscope runtime tests.")
        if not RUNTIME_PATH.exists():
            raise unittest.SkipTest("Virtual microscope runtime script is missing.")

    def run_node_json(self, body: str) -> object:
        script = textwrap.dedent(
            f"""
            const rt = require('./scripts/templates/virtual_microscope_runtime.js');
            const result = (() => {{
            {body}
            }})();
            console.log(JSON.stringify(result));
            """
        )
        proc = subprocess.run(
            ["node", "-e", script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise AssertionError(f"Node runtime failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        return json.loads(proc.stdout)

    def test_fpbase_search_results_are_normalized(self) -> None:
        result = self.run_node_json(
            """
            return rt.normalizeFPbaseSearchResults({
              results: [{
                id: 123,
                slug: 'egfp',
                uuid: 'uuid-egfp',
                name: 'EGFP',
                default_state: { ex_max: 488, em_max: 509, brightness: 0.60, ec: 56000, qy: 0.60 }
              }]
            });
            """
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["key"], "uuid-egfp")
        self.assertEqual(result[0]["name"], "EGFP")
        self.assertEqual(result[0]["exMax"], 488)
        self.assertEqual(result[0]["emMax"], 509)
        self.assertEqual(result[0]["brightness"], 0.6)
        self.assertEqual(result[0]["ec"], 56000)
        self.assertEqual(result[0]["qy"], 0.6)

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

    def test_stage_propagation_and_detector_models_change_outputs(self) -> None:
        result = self.run_node_json(
            """
            const fluor = {
              key: 'green',
              name: 'Green',
              activeStateName: 'Default',
              spectra: {
                ex1p: [[450, 0], [470, 30], [488, 100], [510, 20], [540, 0]],
                ex2p: [],
                em: [[480, 0], [500, 50], [520, 100], [545, 60], [570, 10], [600, 0]]
              },
              exMax: 488,
              emMax: 520
            };
            const instrument = { metadata: { wavelength_grid: { min_nm: 450, max_nm: 750, step_nm: 2 } } };
            function simulate(emission) {
              return rt.simulateInstrument(
                instrument,
                {
                  sources: [{ display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }],
                  excitation: [{ component_type: 'bandpass', center_nm: 488, width_nm: 10 }],
                  dichroic: [],
                  emission: [emission],
                  splitters: [],
                  detectors: [
                    { id: 'cam', display_label: 'Camera', kind: 'camera', qe_peak_pct: 80, user_gain: 1 },
                    { id: 'pmt', display_label: 'PMT', kind: 'pmt', qe_peak_pct: 30, user_gain: 1 }
                  ],
                  selectionMap: {}
                },
                [fluor],
                {}
              );
            }
            const matched = simulate({ component_type: 'bandpass', center_nm: 525, width_nm: 50 });
            const offBand = simulate({ component_type: 'bandpass', center_nm: 700, width_nm: 50 });
            return {
              matched: matched.results,
              offBand: offBand.results
            };
            """
        )

        matched = {row["detectorKey"]: row for row in result["matched"]}
        off_band = {row["detectorKey"]: row for row in result["offBand"]}

        self.assertGreater(matched["cam"]["detectorWeightedIntensity"], matched["pmt"]["detectorWeightedIntensity"])
        self.assertGreater(matched["cam"]["emissionPathThroughput"], off_band["cam"]["emissionPathThroughput"])
        self.assertGreater(matched["cam"]["detectorWeightedIntensity"], off_band["cam"]["detectorWeightedIntensity"])
        self.assertGreater(matched["cam"]["excitationStrength"], 0)

    def test_splitter_branching_and_sted_quality_are_modeled(self) -> None:
        result = self.run_node_json(
            """
            function fluor(key, name, exMax, emMax, ex, em) {
              return {
                key,
                name,
                activeStateName: 'Default',
                spectra: { ex1p: ex, ex2p: [], em },
                exMax,
                emMax
              };
            }
            const green = fluor(
              'green',
              'Green',
              488,
              520,
              [[450, 0], [470, 30], [488, 100], [510, 20], [540, 0]],
              [[480, 0], [500, 50], [520, 100], [545, 60], [570, 10], [600, 0]]
            );
            const red = fluor(
              'red',
              'Red',
              640,
              670,
              [[580, 0], [610, 30], [640, 100], [660, 20], [690, 0]],
              [[620, 0], [650, 40], [670, 100], [700, 70], [730, 20], [760, 0]]
            );
            const broadFarRed = fluor(
              'farred',
              'FarRed',
              640,
              680,
              [[580, 0], [620, 40], [640, 100], [660, 30], [690, 0]],
              [[620, 0], [650, 90], [680, 100], [710, 95], [740, 90], [770, 85], [800, 70]]
            );
            const instrument = { metadata: { wavelength_grid: { min_nm: 450, max_nm: 820, step_nm: 2 } } };
            const splitterSelection = {
              sources: [
                { display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' },
                { display_label: '640 laser', kind: 'laser', role: 'excitation', wavelength_nm: 640, spectral_mode: 'line' }
              ],
              excitation: [{ component_type: 'passthrough' }],
              dichroic: [],
              emission: [],
              splitters: [{
                id: 'split1',
                dichroic: { positions: { 1: { component_type: 'dichroic', cutoffs_nm: [560] } } },
                branches: [
                  { id: 'red', label: 'Red path', mode: 'transmitted', component: { component_type: 'bandpass', center_nm: 700, width_nm: 75 } },
                  { id: 'green', label: 'Green path', mode: 'reflected', component: { component_type: 'bandpass', center_nm: 525, width_nm: 50 } }
                ]
              }],
              detectors: [{ id: 'cam', display_label: 'Camera', kind: 'camera', qe_peak_pct: 80, user_gain: 1 }],
              selectionMap: {}
            };
            const split = rt.simulateInstrument(instrument, splitterSelection, [green, red], {});
            const stedGood = rt.simulateInstrument(
              instrument,
              {
                sources: [
                  { display_label: '640 laser', kind: 'laser', role: 'excitation', wavelength_nm: 640, spectral_mode: 'line' },
                  { display_label: '775 STED', kind: 'laser', role: 'depletion', wavelength_nm: 775, spectral_mode: 'line', timing_mode: 'pulsed', depletion_targets_nm: [640] }
                ],
                excitation: [{ component_type: 'passthrough' }],
                dichroic: [],
                emission: [{ component_type: 'bandpass', center_nm: 720, width_nm: 150 }],
                splitters: [],
                detectors: [{ id: 'hyd', display_label: 'HyD', kind: 'hyd', qe_peak_pct: 60, user_gain: 1 }],
                selectionMap: {}
              },
              [broadFarRed],
              {}
            );
            const stedPoor = rt.simulateInstrument(
              instrument,
              {
                sources: [
                  { display_label: '640 laser', kind: 'laser', role: 'excitation', wavelength_nm: 640, spectral_mode: 'line' },
                  { display_label: '640 cw', kind: 'laser', role: 'depletion', wavelength_nm: 640, spectral_mode: 'line', timing_mode: 'cw', depletion_targets_nm: [561] }
                ],
                excitation: [{ component_type: 'passthrough' }],
                dichroic: [],
                emission: [{ component_type: 'bandpass', center_nm: 720, width_nm: 150 }],
                splitters: [],
                detectors: [{ id: 'hyd', display_label: 'HyD', kind: 'hyd', qe_peak_pct: 60, user_gain: 1 }],
                selectionMap: {}
              },
              [broadFarRed],
              {}
            );
            return {
              split: split.results,
              stedGood: stedGood.results[0],
              stedPoor: stedPoor.results[0]
            };
            """
        )

        split_rows = {(row["fluorophoreKey"], row["pathLabel"]): row for row in result["split"]}
        green_green = split_rows[("green", "Main Path -> Green path -> Camera")]
        green_red = split_rows[("green", "Main Path -> Red path -> Camera")]
        red_green = split_rows[("red", "Main Path -> Green path -> Camera")]
        red_red = split_rows[("red", "Main Path -> Red path -> Camera")]

        self.assertGreater(green_green["detectorWeightedIntensity"], green_red["detectorWeightedIntensity"])
        self.assertGreater(red_red["detectorWeightedIntensity"], red_green["detectorWeightedIntensity"])
        self.assertIn("bleedThrough", red_green)
        self.assertIn("crosstalkPct", red_green)

        self.assertEqual(result["stedGood"]["sted"]["label"], "good")
        self.assertEqual(result["stedPoor"]["sted"]["label"], "poor")
        self.assertGreater(result["stedGood"]["sted"]["score"], result["stedPoor"]["sted"]["score"])
        self.assertLess(result["stedGood"]["detectorWeightedIntensity"], result["stedPoor"]["detectorWeightedIntensity"])


if __name__ == "__main__":
    unittest.main()
