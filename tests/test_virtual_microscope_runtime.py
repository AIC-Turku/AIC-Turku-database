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


    def test_explicit_multiband_dichroic_prefers_transmission_bands_for_emission(self) -> None:
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
                  em: [[emCenter - 25, 0], [emCenter - 10, 40], [emCenter, 100], [emCenter + 12, 50], [emCenter + 28, 0]]
                },
                exMax: 488,
                emMax: emCenter
              };
            }

            const instrument = { metadata: { wavelength_grid: { min_nm: 420, max_nm: 760, step_nm: 2 } } };
            const selection = {
              sources: [{ display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }],
              excitation: [{ component_type: 'passthrough' }],
              dichroic: [{
                component_type: 'multiband_dichroic',
                transmission_bands: [{ center_nm: 525, width_nm: 50 }],
                reflection_bands: [
                  { center_nm: 445, width_nm: 35 },
                  { center_nm: 488, width_nm: 30 },
                  { center_nm: 617, width_nm: 60 }
                ]
              }],
              emission: [{ component_type: 'passthrough' }],
              splitters: [],
              detectors: [{ id: 'cam', display_label: 'Camera', kind: 'camera', qe_peak_pct: 80, user_gain: 1 }],
              selectionMap: {}
            };

            const sim = rt.simulateInstrument(instrument, selection, [fluor('blue', 445), fluor('green', 525), fluor('red', 617)], {});
            return sim.results.map((row) => ({ key: row.fluorophoreKey, intensity: row.detectorWeightedIntensity, throughput: row.emissionPathThroughput }));
            """
        )

        rows = {entry["key"]: entry for entry in result}
        self.assertGreater(rows["green"]["throughput"], rows["blue"]["throughput"])
        self.assertGreater(rows["green"]["throughput"], rows["red"]["throughput"])
        self.assertGreater(rows["green"]["intensity"], rows["blue"]["intensity"])
        self.assertGreater(rows["green"]["intensity"], rows["red"]["intensity"])


    def test_csu_w1_green_channel_regression_explicit_bands_vs_legacy_cutoffs(self) -> None:
        result = self.run_node_json(
            """
            const green = {
              key: 'green',
              name: 'Green',
              activeStateName: 'Default',
              spectra: {
                ex1p: [[450, 0], [470, 30], [488, 100], [510, 20], [540, 0]],
                ex2p: [],
                em: [[500, 0], [515, 45], [525, 100], [540, 55], [560, 0]]
              },
              exMax: 488,
              emMax: 525
            };

            const instrument = { metadata: { wavelength_grid: { min_nm: 430, max_nm: 760, step_nm: 2 } } };
            function simulate(dichroic) {
              return rt.simulateInstrument(
                instrument,
                {
                  sources: [{ display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }],
                  excitation: [{ component_type: 'passthrough' }],
                  dichroic: [dichroic],
                  emission: [{ component_type: 'bandpass', center_nm: 525, width_nm: 30 }],
                  splitters: [],
                  detectors: [{ id: 'cam', display_label: 'Camera', kind: 'camera', qe_peak_pct: 80, user_gain: 1 }],
                  selectionMap: {}
                },
                [green],
                {}
              ).results[0];
            }

            const explicit = simulate({
              component_type: 'multiband_dichroic',
              transmission_bands: [{ center_nm: 521, width_nm: 25 }],
              reflection_bands: [{ center_nm: 488, width_nm: 20 }],
              cutoffs_nm: [405, 488, 568, 647]
            });
            const legacyOnly = simulate({ component_type: 'multiband_dichroic', cutoffs_nm: [405, 488, 568, 647] });
            return {
              explicitThroughput: explicit.emissionPathThroughput,
              explicitIntensity: explicit.detectorWeightedIntensity,
              legacyThroughput: legacyOnly.emissionPathThroughput,
              legacyIntensity: legacyOnly.detectorWeightedIntensity,
            };
            """
        )

        self.assertGreater(result["explicitThroughput"], 0.2)
        self.assertGreater(result["explicitIntensity"], result["legacyIntensity"])
        self.assertGreater(result["explicitThroughput"], result["legacyThroughput"])

    def test_single_cutoff_dichroic_with_single_cutoffs_entry_is_preserved(self) -> None:
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
                  em: [[emCenter - 20, 0], [emCenter - 8, 45], [emCenter, 100], [emCenter + 10, 40], [emCenter + 24, 0]]
                },
                exMax: 488,
                emMax: emCenter
              };
            }
            const instrument = { metadata: { wavelength_grid: { min_nm: 430, max_nm: 760, step_nm: 2 } } };
            const selection = {
              sources: [{ display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }],
              excitation: [{ component_type: 'passthrough' }],
              dichroic: [{ component_type: 'dichroic', cutoffs_nm: [560] }],
              emission: [{ component_type: 'passthrough' }],
              splitters: [],
              detectors: [{ id: 'cam', display_label: 'Camera', kind: 'camera', qe_peak_pct: 80, user_gain: 1 }],
              selectionMap: {}
            };
            const sim = rt.simulateInstrument(instrument, selection, [fluor('below', 525), fluor('above', 617)], {});
            return sim.results.map((row) => ({ key: row.fluorophoreKey, throughput: row.emissionPathThroughput }));
            """
        )

        rows = {entry["key"]: entry for entry in result}
        self.assertLess(rows["below"]["throughput"], rows["above"]["throughput"])

    def test_single_cutoff_dichroic_behavior_is_preserved(self) -> None:
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
                  em: [[emCenter - 20, 0], [emCenter - 8, 45], [emCenter, 100], [emCenter + 10, 40], [emCenter + 24, 0]]
                },
                exMax: 488,
                emMax: emCenter
              };
            }

            const instrument = { metadata: { wavelength_grid: { min_nm: 430, max_nm: 760, step_nm: 2 } } };
            const selection = {
              sources: [{ display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }],
              excitation: [{ component_type: 'passthrough' }],
              dichroic: [{ component_type: 'dichroic', cut_on_nm: 560 }],
              emission: [{ component_type: 'passthrough' }],
              splitters: [],
              detectors: [{ id: 'cam', display_label: 'Camera', kind: 'camera', qe_peak_pct: 80, user_gain: 1 }],
              selectionMap: {}
            };
            const sim = rt.simulateInstrument(instrument, selection, [fluor('below', 525), fluor('above', 617)], {});
            return sim.results.map((row) => ({ key: row.fluorophoreKey, throughput: row.emissionPathThroughput }));
            """
        )

        rows = {entry["key"]: entry for entry in result}
        self.assertLess(rows["below"]["throughput"], rows["above"]["throughput"])

    def test_migration_compatibility_legacy_multicutoff_dichroic_fallback_remains_available(self) -> None:
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
                  em: [[emCenter - 15, 0], [emCenter - 6, 40], [emCenter, 100], [emCenter + 7, 35], [emCenter + 18, 0]]
                },
                exMax: 488,
                emMax: emCenter
              };
            }

            const instrument = { metadata: { wavelength_grid: { min_nm: 430, max_nm: 760, step_nm: 2 } } };
            const selection = {
              sources: [{ display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }],
              excitation: [{ component_type: 'passthrough' }],
              dichroic: [{ component_type: 'multiband_dichroic', cutoffs_nm: [500, 550, 600, 650] }],
              emission: [{ component_type: 'passthrough' }],
              splitters: [],
              detectors: [{ id: 'cam', display_label: 'Camera', kind: 'camera', qe_peak_pct: 80, user_gain: 1 }],
              selectionMap: {}
            };
            const sim = rt.simulateInstrument(instrument, selection, [fluor('band1', 525), fluor('gap', 575), fluor('band2', 617)], {});
            return sim.results.map((row) => ({ key: row.fluorophoreKey, throughput: row.emissionPathThroughput }));
            """
        )

        rows = {entry["key"]: entry for entry in result}
        self.assertGreater(rows["band1"]["throughput"], rows["gap"]["throughput"])
        self.assertGreater(rows["band2"]["throughput"], rows["gap"]["throughput"])

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
                  { id: 'red', label: 'Red path', mode: 'transmitted', component: { component_type: 'bandpass', center_nm: 700, width_nm: 75 }, target_ids: ['cam'] },
                  { id: 'green', label: 'Green path', mode: 'reflected', component: { component_type: 'bandpass', center_nm: 525, width_nm: 50 }, target_ids: ['cam'] }
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

    def test_transmitted_light_sources_do_not_drive_fluorophore_excitation(self) -> None:
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
            function simulate(sources) {
              return rt.simulateInstrument(
                instrument,
                {
                  sources,
                  excitation: [{ component_type: 'passthrough' }],
                  dichroic: [],
                  emission: [{ component_type: 'bandpass', center_nm: 525, width_nm: 50 }],
                  splitters: [],
                  detectors: [{ id: 'cam', display_label: 'Camera', kind: 'camera', qe_peak_pct: 80 }],
                  selectionMap: {}
                },
                [fluor],
                {}
              ).results[0];
            }
            const excitationOnly = simulate([
              { display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }
            ]);
            const excitationPlusTransmitted = simulate([
              { display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' },
              { display_label: 'TL lamp', kind: 'led', role: 'transmitted_illumination', wavelength_nm: 488, spectral_mode: 'line' }
            ]);
            const transmittedOnly = simulate([
              { display_label: 'TL lamp', kind: 'led', role: 'transmitted_illumination', wavelength_nm: 488, spectral_mode: 'line' }
            ]);
            return {
              excitationOnly: excitationOnly.excitationStrength,
              excitationPlusTransmitted: excitationPlusTransmitted.excitationStrength,
              transmittedOnly: transmittedOnly.excitationStrength
            };
            """
        )

        self.assertAlmostEqual(result["excitationOnly"], result["excitationPlusTransmitted"], places=9)
        self.assertEqual(result["transmittedOnly"], 0)

    def test_migration_compatibility_instrument_route_catalog_is_normalized_from_legacy_payload(self) -> None:
        result = self.run_node_json(
            """
            const instrument = rt.normalizeInstrumentPayload({
              id: 'scope-1',
              available_routes: [
                { id: 'epi', label: 'Epi route' },
                { id: 'confocal', label: 'Confocal route' }
              ],
              default_route: 'epi',
              light_sources: [
                {
                  id: 'sources',
                  positions: [
                    { slot: 1, value: { display_label: '488 laser', path: 'confocal', wavelength_nm: 488, kind: 'laser' } },
                    { slot: 2, value: { display_label: 'LED', path: 'epi', wavelength_nm: 470, kind: 'led' } }
                  ]
                }
              ],
              detectors: [
                {
                  id: 'detectors',
                  positions: [
                    { slot: 1, value: { display_label: 'PMT', path: 'confocal', kind: 'pmt' } },
                    { slot: 2, value: { display_label: 'Camera', path: 'epi', kind: 'camera' } }
                  ]
                }
              ],
              stages: {
                excitation: [],
                cube: [],
                dichroic: [],
                emission: []
              },
              splitters: [],
              valid_paths: []
            });
            return {
              defaultRoute: instrument.defaultRoute,
              routeIds: instrument.routeOptions.map((entry) => entry.id),
              routeLabels: instrument.routeOptions.map((entry) => entry.label),
            };
            """
        )

        self.assertEqual(result["defaultRoute"], "epi")
        self.assertEqual(result["routeIds"], ["confocal", "epi"])
        self.assertEqual(result["routeLabels"], ["Confocal route", "Epi route"])

    def test_canonical_dto_is_authoritative_runtime_input(self) -> None:
        result = self.run_node_json(
            """
            const instrument = rt.normalizeInstrumentPayload({
              metadata: { simulation_mode: 'strict' },
              simulation: { default_route: 'epi' },
              sources: [
                { id: 'src_488', display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }
              ],
              optical_path_elements: [
                { id: 'ex_1', stage_role: 'excitation', element_type: 'filter_wheel', display_label: 'EX', component_type: 'bandpass', center_nm: 488, width_nm: 10 },
                { id: 'di_1', stage_role: 'dichroic', element_type: 'dichroic', display_label: 'DI', component_type: 'dichroic', cutoffs_nm: [505] },
                { id: 'em_1', stage_role: 'emission', element_type: 'filter_wheel', display_label: 'EM', component_type: 'bandpass', center_nm: 525, width_nm: 50 }
              ],
              endpoints: [
                { id: 'cam_1', display_label: 'Camera', endpoint_type: 'camera', qe_peak_pct: 82 }
              ],
              light_paths: [
                {
                  id: 'epi',
                  name: 'Epi route',
                  illumination_sequence: [
                    { source_id: 'src_488' },
                    { optical_path_element_id: 'ex_1' }
                  ],
                  detection_sequence: [
                    { optical_path_element_id: 'di_1' },
                    { optical_path_element_id: 'em_1' },
                    { endpoint_id: 'cam_1' }
                  ]
                }
              ],
              projections: {
                virtual_microscope: {
                  light_sources: [{ id: 'legacy_sources', positions: { 1: { display_label: 'Wrong 561', wavelength_nm: 561, kind: 'laser' } } }],
                  stages: {
                    excitation: [{ id: 'legacy_ex', positions: { 1: { component_type: 'bandpass', center_nm: 561, width_nm: 10 } } }],
                    dichroic: [],
                    emission: [],
                    cube: []
                  },
                  splitters: []
                }
              }
            });
            return {
              defaultRoute: instrument.defaultRoute,
              routeIds: instrument.routeOptions.map((entry) => entry.id),
              topologyRouteIds: instrument.routeTopology.routes.map((route) => route.id),
              sourceLabels: instrument.lightSources.flatMap((mechanism) => Object.values(mechanism.positions || {}).map((value) => value.display_label)),
              stageAdapterSourceLabels: instrument.stageAdapters.lightSources.flatMap((mechanism) => Object.values(mechanism.positions || {}).map((value) => value.display_label)),
              excitationLabels: instrument.excitation.map((mechanism) => mechanism.display_label || mechanism.name),
              detectorLabels: instrument.detectors.flatMap((mechanism) => Object.values(mechanism.positions || {}).map((value) => value.display_label)),
            };
            """
        )

        self.assertEqual(result["defaultRoute"], "epi")
        self.assertEqual(result["routeIds"], ["epi"])
        self.assertEqual(result["topologyRouteIds"], ["epi"])
        self.assertEqual(result["sourceLabels"], ["488 laser"])
        self.assertEqual(result["stageAdapterSourceLabels"], ["488 laser"])
        self.assertEqual(result["excitationLabels"], ["EX"])
        self.assertEqual(result["detectorLabels"], ["Camera"])

    def test_reused_canonical_optical_path_element_keeps_route_bindings_when_seen_in_both_sequences(self) -> None:
        result = self.run_node_json(
            """
            const instrument = rt.normalizeInstrumentPayload({
              metadata: { simulation_mode: 'strict' },
              sources: [{ id: 'src_488', display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }],
              optical_path_elements: [
                { id: 'shared_di', stage_role: 'dichroic', element_type: 'dichroic', display_label: 'Main DI', component_type: 'dichroic', cutoffs_nm: [505] }
              ],
              endpoints: [{ id: 'cam_1', display_label: 'Camera', endpoint_type: 'camera' }],
              light_paths: [
                {
                  id: 'epi',
                  name: 'Epi route',
                  illumination_sequence: [
                    { source_id: 'src_488' },
                    { optical_path_element_id: 'shared_di' }
                  ],
                  detection_sequence: [
                    { optical_path_element_id: 'shared_di' },
                    { endpoint_id: 'cam_1' }
                  ]
                }
              ]
            });
            const mechanism = instrument.dichroic[0];
            return {
              routeIds: instrument.routeOptions.map((entry) => entry.id),
              mechanismRoutes: mechanism.__routes,
              illumRefs: mechanism.__sequence_use.illumination.length,
              detectRefs: mechanism.__sequence_use.detection.length,
            };
            """
        )

        self.assertEqual(result["routeIds"], ["epi"])
        self.assertEqual(result["mechanismRoutes"], ["epi"])
        self.assertEqual(result["illumRefs"], 1)
        self.assertEqual(result["detectRefs"], 1)

    def test_canonical_branch_blocks_drive_runtime_splitters_and_branch_endpoints(self) -> None:
        result = self.run_node_json(
            """
            const instrument = rt.normalizeInstrumentPayload({
              metadata: { simulation_mode: 'strict' },
              simulation: { default_route: 'epi' },
              sources: [{ id: 'src_488', display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }],
              optical_path_elements: [
                { id: 'main_splitter', stage_role: 'splitter', element_type: 'splitter', display_label: 'Main splitter', selection_mode: 'exclusive' },
                { id: 'green_filter', stage_role: 'emission', element_type: 'filter_wheel', display_label: 'Green filter', component: { component_type: 'bandpass', center_nm: 525, width_nm: 50 } },
              ],
              endpoints: [
                { id: 'cam', display_label: 'Camera', endpoint_type: 'camera' },
                { id: 'eye', display_label: 'Eyepieces', endpoint_type: 'eyepiece' },
              ],
              light_paths: [
                {
                  id: 'epi',
                  name: 'Epi route',
                  illumination_sequence: [{ source_id: 'src_488' }],
                  detection_sequence: [
                    { optical_path_element_id: 'main_splitter' },
                    { branches: {
                      selection_mode: 'exclusive',
                      items: [
                        { branch_id: 'camera_route', label: 'To camera', sequence: [{ optical_path_element_id: 'green_filter' }, { endpoint_id: 'cam' }] },
                        { branch_id: 'eyepiece_route', label: 'To eyepieces', sequence: [{ endpoint_id: 'eye' }] }
                      ]
                    } }
                  ]
                }
              ]
            });
            return {
              splitterCount: instrument.splitters.length,
              topologyBranchBlockCount: instrument.routeTopology.routes[0].branchBlocks.length,
              branchIds: instrument.splitters[0].branches.map((branch) => branch.id),
              branchTargets: instrument.splitters[0].branches.map((branch) => branch.target_ids.join(',')),
              branchSequenceKinds: instrument.splitters[0].branches[0].sequence.map((step) => Object.keys(step)[0]),
              endpointRoutes: instrument.terminals.map((terminal) => ({ id: terminal.id, routes: terminal.__routes })),
            };
            """
        )

        self.assertEqual(result["splitterCount"], 1)
        self.assertEqual(result["topologyBranchBlockCount"], 1)
        self.assertEqual(result["branchIds"], ["camera_route", "eyepiece_route"])
        self.assertEqual(result["branchTargets"], ["cam", "eye"])
        self.assertEqual(result["branchSequenceKinds"], ["optical_path_element_id", "endpoint_id"])
        self.assertEqual(result["endpointRoutes"], [{"id": "cam", "routes": ["epi"]}, {"id": "eye", "routes": ["epi"]}])

    def test_runtime_keeps_authoritative_inventory_and_route_usage_from_dto(self) -> None:
        result = self.run_node_json(
            """
            const instrument = rt.normalizeInstrumentPayload({
              metadata: { simulation_mode: 'strict' },
              hardware_inventory: [
                { id: 'source:src_488', display_number: 1, display_label: '488 laser' },
                { id: 'endpoint:cam', display_number: 2, display_label: 'Camera' }
              ],
              route_hardware_usage: [
                { route_id: 'epi', hardware_inventory_ids: ['source:src_488', 'endpoint:cam'], endpoint_inventory_ids: ['endpoint:cam'] }
              ],
              sources: [{ id: 'src_488', display_label: '488 laser', kind: 'laser' }],
              endpoints: [{ id: 'cam', display_label: 'Camera', endpoint_type: 'camera' }],
              light_paths: [{ id: 'epi', name: 'Epi', illumination_sequence: [{ source_id: 'src_488' }], detection_sequence: [{ endpoint_id: 'cam' }] }]
            });
            return {
              hardwareInventoryCount: instrument.hardwareInventory.length,
              routeUsageCount: instrument.routeHardwareUsage.length,
              endpointInventoryId: instrument.routeHardwareUsage[0].endpoint_inventory_ids[0],
            };
            """
        )

        self.assertEqual(result["hardwareInventoryCount"], 2)
        self.assertEqual(result["routeUsageCount"], 1)
        self.assertEqual(result["endpointInventoryId"], "endpoint:cam")

    def test_route_topology_keeps_one_graph_per_route_and_multi_detector_bindings(self) -> None:
        result = self.run_node_json(
            """
            const instrument = rt.normalizeInstrumentPayload({
              metadata: { simulation_mode: 'strict' },
              simulation: { default_route: 'epi' },
              hardware_inventory: [
                { id: 'source:src_488', display_number: 1, display_label: '488 laser' },
                { id: 'source:src_561', display_number: 2, display_label: '561 laser' },
                { id: 'optical_path_element:shared_di', display_number: 3, display_label: 'Shared DI' },
                { id: 'endpoint:cam_a', display_number: 4, display_label: 'Camera A' },
                { id: 'endpoint:cam_b', display_number: 5, display_label: 'Camera B' },
                { id: 'endpoint:pmt_1', display_number: 6, display_label: 'PMT 1' }
              ],
              route_hardware_usage: [
                { route_id: 'epi', hardware_inventory_ids: ['source:src_488', 'optical_path_element:shared_di', 'endpoint:cam_a', 'endpoint:cam_b'], endpoint_inventory_ids: ['endpoint:cam_a', 'endpoint:cam_b'] },
                { route_id: 'confocal', hardware_inventory_ids: ['source:src_561', 'optical_path_element:shared_di', 'endpoint:pmt_1'], endpoint_inventory_ids: ['endpoint:pmt_1'] }
              ],
              sources: [
                { id: 'src_488', display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' },
                { id: 'src_561', display_label: '561 laser', kind: 'laser', role: 'excitation', wavelength_nm: 561, spectral_mode: 'line' }
              ],
              optical_path_elements: [
                { id: 'shared_di', stage_role: 'dichroic', element_type: 'dichroic', display_label: 'Shared DI' },
                { id: 'epi_splitter', stage_role: 'splitter', element_type: 'splitter', display_label: 'Epi splitter', selection_mode: 'exclusive' }
              ],
              endpoints: [
                { id: 'cam_a', display_label: 'Camera A', endpoint_type: 'camera' },
                { id: 'cam_b', display_label: 'Camera B', endpoint_type: 'camera' },
                { id: 'pmt_1', display_label: 'PMT 1', endpoint_type: 'detector' }
              ],
              light_paths: [
                {
                  id: 'epi',
                  name: 'Epi route',
                  graph_nodes: [
                    { id: 'epi_src', hardware_inventory_id: 'source:src_488', label: '488 laser', component_kind: 'source', inventory_display_number: 1, column: 0, lane: 0 },
                    { id: 'epi_di', hardware_inventory_id: 'optical_path_element:shared_di', label: 'Shared DI', component_kind: 'optical_path_element', inventory_display_number: 3, column: 1, lane: 0 },
                    { id: 'epi_split', label: 'Epi splitter', component_kind: 'optical_path_element', column: 2, lane: 0 },
                    { id: 'epi_cam_a', hardware_inventory_id: 'endpoint:cam_a', label: 'Camera A', component_kind: 'endpoint', inventory_display_number: 4, column: 3, lane: 0 },
                    { id: 'epi_cam_b', hardware_inventory_id: 'endpoint:cam_b', label: 'Camera B', component_kind: 'endpoint', inventory_display_number: 5, column: 3, lane: 1 }
                  ],
                  graph_edges: [
                    { source: 'epi_src', target: 'epi_di' },
                    { source: 'epi_di', target: 'epi_split' },
                    { source: 'epi_split', target: 'epi_cam_a', branch_id: 'cam_a_branch' },
                    { source: 'epi_split', target: 'epi_cam_b', branch_id: 'cam_b_branch' }
                  ],
                  illumination_sequence: [{ source_id: 'src_488' }],
                  detection_sequence: [
                    { optical_path_element_id: 'shared_di' },
                    { optical_path_element_id: 'epi_splitter' },
                    { branches: { selection_mode: 'exclusive', items: [
                      { branch_id: 'cam_a_branch', sequence: [{ endpoint_id: 'cam_a' }] },
                      { branch_id: 'cam_b_branch', sequence: [{ endpoint_id: 'cam_b' }] }
                    ] } }
                  ]
                },
                {
                  id: 'confocal',
                  name: 'Confocal route',
                  graph_nodes: [
                    { id: 'conf_src', hardware_inventory_id: 'source:src_561', label: '561 laser', component_kind: 'source', inventory_display_number: 2, column: 0, lane: 0 },
                    { id: 'conf_di', hardware_inventory_id: 'optical_path_element:shared_di', label: 'Shared DI', component_kind: 'optical_path_element', inventory_display_number: 3, column: 1, lane: 0 },
                    { id: 'conf_pmt', hardware_inventory_id: 'endpoint:pmt_1', label: 'PMT 1', component_kind: 'endpoint', inventory_display_number: 6, column: 2, lane: 0 }
                  ],
                  graph_edges: [
                    { source: 'conf_src', target: 'conf_di' },
                    { source: 'conf_di', target: 'conf_pmt' }
                  ],
                  illumination_sequence: [{ source_id: 'src_561' }],
                  detection_sequence: [{ optical_path_element_id: 'shared_di' }, { endpoint_id: 'pmt_1' }]
                }
              ]
            });
            return {
              routeIds: instrument.routeTopology.routes.map((route) => route.id),
              graphSizes: instrument.routeTopology.routes.map((route) => ({ id: route.id, nodes: route.graphNodes.length, edges: route.graphEdges.length })),
              branchCounts: instrument.routeTopology.routes.map((route) => ({ id: route.id, branches: route.branchBlocks.length })),
              terminalRoutes: instrument.terminals.map((terminal) => ({ id: terminal.id, routes: terminal.__routes })),
              detectorRoutes: instrument.detectors.map((mechanism) => ({ id: mechanism.id, routes: mechanism.__routes })),
            };
            """
        )

        self.assertEqual(sorted(result["routeIds"]), ["confocal", "epi"])
        self.assertEqual(
            sorted(result["graphSizes"], key=lambda item: item["id"]),
            [{"id": "confocal", "nodes": 3, "edges": 2}, {"id": "epi", "nodes": 5, "edges": 4}],
        )
        self.assertEqual(
            sorted(result["branchCounts"], key=lambda item: item["id"]),
            [{"id": "confocal", "branches": 0}, {"id": "epi", "branches": 1}],
        )
        self.assertEqual(
            sorted(result["terminalRoutes"], key=lambda item: item["id"]),
            [
                {"id": "cam_a", "routes": ["epi"]},
                {"id": "cam_b", "routes": ["epi"]},
                {"id": "pmt_1", "routes": ["confocal"]},
            ],
        )
        detector_routes = {item["id"]: item["routes"] for item in result["detectorRoutes"]}
        self.assertEqual(detector_routes["terminal_mechanism_cam_a"], ["epi"])
        self.assertEqual(detector_routes["terminal_mechanism_cam_b"], ["epi"])
        self.assertEqual(detector_routes["terminal_mechanism_pmt_1"], ["confocal"])

    def test_migration_compatibility_strict_mode_does_not_fallback_route_catalog_from_component_tags(self) -> None:
        result = self.run_node_json(
            """
            const instrument = rt.normalizeInstrumentPayload({
              metadata: { simulation_mode: 'strict' },
              light_sources: [
                {
                  id: 'sources',
                  positions: {
                    1: { display_label: '488 laser', path: 'confocal', wavelength_nm: 488, kind: 'laser' }
                  }
                }
              ],
              detectors: [],
              stages: { excitation: [], cube: [], dichroic: [], emission: [] },
              splitters: [],
              valid_paths: []
            });
            return {
              defaultRoute: instrument.defaultRoute,
              routeIds: instrument.routeOptions.map((entry) => entry.id),
              strictHardwareTruth: instrument.strictHardwareTruth,
            };
            """
        )

        self.assertTrue(result["strictHardwareTruth"])
        self.assertEqual(result["routeIds"], [])
        self.assertIsNone(result["defaultRoute"])

    def test_migration_compatibility_approximation_mode_keeps_route_catalog_fallback(self) -> None:
        result = self.run_node_json(
            """
            const instrument = rt.normalizeInstrumentPayload({
              metadata: { simulation_mode: 'approximate' },
              light_sources: [
                {
                  id: 'sources',
                  positions: {
                    1: { display_label: '488 laser', path: 'confocal', wavelength_nm: 488, kind: 'laser' },
                    2: { display_label: '470 LED', path: 'epi', wavelength_nm: 470, kind: 'led' }
                  }
                }
              ],
              detectors: [],
              stages: { excitation: [], cube: [], dichroic: [], emission: [] },
              splitters: [],
              valid_paths: []
            });
            return {
              routeIds: instrument.routeOptions.map((entry) => entry.id),
              defaultRoute: instrument.defaultRoute,
              strictHardwareTruth: instrument.strictHardwareTruth,
            };
            """
        )

        self.assertFalse(result["strictHardwareTruth"])
        self.assertEqual(result["routeIds"], ["confocal", "epi"])
        self.assertEqual(result["defaultRoute"], "confocal")

    def test_strict_mode_does_not_invent_virtual_detectors(self) -> None:
        result = self.run_node_json(
            """
            const fluor = {
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
            const instrument = { metadata: { simulation_mode: 'strict', wavelength_grid: { min_nm: 450, max_nm: 650, step_nm: 2 } } };
            const simulation = rt.simulateInstrument(
              instrument,
              {
                sources: [{ display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }],
                excitation: [{ component_type: 'passthrough' }],
                dichroic: [],
                emission: [{ component_type: 'bandpass', center_nm: 520, width_nm: 50 }],
                splitters: [],
                detectors: [],
                selectionMap: {}
              },
              [fluor],
              {}
            );
            return {
              selectedDetectors: simulation.selectedDetectors,
              resultsCount: simulation.results.length,
            };
            """
        )

        self.assertEqual(result["selectedDetectors"], [])
        self.assertEqual(result["resultsCount"], 0)

    def test_strict_mode_requires_explicit_splitter_target_ids(self) -> None:
        result = self.run_node_json(
            """
            const fluor = {
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
            const instrument = { metadata: { simulation_mode: 'strict', wavelength_grid: { min_nm: 450, max_nm: 650, step_nm: 2 } } };
            function simulateWithTargets(target_ids) {
              return rt.simulateInstrument(
                instrument,
                {
                  sources: [{ display_label: '488 laser', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }],
                  excitation: [{ component_type: 'passthrough' }],
                  dichroic: [],
                  emission: [{ component_type: 'bandpass', center_nm: 520, width_nm: 50 }],
                  splitters: [
                    {
                      id: 'split',
                      branches: [
                        { id: 'branch_1', label: 'Branch 1', component: { component_type: 'passthrough' }, target_ids }
                      ]
                    }
                  ],
                  detectors: [{ id: 'cam', display_label: 'Camera', kind: 'camera' }],
                  selectionMap: {}
                },
                [fluor],
                {}
              );
            }
            const missingTargets = simulateWithTargets([]);
            const explicitTargets = simulateWithTargets(['cam']);
            return {
              missingCount: missingTargets.results.length,
              explicitCount: explicitTargets.results.length,
            };
            """
        )

        self.assertEqual(result["missingCount"], 0)
        self.assertGreater(result["explicitCount"], 0)

    def test_route_validation_rejects_wrong_route_stage_optics(self) -> None:
        result = self.run_node_json(
            """
            const fluor = {
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
            const instrument = {
              metadata: { simulation_mode: 'strict', wavelength_grid: { min_nm: 450, max_nm: 650, step_nm: 2 } },
              default_route: 'confocal',
              available_routes: [{ id: 'confocal', label: 'Confocal' }, { id: 'epi', label: 'Epi' }]
            };
            const simulation = rt.simulateInstrument(
              instrument,
              {
                sources: [{ display_label: 'Confocal Laser', path: 'confocal', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' }],
                excitation: [{ id: 'epi-ex', display_label: 'Epi EX', path: 'epi', component_type: 'passthrough' }],
                dichroic: [{ id: 'epi-di', display_label: 'Epi DI', path: 'epi', component_type: 'passthrough' }],
                emission: [{ id: 'epi-em', display_label: 'Epi EM', path: 'epi', component_type: 'passthrough' }],
                splitters: [],
                detectors: [{ id: 'confocal-pmt', display_label: 'Confocal PMT', path: 'confocal', kind: 'pmt' }],
                selectionMap: {}
              },
              [fluor],
              { currentRoute: 'confocal' }
            );
            return {
              validSelection: simulation.validSelection,
              routeViolation: simulation.routeViolation,
              routeViolationDetails: simulation.routeViolationDetails,
              resultsCount: simulation.results.length,
              crosstalkKeys: Object.keys(simulation.crosstalkMatrix || {}).length,
            };
            """
        )

        self.assertFalse(result["validSelection"])
        self.assertTrue(result["routeViolation"])
        details = " ".join(result["routeViolationDetails"])
        self.assertIn("Excitation component Epi EX is not on route confocal.", details)
        self.assertIn("Dichroic Epi DI is not on route confocal.", details)
        self.assertIn("Emission component Epi EM is not on route confocal.", details)
        self.assertEqual(result["resultsCount"], 0)
        self.assertEqual(result["crosstalkKeys"], 0)

    def test_optimizer_current_route_stays_strict(self) -> None:
        result = self.run_node_json(
            """
            const fluor = {
              key: 'green',
              name: 'Green',
              activeStateName: 'Default',
              spectra: { ex1p: [[450, 0], [488, 100], [530, 0]], ex2p: [], em: [[500, 0], [520, 100], [560, 0]] },
              exMax: 488,
              emMax: 520
            };
            const instrument = {
              available_routes: [{ id: 'confocal', label: 'Confocal' }, { id: 'epi', label: 'Epi' }],
              default_route: 'epi',
              light_sources: [{
                id: 'sources',
                positions: {
                  1: { slot: 1, display_label: 'Confocal 488', path: 'confocal', kind: 'laser', wavelength_nm: 488 },
                  2: { slot: 2, display_label: 'Epi 488', path: 'epi', kind: 'laser', wavelength_nm: 488 }
                }
              }],
              detectors: [{
                id: 'detectors',
                positions: {
                  1: { slot: 1, display_label: 'Confocal PMT', path: 'confocal', kind: 'pmt' },
                  2: { slot: 2, display_label: 'Epi Camera', path: 'epi', kind: 'camera' }
                }
              }],
              stages: { excitation: [], cube: [], dichroic: [], emission: [] },
              splitters: [],
              valid_paths: []
            };
            const optimized = rt.optimizeLightPath([fluor], instrument, { currentRoute: 'confocal' });
            return optimized;
            """
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["route"], "confocal")

    def test_pairwise_crosstalk_annotations_are_added_to_rows(self) -> None:
        result = self.run_node_json(
            """
            function fluor(key, exMax, emMax, ex, em) {
              return { key, name: key, activeStateName: 'Default', spectra: { ex1p: ex, ex2p: [], em }, exMax, emMax };
            }
            const green = fluor('green', 488, 520, [[450, 0], [488, 100], [540, 0]], [[500, 0], [520, 100], [560, 0]]);
            const red = fluor('red', 561, 600, [[530, 0], [561, 100], [600, 0]], [[580, 0], [600, 100], [650, 0]]);
            const simulation = rt.simulateInstrument(
              { metadata: { wavelength_grid: { min_nm: 450, max_nm: 700, step_nm: 2 } } },
              {
                sources: [
                  { display_label: '488', kind: 'laser', role: 'excitation', wavelength_nm: 488, spectral_mode: 'line' },
                  { display_label: '561', kind: 'laser', role: 'excitation', wavelength_nm: 561, spectral_mode: 'line' }
                ],
                excitation: [{ component_type: 'passthrough' }],
                dichroic: [],
                emission: [{ component_type: 'passthrough' }],
                splitters: [],
                detectors: [{ id: 'cam', display_label: 'Camera', kind: 'camera' }],
                selectionMap: {}
              },
              [green, red],
              {}
            );
            return {
              hasPairwise: simulation.results.every((row) => typeof row.pairwiseCrosstalkPct === 'number'),
              hasLegacyAlias: simulation.results.every((row) => typeof row.crosstalkPct === 'number'),
            };
            """
        )

        self.assertTrue(result["hasPairwise"])
        self.assertTrue(result["hasLegacyAlias"])

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
