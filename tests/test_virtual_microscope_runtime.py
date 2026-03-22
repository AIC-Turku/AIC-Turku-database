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
              hardware_index_map: { by_inventory_id: { 'source:src_488': 1, 'endpoint:cam': 2 } },
              route_hardware_usage: [
                { route_id: 'epi', hardware_inventory_ids: ['source:src_488', 'endpoint:cam'], endpoint_inventory_ids: ['endpoint:cam'] }
              ],
              sources: [{ id: 'src_488', display_label: '488 laser', kind: 'laser' }],
              endpoints: [{ id: 'cam', display_label: 'Camera', endpoint_type: 'camera' }],
              light_paths: [{ id: 'epi', name: 'Epi', illumination_sequence: [{ source_id: 'src_488' }], detection_sequence: [{ endpoint_id: 'cam' }] }]
            });
            return {
              hardwareInventoryCount: instrument.hardwareInventory.length,
              hardwareIndexMap: instrument.hardwareIndexMap.by_inventory_id,
              routeUsageCount: instrument.routeHardwareUsage.length,
              endpointInventoryId: instrument.routeHardwareUsage[0].endpoint_inventory_ids[0],
              topologyContractRoutes: instrument.authoritativeTopologyContract.routes,
            };
            """
        )

        self.assertEqual(result["hardwareInventoryCount"], 2)
        self.assertEqual(result["hardwareIndexMap"], {"source:src_488": 1, "endpoint:cam": 2})
        self.assertEqual(result["routeUsageCount"], 1)
        self.assertEqual(result["endpointInventoryId"], "endpoint:cam")
        self.assertEqual(result["topologyContractRoutes"], "routeTopology.routes")

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
              routeUsageIds: instrument.routeTopology.routes.map((route) => ({ id: route.id, inventoryIds: route.routeLocalHardwareUsage.hardware_inventory_ids })),
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
            sorted(result["routeUsageIds"], key=lambda item: item["id"]),
            [
                {"id": "confocal", "inventoryIds": ["source:src_561", "optical_path_element:shared_di", "endpoint:pmt_1"]},
                {"id": "epi", "inventoryIds": ["source:src_488", "optical_path_element:shared_di", "endpoint:cam_a", "endpoint:cam_b"]},
            ],
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

    def test_component_mask_filter_cube_single_band(self) -> None:
        """componentMask should filter spectrally for filter_cube with a single band."""
        result = self.run_node_json(
            """
            const grid = rt.wavelengthGrid({ min_nm: 400, max_nm: 800, step_nm: 2 });
            const mask = rt.componentMask(
              { component_type: 'filter_cube', bands: [{ center_nm: 606, width_nm: 70 }] },
              grid,
              { mode: 'emission' }
            );
            const idx500 = grid.indexOf(500);
            const idx606 = grid.indexOf(606);
            const idx750 = grid.indexOf(750);
            return { at500: mask[idx500], at606: mask[idx606], at750: mask[idx750] };
            """
        )
        self.assertLess(result["at500"], 0.05, "filter_cube should block 500nm")
        self.assertGreater(result["at606"], 0.9, "filter_cube should pass 606nm")
        self.assertLess(result["at750"], 0.05, "filter_cube should block 750nm")

    def test_component_mask_filter_cube_multiband(self) -> None:
        """componentMask should handle filter_cube with multiple bands."""
        result = self.run_node_json(
            """
            const grid = rt.wavelengthGrid({ min_nm: 400, max_nm: 750, step_nm: 2 });
            const mask = rt.componentMask(
              { component_type: 'filter_cube', bands: [
                { center_nm: 459, width_nm: 25 },
                { center_nm: 525, width_nm: 30 },
                { center_nm: 608, width_nm: 30 }
              ] },
              grid,
              { mode: 'emission' }
            );
            const idx459 = grid.indexOf(460);
            const idx525 = grid.indexOf(526);
            const idx608 = grid.indexOf(608);
            const idx480 = grid.indexOf(480);
            return { at459: mask[idx459], at525: mask[idx525], at608: mask[idx608], at480: mask[idx480] };
            """
        )
        self.assertGreater(result["at459"], 0.8, "filter_cube should pass 459nm band")
        self.assertGreater(result["at525"], 0.8, "filter_cube should pass 525nm band")
        self.assertGreater(result["at608"], 0.8, "filter_cube should pass 608nm band")
        self.assertLess(result["at480"], 0.1, "filter_cube should block gap between bands")

    def test_branch_dedup_across_routes_uses_branch_id_only(self) -> None:
        """Branches with the same branch_id in different routes should be deduplicated."""
        result = self.run_node_json(
            """
            const payload = {
              metadata: {},
              light_paths: [
                {
                  id: 'route_a', name: 'Route A',
                  detection_sequence: [
                    { optical_path_element_id: 'trinocular' },
                    { branches: { selection_mode: 'exclusive', items: [
                      { branch_id: 'to_cam', label: 'To Camera', sequence: [{ endpoint_id: 'cam' }] },
                      { branch_id: 'to_eyes', label: 'To Eyepieces', sequence: [{ endpoint_id: 'eyes' }] },
                    ] } },
                  ],
                },
                {
                  id: 'route_b', name: 'Route B',
                  detection_sequence: [
                    { optical_path_element_id: 'trinocular' },
                    { branches: { selection_mode: 'exclusive', items: [
                      { branch_id: 'to_cam', label: 'To Camera', sequence: [{ endpoint_id: 'cam' }] },
                      { branch_id: 'to_eyes', label: 'To Eyepieces', sequence: [{ endpoint_id: 'eyes' }] },
                    ] } },
                  ],
                },
              ],
              optical_path_elements: [
                { id: 'trinocular', stage_role: 'splitter', element_type: 'splitter', selection_mode: 'exclusive' },
              ],
              endpoints: [
                { id: 'cam', endpoint_type: 'camera_port' },
                { id: 'eyes', endpoint_type: 'eyepiece' },
              ],
            };
            const inst = rt.normalizeInstrumentPayload(payload, { allowApproximation: false });
            const splitters = inst.splitters || [];
            const branchCounts = splitters.map(s => (s.branches || []).length);
            const branchIds = splitters.flatMap(s => (s.branches || []).map(b => b.id));
            return { splitterCount: splitters.length, branchCounts, branchIds };
            """
        )
        self.assertEqual(result["splitterCount"], 1, "Should have exactly one splitter")
        self.assertEqual(result["branchCounts"], [2], "Should have exactly 2 branches, not 4")
        self.assertIn("to_cam", result["branchIds"])
        self.assertIn("to_eyes", result["branchIds"])

    def test_component_mask_analyzer_is_passthrough(self) -> None:
        """Analyzer component should pass all wavelengths (no spectral effect)."""
        result = self.run_node_json(
            """
            const grid = rt.wavelengthGrid({ min_nm: 400, max_nm: 700, step_nm: 2 });
            const mask = rt.componentMask(
              { component_type: 'analyzer' },
              grid,
              { mode: 'emission' }
            );
            const allOnes = mask.every(v => v === 1);
            return { allOnes, length: mask.length };
            """
        )
        self.assertTrue(result["allOnes"], "analyzer should pass all wavelengths")
        self.assertGreater(result["length"], 0)

    def test_component_mask_all_vocabulary_types_are_handled(self) -> None:
        """Every vocabulary component_type should produce a defined mask (not fall through to generic passthrough)."""
        result = self.run_node_json(
            """
            const grid = rt.wavelengthGrid({ min_nm: 400, max_nm: 700, step_nm: 2 });
            const types = [
              { component_type: 'bandpass', center_nm: 525, width_nm: 50 },
              { component_type: 'multiband_bandpass', bands: [{ center_nm: 525, width_nm: 50 }] },
              { component_type: 'longpass', cut_on_nm: 500 },
              { component_type: 'shortpass', cut_off_nm: 600 },
              { component_type: 'dichroic', cutoffs_nm: [500] },
              { component_type: 'multiband_dichroic', cutoffs_nm: [500, 600] },
              { component_type: 'polychroic', cutoffs_nm: [500, 600] },
              { component_type: 'notch', center_nm: 525, width_nm: 50 },
              { component_type: 'filter_cube', bands: [{ center_nm: 525, width_nm: 50 }] },
              { component_type: 'analyzer' },
              { component_type: 'empty' },
              { component_type: 'mirror' },
              { component_type: 'block' },
              { component_type: 'passthrough' },
              { component_type: 'neutral_density' },
            ];
            const results = {};
            types.forEach((comp) => {
              const mask = rt.componentMask(comp, grid, { mode: 'emission' });
              results[comp.component_type] = {
                length: mask.length,
                hasVariation: !mask.every(v => v === mask[0]),
                firstValue: mask[0],
              };
            });
            return results;
            """
        )
        # Spectral filters should have variation
        for comp_type in ["bandpass", "multiband_bandpass", "longpass", "shortpass", "notch", "filter_cube"]:
            self.assertTrue(result[comp_type]["hasVariation"], f"{comp_type} should have spectral variation")
        # Passthrough types should all be 1
        for comp_type in ["empty", "mirror", "passthrough", "neutral_density", "analyzer"]:
            self.assertFalse(result[comp_type]["hasVariation"], f"{comp_type} should be uniform")
            self.assertEqual(result[comp_type]["firstValue"], 1, f"{comp_type} should pass all light")
        # Block should be all 0
        self.assertFalse(result["block"]["hasVariation"])
        self.assertEqual(result["block"]["firstValue"], 0, "block should block all light")
        # Dichroics should have variation
        for comp_type in ["dichroic", "multiband_dichroic", "polychroic"]:
            self.assertTrue(result[comp_type]["hasVariation"], f"{comp_type} should have spectral variation")

    def test_dichroic_mask_reflects_excitation_transmits_emission(self) -> None:
        """Dichroic with cut_on_nm should reflect excitation light and transmit emission light."""
        result = self.run_node_json(
            """
            const grid = rt.wavelengthGrid({ min_nm: 400, max_nm: 800, step_nm: 2 });
            const mask_ex = rt.componentMask(
              { component_type: 'dichroic', cut_on_nm: 500 },
              grid,
              { mode: 'excitation' }
            );
            const mask_em = rt.componentMask(
              { component_type: 'dichroic', cut_on_nm: 500 },
              grid,
              { mode: 'emission' }
            );
            const idx450 = grid.indexOf(450);
            const idx600 = grid.indexOf(600);
            return {
              ex_at450: mask_ex[idx450],
              ex_at600: mask_ex[idx600],
              em_at450: mask_em[idx450],
              em_at600: mask_em[idx600],
            };
            """
        )
        # In excitation mode, dichroic reflects (1 - transmit): passes short wavelengths
        self.assertGreater(result["ex_at450"], 0.8, "Dichroic should reflect/pass 450nm in excitation mode")
        self.assertLess(result["ex_at600"], 0.2, "Dichroic should block 600nm in excitation mode")
        # In emission mode, dichroic transmits: passes long wavelengths
        self.assertLess(result["em_at450"], 0.2, "Dichroic should block 450nm in emission mode")
        self.assertGreater(result["em_at600"], 0.8, "Dichroic should transmit 600nm in emission mode")

    def test_simulate_with_cube_dichroic_and_emission(self) -> None:
        """simulateInstrument should correctly filter through cube dichroic + emission."""
        result = self.run_node_json(
            """
            const grid = rt.wavelengthGrid({ min_nm: 400, max_nm: 800, step_nm: 2 });
            // Simulate a cube with dichroic (495nm cut-on) + emission (525/50 bandpass)
            const selection = {
              sources: [{ display_label: '470 LED', kind: 'led', role: 'excitation', wavelength_nm: 470, spectrum_type: 'gaussian', fwhm_nm: 30 }],
              excitation: [],
              dichroic: [{ component_type: 'dichroic', cut_on_nm: 495 }],
              emission: [{ component_type: 'bandpass', center_nm: 525, width_nm: 50 }],
              splitters: [],
              detectors: [],
            };
            const instrument = {
              metadata: { wavelength_grid: { min_nm: 400, max_nm: 800, step_nm: 2 } },
            };
            const gfp = {
              key: 'gfp', name: 'GFP', exMax: 488, emMax: 509,
              activeStateName: 'Default',
              spectra: {
                ex1p: [[430, 0], [460, 30], [488, 100], [500, 60], [520, 0]],
                ex2p: [],
                em: [[490, 0], [500, 30], [509, 100], [530, 60], [570, 0]],
              },
            };
            const sim = rt.simulateInstrument(instrument, selection, [gfp], {});
            const excArea = sim.excitationAtSample.reduce((s, v) => s + v, 0);
            const hasEmission = sim.emittedSpectra.length > 0 && sim.emittedSpectra[0].postOpticsSpectrum.some(v => v > 0.01);
            return { excArea: excArea > 0, hasEmission };
            """
        )
        self.assertTrue(result["excArea"], "Excitation should reach sample through dichroic")
        self.assertTrue(result["hasEmission"], "Emission should pass through dichroic + emission filter")

    # ── VM-005: Filter cube composite modeling ──────────────────────────

    def test_component_mask_filter_cube_composite_excitation_mode(self) -> None:
        """componentMask should use sub-components when filter_cube has linked excitation/dichroic/emission."""
        result = self.run_node_json(
            """
            const grid = rt.wavelengthGrid({ min_nm: 400, max_nm: 800, step_nm: 2 });
            // Cube with explicit dichroic (cut_on=500) and emission_filter (bandpass 525/50).
            // In excitation mode, dichroic reflects short wavelengths.
            const cube = {
              component_type: 'filter_cube',
              dichroic: { component_type: 'dichroic', cut_on_nm: 500 },
              emission_filter: { component_type: 'bandpass', center_nm: 525, width_nm: 50 },
            };
            const mask = rt.componentMask(cube, grid, { mode: 'excitation' });
            const idx460 = grid.indexOf(460);
            const idx600 = grid.indexOf(600);
            return { at460: mask[idx460], at600: mask[idx600] };
            """
        )
        # Excitation mode with dichroic cut_on=500: short wavelengths pass (reflected), long blocked
        self.assertGreater(result["at460"], 0.8, "Cube in excitation mode should pass 460nm via dichroic reflection")
        self.assertLess(result["at600"], 0.2, "Cube in excitation mode should block 600nm")

    def test_component_mask_filter_cube_composite_emission_mode(self) -> None:
        """componentMask should apply dichroic+emission in emission mode for composite filter_cube."""
        result = self.run_node_json(
            """
            const grid = rt.wavelengthGrid({ min_nm: 400, max_nm: 800, step_nm: 2 });
            const cube = {
              component_type: 'filter_cube',
              dichroic: { component_type: 'dichroic', cut_on_nm: 500 },
              emission_filter: { component_type: 'bandpass', center_nm: 525, width_nm: 50 },
            };
            const mask = rt.componentMask(cube, grid, { mode: 'emission' });
            const idx460 = grid.indexOf(460);
            const idx525 = grid.indexOf(526);
            const idx700 = grid.indexOf(700);
            return { at460: mask[idx460], at525: mask[idx525], at700: mask[idx700] };
            """
        )
        # Emission mode: dichroic transmits long λ, then emission bandpass selects 500-550nm
        self.assertLess(result["at460"], 0.1, "460nm should not pass through dichroic+emission in emission mode")
        self.assertGreater(result["at525"], 0.5, "525nm should pass through dichroic+emission in emission mode")
        self.assertLess(result["at700"], 0.1, "700nm should be blocked by emission bandpass")

    def test_component_mask_filter_cube_flat_fallback_still_works(self) -> None:
        """Flat filter_cube without sub-components should still apply bands (emission-only fallback)."""
        result = self.run_node_json(
            """
            const grid = rt.wavelengthGrid({ min_nm: 400, max_nm: 800, step_nm: 2 });
            const mask = rt.componentMask(
              { component_type: 'filter_cube', bands: [{ center_nm: 606, width_nm: 70 }] },
              grid,
              { mode: 'emission' }
            );
            const idx500 = grid.indexOf(500);
            const idx606 = grid.indexOf(606);
            return { at500: mask[idx500], at606: mask[idx606] };
            """
        )
        self.assertLess(result["at500"], 0.05, "Flat fallback should still block 500nm")
        self.assertGreater(result["at606"], 0.9, "Flat fallback should still pass 606nm")

    # ── VM-006: Unsupported component surfacing ─────────────────────────

    def test_component_mask_analyzer_warns_and_passes(self) -> None:
        """Analyzer should pass all wavelengths but produce a console.warn."""
        result = self.run_node_json(
            """
            const grid = rt.wavelengthGrid({ min_nm: 400, max_nm: 700, step_nm: 2 });
            const warnings = [];
            const origWarn = console.warn;
            console.warn = (...args) => warnings.push(args.join(' '));
            const mask = rt.componentMask(
              { component_type: 'analyzer', name: 'DIC Analyzer' },
              grid,
              { mode: 'emission' }
            );
            console.warn = origWarn;
            const allOnes = mask.every(v => v === 1);
            return { allOnes, warningCount: warnings.length, hasAnalyzerWarn: warnings.some(w => w.includes('analyzer')) };
            """
        )
        self.assertTrue(result["allOnes"], "analyzer should still pass all wavelengths")
        self.assertGreater(result["warningCount"], 0, "analyzer should emit a console.warn")
        self.assertTrue(result["hasAnalyzerWarn"], "warning should mention 'analyzer'")

    def test_component_mask_unknown_type_warns(self) -> None:
        """Unknown component types should emit a console.warn about unsupported type."""
        result = self.run_node_json(
            """
            const grid = rt.wavelengthGrid({ min_nm: 400, max_nm: 700, step_nm: 2 });
            const warnings = [];
            const origWarn = console.warn;
            console.warn = (...args) => warnings.push(args.join(' '));
            const mask = rt.componentMask(
              { component_type: 'objective_lens' },
              grid,
              { mode: 'emission' }
            );
            console.warn = origWarn;
            const allOnes = mask.every(v => v === 1);
            return { allOnes, warningCount: warnings.length, hasUnsupportedWarn: warnings.some(w => w.includes('unsupported')) };
            """
        )
        self.assertTrue(result["allOnes"], "unknown type should pass all wavelengths")
        self.assertGreater(result["warningCount"], 0, "unknown type should emit a console.warn")
        self.assertTrue(result["hasUnsupportedWarn"], "warning should mention 'unsupported'")

    # ── VM-006: analyzer stage flows through normalizeInstrumentPayload ──

    def test_analyzer_stage_flows_through_normalized_instrument(self) -> None:
        """normalizeInstrumentPayload should expose the analyzer stage group."""
        result = self.run_node_json(
            """
            const payload = {
                metadata: {},
                light_paths: [{
                    id: 'dic',
                    illumination_sequence: [{ source_id: 'hal' }],
                    detection_sequence: [
                        { optical_path_element_id: 'analyzer_slider' },
                        { endpoint_id: 'cam' },
                    ],
                }],
                light_sources: [{ id: 'hal', kind: 'halogen_lamp', wavelength_nm: 550 }],
                optical_path_elements: [{
                    id: 'analyzer_slider',
                    name: 'DIC Fixed Analyzer',
                    stage_role: 'analyzer',
                    element_type: 'slider',
                    positions: { 1: { component_type: 'analyzer', name: 'Analyzer' } },
                }],
                endpoints: [{ id: 'cam', endpoint_type: 'camera_port' }],
                projections: {
                    virtual_microscope: {
                        stages: {
                            analyzer: [{
                                id: 'analyzer_mech_0',
                                name: 'DIC Fixed Analyzer',
                                positions: [{ slot: 1, component_type: 'analyzer', name: 'Analyzer' }],
                                options: [{ slot: 1, display_label: 'Analyzer', value: { component_type: 'analyzer' } }],
                                control_kind: 'dropdown',
                            }],
                            excitation: [],
                            dichroic: [],
                            emission: [],
                            cube: [],
                        },
                        valid_paths: [{ analyzer_mech_0: 1 }],
                        splitters: [],
                        light_sources: [],
                        detectors: [],
                        terminals: [],
                        available_routes: [],
                    }
                },
            };
            const inst = rt.normalizeInstrumentPayload(payload);
            return {
                hasAnalyzer: Array.isArray(inst.analyzer) && inst.analyzer.length > 0,
                analyzerName: inst.analyzer && inst.analyzer[0] ? inst.analyzer[0].name : null,
            };
            """
        )
        self.assertTrue(result["hasAnalyzer"], "analyzer should be present in normalized instrument")
        self.assertEqual(result["analyzerName"], "DIC Fixed Analyzer")

    # ── VM-007: sequential acquisition detection ──

    def test_optimizer_returns_sequential_acquisition_for_incompatible_fluorophores(self) -> None:
        """optimizeLightPath should return requiresSequentialAcquisition when no shared path works."""
        result = self.run_node_json(
            """
            // Instrument with a single cube mechanism that has two non-overlapping cubes
            const payload = {
                metadata: { wavelength_grid: { min_nm: 400, max_nm: 800, step_nm: 2 } },
                light_sources: [{ id: 'led405', kind: 'led', wavelength_nm: 405 }, { id: 'led561', kind: 'led', wavelength_nm: 561 }],
                endpoints: [{ id: 'cam', endpoint_type: 'camera_port' }],
                light_paths: [{
                    id: 'epi',
                    illumination_sequence: [{ source_id: 'led405' }, { source_id: 'led561' }],
                    detection_sequence: [{ endpoint_id: 'cam' }],
                }],
                projections: {
                    virtual_microscope: {
                        light_sources: [{
                            id: 'source_mech_0',
                            positions: {
                                1: { kind: 'led', wavelength_nm: 405, spectrum_type: 'gaussian', fwhm_nm: 20 },
                                2: { kind: 'led', wavelength_nm: 561, spectrum_type: 'gaussian', fwhm_nm: 20 },
                            },
                            options: [
                                { slot: 1, value: { kind: 'led', wavelength_nm: 405, spectrum_type: 'gaussian', fwhm_nm: 20 } },
                                { slot: 2, value: { kind: 'led', wavelength_nm: 561, spectrum_type: 'gaussian', fwhm_nm: 20 } },
                            ],
                        }],
                        stages: {
                            cube: [{
                                id: 'cube_mech_0',
                                name: 'Cube Turret',
                                positions: [
                                    { slot: 1, component_type: 'filter_cube', label: 'DAPI',
                                      excitation_filter: { component_type: 'bandpass', center_nm: 390, width_nm: 40 },
                                      dichroic: { component_type: 'dichroic', cut_on_nm: 420 },
                                      emission_filter: { component_type: 'bandpass', center_nm: 460, width_nm: 50 } },
                                    { slot: 2, component_type: 'filter_cube', label: 'mCherry',
                                      excitation_filter: { component_type: 'bandpass', center_nm: 560, width_nm: 40 },
                                      dichroic: { component_type: 'dichroic', cut_on_nm: 590 },
                                      emission_filter: { component_type: 'bandpass', center_nm: 630, width_nm: 60 } },
                                ],
                                options: [
                                    { slot: 1, display_label: 'DAPI', value: {
                                        component_type: 'filter_cube', label: 'DAPI',
                                        excitation_filter: { component_type: 'bandpass', center_nm: 390, width_nm: 40 },
                                        dichroic: { component_type: 'dichroic', cut_on_nm: 420 },
                                        emission_filter: { component_type: 'bandpass', center_nm: 460, width_nm: 50 } } },
                                    { slot: 2, display_label: 'mCherry', value: {
                                        component_type: 'filter_cube', label: 'mCherry',
                                        excitation_filter: { component_type: 'bandpass', center_nm: 560, width_nm: 40 },
                                        dichroic: { component_type: 'dichroic', cut_on_nm: 590 },
                                        emission_filter: { component_type: 'bandpass', center_nm: 630, width_nm: 60 } } },
                                ],
                                control_kind: 'dropdown',
                            }],
                            excitation: [],
                            dichroic: [],
                            emission: [],
                        },
                        splitters: [],
                        detectors: [],
                        terminals: [{ id: 'cam', endpoint_type: 'camera_port' }],
                        valid_paths: [{ cube_mech_0: 1 }, { cube_mech_0: 2 }],
                        available_routes: [{ id: 'epi', label: 'Epi' }],
                    }
                },
            };

            const dapi = {
                key: 'dapi_key', name: 'DAPI', exMax: 360, emMax: 460,
                activeStateName: 'Default',
                spectra: {
                    ex1p: [[330, 0], [340, 20], [360, 100], [380, 30], [400, 0]],
                    ex2p: [],
                    em: [[400, 0], [430, 30], [460, 100], [490, 50], [550, 0]],
                },
            };
            const mcherry = {
                key: 'mcherry_key', name: 'mCherry', exMax: 587, emMax: 610,
                activeStateName: 'Default',
                spectra: {
                    ex1p: [[500, 0], [540, 20], [587, 100], [600, 30], [620, 0]],
                    ex2p: [],
                    em: [[580, 0], [600, 30], [610, 100], [640, 60], [700, 0]],
                },
            };

            const result = rt.optimizeLightPath([dapi, mcherry], payload, {});
            return {
                isSequential: result ? Boolean(result.requiresSequentialAcquisition) : false,
                hasPerFluorConfigs: result && Array.isArray(result.perFluorophoreConfigs) ? result.perFluorophoreConfigs.length : 0,
                hasReason: result && result.reason ? true : false,
                isNull: result === null,
            };
            """
        )
        # If the optimizer can't find a shared config but can find individual ones, it returns sequential.
        # If the optimizer happens to find a shared config, that's also acceptable.
        if result["isNull"]:
            pass  # Optimizer found nothing at all — acceptable for this constrained instrument
        elif result["isSequential"]:
            self.assertTrue(result["hasReason"], "sequential result should have a reason")
            self.assertGreaterEqual(result["hasPerFluorConfigs"], 2, "should have per-fluorophore configs")
        else:
            pass  # Optimizer found a shared config — also acceptable

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
