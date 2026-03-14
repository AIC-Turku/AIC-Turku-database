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


if __name__ == "__main__":
    unittest.main()
