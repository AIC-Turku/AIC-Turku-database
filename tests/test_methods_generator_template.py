import json
import re
import shutil
import subprocess
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = REPO_ROOT / "scripts" / "templates" / "methods_generator.md.j2"


class MethodsGeneratorTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("node") is None:
            raise unittest.SkipTest("Node.js is required for methods generator template tests.")
        content = TEMPLATE_PATH.read_text(encoding="utf-8")
        scripts = re.findall(r"<script(?: [^>]*)?>(.*?)</script>", content, flags=re.S)
        if not scripts:
            raise unittest.SkipTest("Methods generator template does not contain a script block.")
        cls.script_source = scripts[-1]

    def run_template(self, *, instruments=None, config=None, fetch_mode="ok", actions_js="return {};") -> object:
        instrument_payload = instruments if instruments is not None else []
        config_payload = config if config is not None else {
            "acknowledgements": {
                "standard": "Standard acknowledgement.",
                "xcelligence_addition": "xCELL acknowledgement.",
            },
            "output_title": "Light Microscopy Methods",
            "instrument_data_url": "../assets/instruments_data.json",
        }
        script = textwrap.dedent(
            f"""
            const scriptSource = {json.dumps(self.script_source)};
            const instrumentPayload = {json.dumps(instrument_payload)};
            const configText = {json.dumps(json.dumps(config_payload))};
            const fetchMode = {json.dumps(fetch_mode)};
            const state = {{ inputs: [] }};

            function createElement(id = '', tagName = 'div') {{
              return {{
                id,
                tagName: String(tagName || 'div').toUpperCase(),
                value: '',
                textContent: '',
                innerText: '',
                innerHTML: '',
                style: {{}},
                disabled: false,
                checked: false,
                dataset: {{}},
                children: [],
                options: [],
                listeners: {{}},
                appendChild(child) {{
                  this.children.push(child);
                  if (child && child.tagName === 'OPTION') this.options.push(child);
                  registerInputs(child);
                  return child;
                }},
                addEventListener(name, fn) {{
                  this.listeners[name] = fn;
                }},
                setSelectionRange() {{}},
                select() {{}},
              }};
            }}

            function registerInputs(node) {{
              if (!node || typeof node !== 'object') return;
              if (node.tagName === 'INPUT' && !state.inputs.includes(node)) {{
                state.inputs.push(node);
              }}
              if (Array.isArray(node.children)) {{
                node.children.forEach(registerInputs);
              }}
            }}

            const elements = new Map();
            function ensureElement(id, tagName = 'div') {{
              if (!elements.has(id)) elements.set(id, createElement(id, tagName));
              return elements.get(id);
            }}

            const requiredIds = [
              'methods-generator-config',
              'system-select',
              'hardware-options',
              'output-text',
              'copy-btn',
              'clear-btn',
              'add-btn',
              'copy-feedback',
              'methods-metadata-warning',
              'methods-metadata-blockers',
              'section-modality',
              'section-module',
              'section-scanner',
              'section-obj',
              'section-light',
              'section-filter',
              'section-splitter',
              'section-det',
              'section-magnification-changer',
              'section-optical-modulator',
              'section-illumination-logic',
              'modality-list',
              'module-list',
              'scanner-list',
              'obj-list',
              'light-list',
              'det-list',
              'magnification-changer-list',
              'optical-modulator-list',
              'illumination-logic-list',
              'filter-list',
              'splitter-list',
            ];
            requiredIds.forEach((id) => ensureElement(id, id === 'system-select' ? 'select' : id === 'output-text' ? 'textarea' : 'div'));
            ensureElement('add-btn', 'button');
            ensureElement('copy-btn', 'button');
            ensureElement('clear-btn', 'button');
            ensureElement('copy-feedback', 'span');
            ensureElement('methods-generator-config', 'script').textContent = configText;

            const document = {{
              listeners: {{}},
              addEventListener(name, fn) {{
                this.listeners[name] = fn;
              }},
              getElementById(id) {{
                return ensureElement(id);
              }},
              createElement(tagName) {{
                const node = createElement('', tagName);
                if (node.tagName === 'INPUT') state.inputs.push(node);
                return node;
              }},
              querySelectorAll(selector) {{
                const match = selector.match(/^input\\[id\\^="([^"]+)"\\]:checked$/);
                if (!match) return [];
                const prefix = match[1];
                return state.inputs.filter((input) => input && typeof input.id === 'string' && input.id.startsWith(prefix) && input.checked);
              }},
            }};

            globalThis.document = document;
            globalThis.window = globalThis;
            globalThis.navigator = {{ clipboard: {{ writeText: async () => undefined }} }};
            globalThis.setTimeout = (fn) => {{ if (typeof fn === 'function') fn(); return 0; }};
            globalThis.fetch = async () => {{
              if (fetchMode === 'reject') throw new Error('network down');
              if (fetchMode === 'http500') return {{ ok: false, status: 500, json: async () => ({{}}) }};
              return {{ ok: true, status: 200, json: async () => ({{ instruments: instrumentPayload }}) }};
            }};

            eval(scriptSource);

            (async () => {{
              await document.listeners.DOMContentLoaded();
              const result = await (async () => {{
                {actions_js}
              }})();
              console.log(JSON.stringify(result));
            }})().catch((error) => {{
              console.error(error && error.stack ? error.stack : String(error));
              process.exit(1);
            }});
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
            raise AssertionError(f"Node template run failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        return json.loads(proc.stdout)

    def test_xcelligence_acknowledgement_is_emitted_when_matching_instrument_is_used(self) -> None:
        instrument = {
            "id": "scope-agilent-rtca-esight",
            "display_name": "Agilent xCELLigence RTCA eSight",
            "retired": False,
            "methods_generation": {"is_blocked": False, "blockers": []},
            "methods": {"base_sentence": "Base method block."},
            "hardware": {
                "scanner": {"present": False},
                "objectives": [],
                "light_sources": [],
                "detectors": [],
                "magnification_changers": [],
                "optical_modulators": [],
                "illumination_logic": [],
                "optical_path": {"filters": [], "splitters": []},
            },
            "modalities": [],
            "modules": [],
        }
        result = self.run_template(
            instruments=[instrument],
            config={
                "acknowledgements": {
                    "standard": "Standard acknowledgement.",
                    "xcelligence_addition": "xCELL acknowledgement.",
                },
                "output_title": "Methods",
                "instrument_data_url": "../assets/instruments_data.json",
            },
            actions_js="""
            const systemSelect = document.getElementById('system-select');
            systemSelect.value = 'scope-agilent-rtca-esight';
            systemSelect.listeners.change({ target: systemSelect });
            document.getElementById('add-btn').listeners.click();
            return { output: document.getElementById('output-text').value };
            """,
        )

        self.assertIn("Standard acknowledgement.", result["output"])
        self.assertIn("xCELL acknowledgement.", result["output"])
        self.assertIn("Base method block.", result["output"])

    def test_duplicate_add_clicks_do_not_duplicate_same_method_block(self) -> None:
        instrument = {
            "id": "scope-1",
            "display_name": "Scope 1",
            "retired": False,
            "methods_generation": {"is_blocked": False, "blockers": []},
            "methods": {"base_sentence": "Base method block."},
            "hardware": {
                "scanner": {"present": False},
                "objectives": [],
                "light_sources": [],
                "detectors": [],
                "magnification_changers": [],
                "optical_modulators": [],
                "illumination_logic": [],
                "optical_path": {"filters": [], "splitters": []},
            },
            "modalities": [],
            "modules": [],
        }
        result = self.run_template(
            instruments=[instrument],
            actions_js="""
            const systemSelect = document.getElementById('system-select');
            systemSelect.value = 'scope-1';
            systemSelect.listeners.change({ target: systemSelect });
            const addButton = document.getElementById('add-btn');
            addButton.listeners.click();
            addButton.listeners.click();
            const output = document.getElementById('output-text').value;
            const count = (output.match(/Base method block\\./g) || []).length;
            return { output, count };
            """,
        )

        self.assertEqual(result["count"], 1)

    def test_fetch_failures_are_reported_in_the_ui(self) -> None:
        result = self.run_template(
            instruments=[],
            fetch_mode="reject",
            actions_js="""
            return {
              output: document.getElementById('output-text').value,
              addDisabled: document.getElementById('add-btn').disabled,
              selectDisabled: document.getElementById('system-select').disabled,
            };
            """,
        )

        self.assertIn("Failed to load instrument data for the Methods Generator", result["output"])
        self.assertTrue(result["addDisabled"])
        self.assertTrue(result["selectDisabled"])


    def test_empty_sections_are_hidden_for_instruments_without_applicable_items(self) -> None:
        instrument = {
            "id": "scope-1",
            "display_name": "Scope 1",
            "retired": False,
            "methods_generation": {"is_blocked": False, "blockers": []},
            "methods": {"base_sentence": "Base method block."},
            "hardware": {
                "scanner": {"present": False},
                "objectives": [{"id": "obj-1", "display_label": "63x Oil", "display_subtitle": "NA 1.40"}],
                "light_sources": [],
                "detectors": [],
                "magnification_changers": [],
                "optical_modulators": [],
                "illumination_logic": [],
                "optical_path": {"filters": [], "splitters": []},
            },
            "modalities": [],
            "modules": [],
        }
        result = self.run_template(
            instruments=[instrument],
            actions_js="""
            const systemSelect = document.getElementById('system-select');
            systemSelect.value = 'scope-1';
            systemSelect.listeners.change({ target: systemSelect });
            return {
              sectionObj: document.getElementById('section-obj').style.display,
              sectionModule: document.getElementById('section-module').style.display,
              sectionLight: document.getElementById('section-light').style.display,
            };
            """,
        )

        self.assertEqual(result["sectionObj"], "")
        self.assertEqual(result["sectionModule"], "none")
        self.assertEqual(result["sectionLight"], "none")

    def test_item_details_are_rendered_inline_with_checkbox_labels(self) -> None:
        instrument = {
            "id": "scope-1",
            "display_name": "Scope 1",
            "retired": False,
            "methods_generation": {"is_blocked": False, "blockers": []},
            "methods": {"base_sentence": "Base method block."},
            "hardware": {
                "scanner": {"present": False},
                "objectives": [
                    {
                        "id": "obj-1",
                        "display_label": "HC PL APO 63x Oil",
                        "display_subtitle": "NA 1.40",
                    }
                ],
                "light_sources": [],
                "detectors": [],
                "magnification_changers": [],
                "optical_modulators": [],
                "illumination_logic": [],
                "optical_path": {"filters": [], "splitters": []},
            },
            "modalities": [],
            "modules": [],
        }
        result = self.run_template(
            instruments=[instrument],
            actions_js="""
            const systemSelect = document.getElementById('system-select');
            systemSelect.value = 'scope-1';
            systemSelect.listeners.change({ target: systemSelect });
            const labelNode = document.getElementById('obj-list').children[0].children[1];
            const mainText = labelNode.children[0]?.textContent || '';
            const noteText = labelNode.children[1]?.textContent || '';
            const noteFontSize = labelNode.children[1]?.style?.fontSize || '';
            const noteColor = labelNode.children[1]?.style?.color || '';
            return { mainText, noteText, noteFontSize, noteColor };
            """,
        )

        self.assertIn('HC PL APO 63x Oil', result['mainText'])
        self.assertIn('NA 1.40', result['noteText'])
        self.assertIn('—', result['noteText'])
        self.assertEqual('0.85em', result['noteFontSize'])
        self.assertEqual('var(--md-default-fg-color--light)', result['noteColor'])

    def test_methods_are_still_generated_when_metadata_blockers_exist(self) -> None:
        instrument = {
            "id": "scope-1",
            "display_name": "Scope 1",
            "retired": False,
            "methods_generation": {
                "is_blocked": True,
                "blockers": [
                    {"kind": "instrument_metadata", "title": "Objective NA"},
                    {"kind": "instrument_metadata", "path": "software[0].version"},
                ],
            },
            "methods": {"base_sentence": "Base method block."},
            "hardware": {
                "scanner": {"present": False},
                "objectives": [],
                "light_sources": [],
                "detectors": [],
                "magnification_changers": [],
                "optical_modulators": [],
                "illumination_logic": [],
                "optical_path": {"filters": [], "splitters": []},
            },
            "modalities": [],
            "modules": [],
        }
        result = self.run_template(
            instruments=[instrument],
            actions_js="""
            const systemSelect = document.getElementById('system-select');
            systemSelect.value = 'scope-1';
            systemSelect.listeners.change({ target: systemSelect });
            document.getElementById('add-btn').listeners.click();
            return { output: document.getElementById('output-text').value };
            """,
        )

        self.assertIn("Base method block.", result["output"])
        self.assertIn("Some instrument metadata is missing", result["output"])
        self.assertIn("ask staff", result["output"])
        self.assertIn("Objective NA", result["output"])

    def test_modality_selector_filters_optical_hardware_from_dto_route_usage(self) -> None:
        instrument = {
            "id": "scope-modality-filter",
            "display_name": "Scope Modality Filter",
            "retired": False,
            "methods_generation": {"is_blocked": False, "blockers": []},
            "methods": {"base_sentence": "Base method block."},
            "hardware": {
                "scanner": {"present": False},
                "objectives": [],
                "light_sources": [],
                "detectors": [],
                "magnification_changers": [],
                "optical_modulators": [],
                "illumination_logic": [],
                "optical_path": {
                    "hardware_inventory_renderables": [
                        {"id": "source:laser_488", "inventory_class": "light_source", "display_label": "488 Laser", "display_subtitle": "Light Source", "method_sentence": "488 sentence.", "modalities": ["widefield_fluorescence"]},
                        {"id": "source:laser_561", "inventory_class": "light_source", "display_label": "561 Laser", "display_subtitle": "Light Source", "method_sentence": "Excitation was provided by 561 Laser.", "modalities": ["confocal"]},
                        {"id": "optical_path_element:ex_488", "inventory_class": "optical_element", "display_label": "EX 488", "display_subtitle": "Optical Element", "method_sentence": "EX sentence.", "modalities": ["widefield_fluorescence"]},
                        {"id": "optical_path_element:pinhole", "inventory_class": "optical_element", "display_label": "Pinhole", "display_subtitle": "Optical Element", "method_sentence": "Pinhole sentence.", "modalities": ["confocal"]},
                        {"id": "endpoint:cam", "inventory_class": "endpoint", "display_label": "Main Camera", "display_subtitle": "Endpoint", "method_sentence": "Cam sentence.", "modalities": ["widefield_fluorescence"]},
                        {"id": "endpoint:hyd", "inventory_class": "endpoint", "display_label": "HyD", "display_subtitle": "Endpoint", "method_sentence": "HyD sentence.", "modalities": ["confocal"]},
                    ],
                    "authoritative_route_contract": {
                        "routes": [
                        {
                            "id": "widefield_fluorescence",
                            "display_label": "Widefield",
                            "illumination_mode": "widefield_fluorescence",
                            "relevant_hardware": {
                                "sources": [{"id": "source:laser_488", "display_label": "488 Laser", "modalities": ["widefield_fluorescence"]}],
                                "filters": [{"id": "optical_path_element:ex_488", "display_label": "EX 488", "modalities": ["widefield_fluorescence"]}],
                                "splitters": [],
                                "endpoints": [{"id": "endpoint:cam", "display_label": "Main Camera", "modalities": ["widefield_fluorescence"]}],
                            },
                        },
                        {
                            "id": "confocal",
                            "display_label": "Confocal",
                            "illumination_mode": "confocal",
                            "relevant_hardware": {
                                "sources": [{"id": "source:laser_561", "display_label": "561 Laser", "modalities": ["confocal"]}],
                                "filters": [{"id": "optical_path_element:pinhole", "display_label": "Pinhole", "modalities": ["confocal"]}],
                                "splitters": [],
                                "endpoints": [{"id": "endpoint:hyd", "display_label": "HyD", "modalities": ["confocal"]}],
                            },
                        },
                    ],
                    },
                },
            },
            "modalities": [
                {"id": "widefield_fluorescence", "display_label": "Widefield Fluorescence"},
                {"id": "confocal", "display_label": "Confocal"},
            ],
            "modules": [],
        }
        result = self.run_template(
            instruments=[instrument],
            actions_js="""
            const systemSelect = document.getElementById('system-select');
            systemSelect.value = 'scope-modality-filter';
            systemSelect.listeners.change({ target: systemSelect });
            // Check the confocal modality checkbox and fire the container change event
            const confocalCheckbox = state.inputs.find(cb => cb.id && cb.id.startsWith('modality-') && cb.value === 'confocal');
            confocalCheckbox.checked = true;
            document.getElementById('modality-list').listeners.change();
            // Check all hardware items now shown (only confocal hardware after filtering)
            document.getElementById('light-list').children.forEach(w => { const cb = w.children[0]; if (cb) cb.checked = true; });
            document.getElementById('filter-list').children.forEach(w => { const cb = w.children[0]; if (cb) cb.checked = true; });
            document.getElementById('det-list').children.forEach(w => { const cb = w.children[0]; if (cb) cb.checked = true; });
            document.getElementById('add-btn').listeners.click();
            return {
              lightCount: document.getElementById('light-list').children.length,
              lightLabel: document.getElementById('light-list').children[0].children[1].children[0].textContent,
              filterLabel: document.getElementById('filter-list').children[0].children[1].children[0].textContent,
              detectorLabel: document.getElementById('det-list').children[0].children[1].children[0].textContent,
              output: document.getElementById('output-text').value,
            };
            """,
        )

        self.assertEqual(result["lightCount"], 1)
        self.assertIn("561 Laser", result["lightLabel"])
        self.assertIn("Pinhole", result["filterLabel"])
        self.assertIn("HyD", result["detectorLabel"])
        self.assertIn("Excitation was provided by 561 Laser.", result["output"])
        self.assertIn("Pinhole sentence.", result["output"])
        self.assertIn("HyD sentence.", result["output"])

    def test_methods_include_exact_runtime_selected_vm_configuration_when_available(self) -> None:
        instrument = {
            "id": "scope-runtime-vm",
            "display_name": "Scope Runtime VM",
            "retired": False,
            "methods_generation": {"is_blocked": False, "blockers": []},
            "methods": {"base_sentence": "Base method block."},
            "hardware": {
                "scanner": {"present": False},
                "objectives": [],
                "light_sources": [],
                "detectors": [],
                "magnification_changers": [],
                "optical_modulators": [],
                "illumination_logic": [],
                "optical_path": {"filters": [], "splitters": []},
            },
            "modalities": [],
            "modules": [],
        }
        result = self.run_template(
            instruments=[instrument],
            actions_js="""
            globalThis.localStorage = {
              getItem(key) {
                if (key !== 'aic.virtualMicroscope.selectedConfiguration') return null;
                return JSON.stringify({
                  scope_id: 'scope-runtime-vm',
                  route: 'confocal_spinning_disk',
                  sources: [{ display_label: 'Laser 561', wavelength_nm: 561 }],
                  selected_route_steps: [
                    { kind: 'optical_component', display_label: 'Filter wheel', position_key: 'Pos_1', _cube_incomplete: true, _unsupported_spectral_model: false },
                    { kind: 'optical_component', display_label: 'Analyzer', position_key: 'Pos_2', _unsupported_spectral_model: true },
                    { kind: 'routing_component', display_label: 'Trinocular', unsupported_reason: 'unsupported_spectral_model' },
                  ],
                  splitters: [{ display_label: 'Dual-view splitter', selected_branch_ids: ['green', 'red'] }],
                  detectors: [{ display_label: 'sCMOS camera', collection_min_nm: 600, collection_max_nm: 700 }],
                  acquisition_plan: {
                    requiresSequentialAcquisition: true,
                    steps: [
                      { step: 1, fluorophoreName: 'DAPI', route: 'widefield' },
                      { step: 2, fluorophoreName: 'mCherry', route: 'confocal' },
                    ],
                  },
                });
              }
            };
            const systemSelect = document.getElementById('system-select');
            systemSelect.value = 'scope-runtime-vm';
            systemSelect.listeners.change({ target: systemSelect });
            document.getElementById('add-btn').listeners.click();
            return { output: document.getElementById('output-text').value };
            """,
        )

        self.assertIn("Exact runtime-selected configuration (browser fallback) used route confocal_spinning_disk.", result["output"])
        self.assertIn("Selected wheel/turret positions:", result["output"])
        self.assertIn("Filter wheel @ Pos_1", result["output"])
        self.assertIn("Selected splitter branches:", result["output"])
        self.assertIn("Dual-view splitter [green, red]", result["output"])
        self.assertIn("Selected endpoints/detectors:", result["output"])
        self.assertIn("sCMOS camera (600–700 nm)", result["output"])
        self.assertIn("Flattened/incomplete optics were present", result["output"])
        self.assertIn("Unsupported spectral model flags were present", result["output"])
        self.assertIn("Sequential acquisition is planned", result["output"])

    def test_runtime_selected_configuration_prefers_exported_dto_over_local_storage(self) -> None:
        instrument = {
            "id": "scope-runtime-exported",
            "display_name": "Scope Runtime Exported",
            "retired": False,
            "runtime_selected_configuration": {
                "route": "dto_route",
                "sources": [{"display_label": "DTO Laser", "wavelength_nm": 488}],
                "selected_route_steps": [{"kind": "optical_component", "display_label": "DTO Wheel", "position_key": "Pos_1"}],
            },
            "methods_generation": {"is_blocked": False, "blockers": []},
            "methods": {"base_sentence": "Base method block."},
            "hardware": {
                "scanner": {"present": False},
                "objectives": [],
                "light_sources": [],
                "detectors": [],
                "magnification_changers": [],
                "optical_modulators": [],
                "illumination_logic": [],
                "optical_path": {"filters": [], "splitters": []},
            },
            "modalities": [],
            "modules": [],
        }
        result = self.run_template(
            instruments=[instrument],
            actions_js="""
            globalThis.localStorage = {
              getItem(key) {
                if (key !== 'aic.virtualMicroscope.selectedConfiguration') return null;
                return JSON.stringify({
                  scope_id: 'scope-runtime-exported',
                  route: 'local_storage_route',
                  sources: [{ display_label: 'LS Laser', wavelength_nm: 561 }],
                  selected_route_steps: [{ kind: 'optical_component', display_label: 'LS Wheel', position_key: 'Pos_9' }],
                });
              }
            };
            const systemSelect = document.getElementById('system-select');
            systemSelect.value = 'scope-runtime-exported';
            systemSelect.listeners.change({ target: systemSelect });
            document.getElementById('add-btn').listeners.click();
            return { output: document.getElementById('output-text').value };
            """,
        )

        self.assertIn("Exact runtime-selected configuration (exported DTO) used route dto_route.", result["output"])
        self.assertIn("DTO Laser (488 nm)", result["output"])
        self.assertNotIn("local_storage_route", result["output"])
        self.assertNotIn("LS Laser", result["output"])

    def test_structured_cube_route_facts_are_rendered_in_methods_text(self) -> None:
        instrument = {
            "id": "scope-cube-structured",
            "display_name": "Scope Cube Structured",
            "retired": False,
            "runtime_selected_configuration": {"route": "widefield"},
            "methods_generation": {"is_blocked": False, "blockers": []},
            "methods": {"base_sentence": "Base method block."},
            "hardware": {
                "scanner": {"present": False},
                "objectives": [],
                "light_sources": [],
                "detectors": [],
                "magnification_changers": [],
                "optical_modulators": [],
                "illumination_logic": [],
                "optical_path": {
                    "filters": [],
                    "splitters": [],
                    "authoritative_route_contract": {
                        "routes": [
                            {
                                "id": "widefield",
                                "route_optical_facts": {
                                    "selected_or_selectable_emission_filters": [
                                        {
                                            "display_label": "GFP Cube",
                                            "position_key": "Pos_1",
                                            "product_code": "49002",
                                            "excitation_filter": {"display_label": "470/40"},
                                            "dichroic": {"display_label": "495LP"},
                                            "emission_filter": {"display_label": "525/50"},
                                        }
                                    ]
                                },
                            }
                        ]
                    },
                },
            },
            "modalities": [],
            "modules": [],
        }
        result = self.run_template(
            instruments=[instrument],
            actions_js="""
            const systemSelect = document.getElementById('system-select');
            systemSelect.value = 'scope-cube-structured';
            systemSelect.listeners.change({ target: systemSelect });
            document.getElementById('add-btn').listeners.click();
            return { output: document.getElementById('output-text').value };
            """,
        )

        self.assertIn("Route-specific optical selections/facts:", result["output"])
        self.assertIn("GFP Cube @ Pos_1", result["output"])
        self.assertIn("cube internals (EX 470/40; DI 495LP; EM 525/50)", result["output"])
        self.assertIn("product code 49002", result["output"])

    def test_flattened_cube_route_facts_render_without_local_storage(self) -> None:
        instrument = {
            "id": "scope-cube-flattened",
            "display_name": "Scope Cube Flattened",
            "retired": False,
            "runtime_selected_configuration": {
                "route": "xcelligence_route",
                "selected_route_steps": [],
            },
            "methods_generation": {"is_blocked": False, "blockers": []},
            "methods": {"base_sentence": "Base method block."},
            "hardware": {
                "scanner": {"present": False},
                "objectives": [],
                "light_sources": [],
                "detectors": [],
                "magnification_changers": [],
                "optical_modulators": [],
                "illumination_logic": [],
                "optical_path": {
                    "filters": [],
                    "splitters": [],
                    "authoritative_route_contract": {
                        "routes": [
                            {
                                "id": "xcelligence_route",
                                "route_optical_facts": {
                                    "selected_or_selectable_excitation_filters": [
                                        {
                                            "display_label": "DAPI channel",
                                            "channel_label": "DAPI",
                                            "available_positions": [
                                                {"display_label": "DAPI", "position_key": "Pos_1"},
                                                {"display_label": "FITC", "position_key": "Pos_2"},
                                            ],
                                            "_cube_incomplete": True,
                                            "_unsupported_spectral_model": True,
                                        }
                                    ]
                                },
                            }
                        ]
                    },
                },
            },
            "modalities": [],
            "modules": [],
        }
        result = self.run_template(
            instruments=[instrument],
            actions_js="""
            globalThis.localStorage = { getItem() { return null; } };
            const systemSelect = document.getElementById('system-select');
            systemSelect.value = 'scope-cube-flattened';
            systemSelect.listeners.change({ target: systemSelect });
            document.getElementById('add-btn').listeners.click();
            return { output: document.getElementById('output-text').value };
            """,
        )

        self.assertIn("Exact runtime-selected configuration (exported DTO) used route xcelligence_route.", result["output"])
        self.assertIn("channel DAPI", result["output"])
        self.assertIn("selectable positions: DAPI and FITC", result["output"])
        self.assertIn("caveats: incomplete cube and unsupported spectral model", result["output"])

    def test_semantic_dedupe_prefers_runtime_selected_source_over_generic_source_sentence(self) -> None:
        instrument = {
            "id": "scope-source-dedupe",
            "display_name": "Scope Source Dedupe",
            "retired": False,
            "runtime_selected_configuration": {
                "route": "route_1",
                "sources": [{"display_label": "Laser 488", "wavelength_nm": 488}],
                "selected_route_steps": [],
            },
            "methods_generation": {"is_blocked": False, "blockers": []},
            "methods": {"base_sentence": "Base method block."},
            "hardware": {
                "scanner": {"present": False},
                "objectives": [],
                "light_sources": [],
                "detectors": [],
                "magnification_changers": [],
                "optical_modulators": [],
                "illumination_logic": [],
                "optical_path": {
                    "hardware_inventory_renderables": [
                        {
                            "id": "source:laser_488",
                            "inventory_class": "light_source",
                            "display_label": "Laser 488",
                            "method_sentence": "Excitation was provided by Laser 488.",
                        }
                    ],
                    "authoritative_route_contract": {"routes": [{"id": "route_1"}]},
                },
            },
            "modalities": [],
            "modules": [],
        }
        result = self.run_template(
            instruments=[instrument],
            actions_js="""
            const systemSelect = document.getElementById('system-select');
            systemSelect.value = 'scope-source-dedupe';
            systemSelect.listeners.change({ target: systemSelect });
            document.getElementById('light-list').children.forEach(w => { const cb = w.children[0]; if (cb) cb.checked = true; });
            document.getElementById('add-btn').listeners.click();
            return { output: document.getElementById('output-text').value };
            """,
        )
        self.assertIn("Selected sources: Laser 488 (488 nm).", result["output"])
        self.assertNotIn("Excitation was provided by Laser 488.", result["output"])

    def test_semantic_dedupe_suppresses_generic_optical_sentence_when_runtime_selection_is_more_specific(self) -> None:
        instrument = {
            "id": "scope-filter-dedupe",
            "display_name": "Scope Filter Dedupe",
            "retired": False,
            "runtime_selected_configuration": {
                "route": "route_2",
                "sources": [],
                "selected_route_steps": [{"kind": "optical_component", "display_label": "Filter wheel", "position_key": "Pos_2"}],
            },
            "methods_generation": {"is_blocked": False, "blockers": []},
            "methods": {"base_sentence": "Base method block."},
            "hardware": {
                "scanner": {"present": False},
                "objectives": [],
                "light_sources": [],
                "detectors": [],
                "magnification_changers": [],
                "optical_modulators": [],
                "illumination_logic": [],
                "optical_path": {
                    "hardware_inventory_renderables": [
                        {
                            "id": "filter:wheel",
                            "inventory_class": "optical_element",
                            "display_label": "Filter wheel",
                            "method_sentence": "The optical path included Filter wheel.",
                        }
                    ],
                    "authoritative_route_contract": {"routes": [{"id": "route_2"}]},
                },
            },
            "modalities": [],
            "modules": [],
        }
        result = self.run_template(
            instruments=[instrument],
            actions_js="""
            const systemSelect = document.getElementById('system-select');
            systemSelect.value = 'scope-filter-dedupe';
            systemSelect.listeners.change({ target: systemSelect });
            document.getElementById('filter-list').children.forEach(w => { const cb = w.children[0]; if (cb) cb.checked = true; });
            document.getElementById('add-btn').listeners.click();
            return { output: document.getElementById('output-text').value };
            """,
        )
        self.assertIn("Selected wheel/turret positions: Filter wheel @ Pos_2.", result["output"])
        self.assertNotIn("The optical path included Filter wheel.", result["output"])

    def test_duplicate_endpoint_prose_with_same_label_is_non_duplicative(self) -> None:
        instrument = {
            "id": "scope-endpoint-dedupe",
            "display_name": "Scope Endpoint Dedupe",
            "retired": False,
            "methods_generation": {"is_blocked": False, "blockers": []},
            "methods": {"base_sentence": "Base method block."},
            "hardware": {
                "scanner": {"present": False},
                "objectives": [],
                "light_sources": [],
                "detectors": [],
                "magnification_changers": [],
                "optical_modulators": [],
                "illumination_logic": [],
                "optical_path": {
                    "hardware_inventory_renderables": [
                        {
                            "id": "endpoint:cam_a",
                            "inventory_class": "endpoint",
                            "display_label": "Kinetix",
                            "method_sentence": "Detected or observed light terminated at Kinetix.",
                        },
                        {
                            "id": "endpoint:cam_b",
                            "inventory_class": "endpoint",
                            "display_label": "Kinetix",
                            "method_sentence": "Detected or observed light terminated at Kinetix.",
                        },
                    ],
                    "authoritative_route_contract": {"routes": []},
                },
            },
            "modalities": [],
            "modules": [],
        }
        result = self.run_template(
            instruments=[instrument],
            actions_js="""
            const systemSelect = document.getElementById('system-select');
            systemSelect.value = 'scope-endpoint-dedupe';
            systemSelect.listeners.change({ target: systemSelect });
            document.getElementById('det-list').children.forEach(w => { const cb = w.children[0]; if (cb) cb.checked = true; });
            document.getElementById('add-btn').listeners.click();
            const output = document.getElementById('output-text').value;
            const count = (output.match(/Detected or observed light terminated at Kinetix\\./g) || []).length;
            return { output, count };
            """,
        )
        self.assertEqual(result["count"], 1)

    def test_quarep_placeholder_is_only_appended_when_export_marks_it_needed(self) -> None:
        instrument = {
            "id": "scope-quarep-flag",
            "display_name": "Scope Quarep Flag",
            "retired": False,
            "methods_generation": {"is_blocked": False, "blockers": []},
            "methods": {
                "base_sentence": "Base method block.",
                "quarep_light_path_recommendation_needed": False,
                "quarep_light_path_recommendation": "[PLEASE VERIFY: this should not be shown].",
            },
            "hardware": {
                "scanner": {"present": False},
                "objectives": [],
                "light_sources": [],
                "detectors": [],
                "magnification_changers": [],
                "optical_modulators": [],
                "illumination_logic": [],
                "optical_path": {"filters": [], "splitters": [], "authoritative_route_contract": {"routes": []}},
            },
            "modalities": [],
            "modules": [],
        }
        result = self.run_template(
            instruments=[instrument],
            actions_js="""
            const systemSelect = document.getElementById('system-select');
            systemSelect.value = 'scope-quarep-flag';
            systemSelect.listeners.change({ target: systemSelect });
            document.getElementById('add-btn').listeners.click();
            return { output: document.getElementById('output-text').value };
            """,
        )
        self.assertIn("Base method block.", result["output"])
        self.assertNotIn("this should not be shown", result["output"])

    def test_methods_text_keeps_route_fact_field_when_present_upstream(self) -> None:
        """Regression guard: upstream route fact fields (e.g. product_code) must survive to final methods text."""
        instrument = {
            "id": "scope-field-survival",
            "display_name": "Scope Field Survival",
            "retired": False,
            "runtime_selected_configuration": {"route": "widefield"},
            "methods_generation": {"is_blocked": False, "blockers": []},
            "methods": {"base_sentence": "Base method block."},
            "hardware": {
                "scanner": {"present": False},
                "objectives": [],
                "light_sources": [],
                "detectors": [],
                "magnification_changers": [],
                "optical_modulators": [],
                "illumination_logic": [],
                "optical_path": {
                    "authoritative_route_contract": {
                        "routes": [
                            {
                                "id": "widefield",
                                "route_optical_facts": {
                                    "selected_or_selectable_emission_filters": [
                                        {
                                            "display_label": "FITC cube",
                                            "position_key": "Pos_2",
                                            "product_code": "A1-49002",
                                        }
                                    ]
                                },
                            }
                        ]
                    }
                },
            },
            "modalities": [],
            "modules": [],
        }
        result = self.run_template(
            instruments=[instrument],
            actions_js="""
            const systemSelect = document.getElementById('system-select');
            systemSelect.value = 'scope-field-survival';
            systemSelect.listeners.change({ target: systemSelect });
            document.getElementById('add-btn').listeners.click();
            return { output: document.getElementById('output-text').value };
            """,
        )
        self.assertIn("FITC cube @ Pos_2", result["output"])
        self.assertIn("product code A1-49002", result["output"])

    def test_route_specific_and_runtime_selected_configuration_sentences_are_not_duplicated(self) -> None:
        instrument = {
            "id": "scope-no-dup-route-runtime",
            "display_name": "Scope No Dup",
            "retired": False,
            "runtime_selected_configuration": {
                "route": "route_main",
                "selected_route_steps": [{"kind": "optical_component", "display_label": "Filter wheel", "position_key": "Pos_1"}],
            },
            "methods_generation": {"is_blocked": False, "blockers": []},
            "methods": {"base_sentence": "Base method block."},
            "hardware": {
                "scanner": {"present": False},
                "objectives": [],
                "light_sources": [],
                "detectors": [],
                "magnification_changers": [],
                "optical_modulators": [],
                "illumination_logic": [],
                "optical_path": {
                    "authoritative_route_contract": {
                        "routes": [
                            {
                                "id": "route_main",
                                "route_optical_facts": {
                                    "selected_or_selectable_emission_filters": [
                                        {"display_label": "Filter wheel", "position_key": "Pos_1"}
                                    ]
                                },
                            }
                        ]
                    }
                },
            },
            "modalities": [],
            "modules": [],
        }
        result = self.run_template(
            instruments=[instrument],
            actions_js="""
            const systemSelect = document.getElementById('system-select');
            systemSelect.value = 'scope-no-dup-route-runtime';
            systemSelect.listeners.change({ target: systemSelect });
            document.getElementById('add-btn').listeners.click();
            const output = document.getElementById('output-text').value;
            return {
              output,
              routeCount: (output.match(/Exact runtime-selected configuration/g) || []).length,
              wheelCount: (output.match(/Selected wheel\\/turret positions:/g) || []).length
            };
            """,
        )
        self.assertEqual(result["routeCount"], 1)
        self.assertEqual(result["wheelCount"], 1)

    def test_xcelligence_style_flattened_channel_facts_render_without_cube_internals(self) -> None:
        """Regression guard for xCELLigence-style flattened cubes: known channel/positions must still render."""
        instrument = {
            "id": "scope-agilent-rtca-esight",
            "display_name": "Agilent xCELLigence RTCA eSight",
            "retired": False,
            "runtime_selected_configuration": {"route": "xcelligence_route"},
            "methods_generation": {"is_blocked": False, "blockers": []},
            "methods": {"base_sentence": "Base method block."},
            "hardware": {
                "scanner": {"present": False},
                "objectives": [],
                "light_sources": [],
                "detectors": [],
                "magnification_changers": [],
                "optical_modulators": [],
                "illumination_logic": [],
                "optical_path": {
                    "authoritative_route_contract": {
                        "routes": [
                            {
                                "id": "xcelligence_route",
                                "route_optical_facts": {
                                    "selected_or_selectable_excitation_filters": [
                                        {
                                            "display_label": "DAPI channel",
                                            "channel_label": "DAPI",
                                            "available_positions": [
                                                {"display_label": "DAPI", "position_key": "Pos_1"},
                                                {"display_label": "FITC", "position_key": "Pos_2"},
                                            ],
                                            "_cube_incomplete": True,
                                            "_unsupported_spectral_model": True,
                                        }
                                    ]
                                },
                            }
                        ]
                    }
                },
            },
            "modalities": [],
            "modules": [],
        }
        result = self.run_template(
            instruments=[instrument],
            actions_js="""
            const systemSelect = document.getElementById('system-select');
            systemSelect.value = 'scope-agilent-rtca-esight';
            systemSelect.listeners.change({ target: systemSelect });
            document.getElementById('add-btn').listeners.click();
            return { output: document.getElementById('output-text').value };
            """,
        )
        self.assertIn("channel DAPI", result["output"])
        self.assertIn("selectable positions: DAPI and FITC", result["output"])
        self.assertIn("caveats: incomplete cube and unsupported spectral model", result["output"])


if __name__ == "__main__":
    unittest.main()
