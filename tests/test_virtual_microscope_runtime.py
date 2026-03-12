import json
import shutil
import subprocess
import textwrap
import unittest
import urllib.error
import urllib.request
from pathlib import Path


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

    def test_source_spectrum_parses_multi_line_descriptors(self) -> None:
        result = self.run_node_json(
            """
            const grid = rt.wavelengthGrid({ min_nm: 380, max_nm: 760, step_nm: 2 });
            const spectrum = rt.sourceSpectrum({
              display_label: '395/25; 440/20; 475/28; 555/15; 640/30',
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
              centers: rt.sourceCenters({ display_label: '395/25; 440/20; 475/28; 555/15; 640/30' })
            };
            """
        )

        self.assertEqual(result["centers"], [395, 440, 475, 555, 640])
        bright_peaks = [entry for entry in result["peaks"] if entry["value"] >= 0.49]
        self.assertEqual(len(bright_peaks), 5)

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


    def test_detector_user_gain_no_longer_changes_output(self) -> None:
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
            const instrument = { metadata: { wavelength_grid: { min_nm: 450, max_nm: 650, step_nm: 2 } } };
            function simulate(userGain) {
              return rt.simulateInstrument(
                instrument,
                {
                  sources: [{ display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }],
                  excitation: [{ component_type: 'passthrough' }],
                  dichroic: [],
                  emission: [{ component_type: 'bandpass', center_nm: 525, width_nm: 50 }],
                  splitters: [],
                  detectors: [{ id: 'pmt', display_label: 'PMT', kind: 'pmt', qe_peak_pct: 30, user_gain: userGain }],
                  selectionMap: {}
                },
                [fluor],
                {}
              ).results[0];
            }
            const low = simulate(1);
            const high = simulate(25);
            return { low, high };
            """
        )

        self.assertAlmostEqual(result["low"]["detectorWeightedIntensity"], result["high"]["detectorWeightedIntensity"], places=9)
        self.assertAlmostEqual(result["low"]["planningScore"], result["high"]["planningScore"], places=9)

    def test_excitation_leakage_warning_tracks_detection_path_rejection(self) -> None:
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
            const instrument = { metadata: { wavelength_grid: { min_nm: 450, max_nm: 650, step_nm: 2 } } };
            function simulate(center, width) {
              return rt.simulateInstrument(
                instrument,
                {
                  sources: [{ display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }],
                  excitation: [{ component_type: 'passthrough' }],
                  dichroic: [],
                  emission: [{ component_type: 'bandpass', center_nm: center, width_nm: width }],
                  splitters: [],
                  detectors: [{
                    id: 'pmt',
                    display_label: 'PMT',
                    kind: 'pmt',
                    qe_peak_pct: 35,
                    collection_enabled: true,
                    collection_center_nm: center,
                    collection_width_nm: width
                  }],
                  selectionMap: {}
                },
                [fluor],
                {}
              );
            }
            const leaking = simulate(488, 20);
            const blocked = simulate(525, 40);
            return {
              leaking: leaking.results[0],
              blocked: blocked.results[0],
              leakingPath: leaking.pathSpectra[0],
              blockedPath: blocked.pathSpectra[0]
            };
            """
        )

        self.assertGreater(result["leaking"]["excitationLeakageWeightedIntensity"], result["blocked"]["excitationLeakageWeightedIntensity"])
        self.assertGreater(result["leaking"]["excitationLeakageThroughput"], result["blocked"]["excitationLeakageThroughput"])
        self.assertIn(result["leaking"]["excitationLeakageWarningLevel"], {"moderate", "high"})
        self.assertEqual(result["blocked"]["excitationLeakageWarningLevel"], "none")
        self.assertTrue(result["leaking"]["laserLeakageLikely"])
        self.assertFalse(result["blocked"]["laserLeakageLikely"])
        self.assertIn("488 laser", result["leaking"]["laserLeakageNote"])
        self.assertGreater(sum(result["leakingPath"]["excitationLeakageSpectrum"]), 0)
        self.assertLess(sum(result["blockedPath"]["excitationLeakageSpectrum"]), 1e-12)
        self.assertLess(result["leaking"]["planningScore"], result["blocked"]["planningScore"])

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
        self.assertIn(result["spectraSource"], {"api", "detail", "api+synthetic"})
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

    def test_point_detector_collection_window_changes_output(self) -> None:
        result = self.run_node_json(
            """
            const fluor = {
              key: 'red',
              name: 'Red',
              activeStateName: 'Default',
              spectra: {
                ex1p: [[560, 0], [600, 20], [640, 100], [670, 35], [700, 0]],
                ex2p: [],
                em: [[600, 0], [630, 25], [670, 100], [710, 60], [760, 0]]
              },
              exMax: 640,
              emMax: 670
            };
            const instrument = { metadata: { wavelength_grid: { min_nm: 550, max_nm: 800, step_nm: 2 } } };
            function simulate(center) {
              return rt.simulateInstrument(
                instrument,
                {
                  sources: [{ display_label: '640 laser', kind: 'laser', role: 'excitation', wavelength_nm: 640, spectral_mode: 'line' }],
                  excitation: [{ component_type: 'passthrough' }],
                  dichroic: [],
                  emission: [{ component_type: 'bandpass', center_nm: 690, width_nm: 140 }],
                  splitters: [],
                  detectors: [{ id: 'pmt', display_label: 'PMT', kind: 'pmt', user_gain: 1, collection_enabled: true, collection_center_nm: center, collection_width_nm: 30 }],
                  selectionMap: {}
                },
                [fluor],
                {}
              );
            }
            const onTarget = simulate(670);
            const offTarget = simulate(760);
            return {
              onTarget: onTarget.results[0].detectorWeightedIntensity,
              offTarget: offTarget.results[0].detectorWeightedIntensity,
              pathSpectra: onTarget.pathSpectra.length,
              maskDip: Math.min(...onTarget.pathSpectra[0].collectionMask)
            };
            """
        )

        self.assertGreater(result["onTarget"], result["offTarget"])
        self.assertGreater(result["pathSpectra"], 0)
        self.assertEqual(result["maskDip"], 0)

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


if __name__ == "__main__":
    unittest.main()
