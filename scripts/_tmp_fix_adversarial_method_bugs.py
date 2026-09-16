from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Expected marker not found in {path}: {old[:180]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# -----------------------------------------------------------------------------
# Methods Generator: one acquisition == one physical route, with safe state reset.
# -----------------------------------------------------------------------------
js = "assets/javascripts/methods_generator_app.js"

replace_once(
    js,
    '''            const routeCheckbox = document.createElement("input");
            routeCheckbox.type = "checkbox";
            routeCheckbox.id = `route-${routeIdx}`;
''',
    '''            const routeCheckbox = document.createElement("input");
            routeCheckbox.type = "radio";
            routeCheckbox.name = "methods-light-path";
            routeCheckbox.id = `route-${routeIdx}`;
''',
)

replace_once(
    js,
    '''            routeCheckbox.dataset.category = "route";
            routeCheckbox.dataset.routeType = cleanText(route.route_type);

            const routeLabelEl = document.createElement("label");
''',
    '''            routeCheckbox.dataset.category = "route";
            routeCheckbox.dataset.routeType = cleanText(route.route_type);
            const relevantHardware = route?.relevant_hardware && typeof route.relevant_hardware === "object"
                ? route.relevant_hardware : {};
            const hasRecordedRouteHardware = ["sources", "filters", "splitters", "endpoints"]
                .some(key => Array.isArray(relevantHardware[key]) && relevantHardware[key].length > 0);
            routeCheckbox.dataset.topologyIncomplete = hasRecordedRouteHardware ? "" : "1";

            const routeLabelEl = document.createElement("label");
''',
)

replace_once(
    js,
    '''            routeIds: parseJsonArray(cb.dataset.routeIds),
            publicationTemplate: cleanText(cb.dataset.publicationTemplate),
''',
    '''            routeIds: parseJsonArray(cb.dataset.routeIds),
            topologyIncomplete: cb.dataset.topologyIncomplete === "1",
            publicationTemplate: cleanText(cb.dataset.publicationTemplate),
''',
)

replace_once(
    js,
    '''    document.getElementById("method-list").addEventListener("change", (event) => {
        if (!currentInst || event?.target?.dataset.category !== "method") return;
        const routeIds = parseJsonArray(event.target.dataset.routeIds);
        const allowed = new Set(routeIds);
        const routeInputs = Array.from(document.querySelectorAll('input[id^="route-"]'));
        routeInputs.forEach((route) => {
            const wrapper = route.parentElement;
            const compatible = allowed.has(route.value);
            if (wrapper) wrapper.style.display = compatible ? "" : "none";
            route.disabled = !compatible;
            if (!compatible) route.checked = false;
        });
        document.querySelectorAll('input[id^="readout-"]').forEach((readout) => {
            const compatible = allowed.has(readout.dataset.routeId);
            if (readout.parentElement) readout.parentElement.style.display = compatible ? "" : "none";
            readout.disabled = !compatible;
            if (!compatible) readout.checked = false;
        });
        toggleSectionVisibility("section-route", routeIds.length > 0);
        if (routeIds.length === 1) {
            const route = routeInputs.find(item => item.value === routeIds[0]);
            if (route) route.checked = true;
            updateHardwareVisibility(currentInst);
        } else {
            ["section-light", "section-filter", "section-splitter", "section-det"].forEach(id => {
                const section = document.getElementById(id);
                if (section) section.style.display = "none";
            });
        }
    });
''',
    '''    document.getElementById("method-list").addEventListener("change", (event) => {
        if (!currentInst || event?.target?.dataset.category !== "method") return;
        const routeIds = parseJsonArray(event.target.dataset.routeIds);
        const allowed = new Set(routeIds);
        const routeInputs = Array.from(document.querySelectorAll('input[id^="route-"]'));

        // Changing method starts a new physical-path decision. Route-specific state
        // from the previous method must never survive invisibly into the new draft.
        ["route", "readout", "light", "det", "filter", "filterposition", "splitter"].forEach(prefix => {
            document.querySelectorAll(`input[id^="${prefix}-"]`).forEach(input => { input.checked = false; });
        });

        routeInputs.forEach((route) => {
            const wrapper = route.parentElement;
            const compatible = allowed.has(route.value);
            if (wrapper) wrapper.style.display = compatible ? "" : "none";
            route.disabled = !compatible;
        });
        document.querySelectorAll('input[id^="readout-"]').forEach((readout) => {
            const compatible = allowed.has(readout.dataset.routeId);
            if (readout.parentElement) readout.parentElement.style.display = compatible ? "" : "none";
            readout.disabled = !compatible;
        });
        toggleSectionVisibility("section-route", routeIds.length > 0);

        const selectionStatus = document.getElementById("methods-selection-status");
        if (selectionStatus) {
            selectionStatus.textContent = "";
            selectionStatus.style.display = "none";
        }

        if (routeIds.length === 1) {
            const route = routeInputs.find(item => item.value === routeIds[0]);
            if (route) route.checked = true;
            updateHardwareVisibility(currentInst, false);
        } else {
            // Re-render with no retained state so hidden controls cannot remain
            // checked, then keep route-specific hardware hidden until one path is chosen.
            updateHardwareVisibility(currentInst, false);
            ["section-light", "section-filter", "section-splitter", "section-det"].forEach(id => {
                const section = document.getElementById(id);
                if (section) section.style.display = "none";
            });
        }
    });
''',
)

replace_once(
    js,
    '''    document.getElementById("route-list").addEventListener("change", (event) => {
        const target = event?.target;
        if (target?.dataset.category === "route" && target.checked) {
            document.querySelectorAll('input[id^="readout-"]').forEach(readout => {
                if (readout.dataset.routeId !== target.value) readout.checked = false;
            });
        } else if (target?.dataset.category === "readout" && target.checked) {
            document.querySelectorAll('input[id^="route-"]').forEach(route => {
                if (route.value === target.dataset.routeId) route.checked = true;
            });
        } else if (target?.dataset.category === "route" && !target.checked) {
            document.querySelectorAll('input[id^="readout-"]').forEach(readout => {
                if (readout.dataset.routeId === target.value) readout.checked = false;
            });
        }
        if (currentInst) updateHardwareVisibility(currentInst);
    });
''',
    '''    document.getElementById("route-list").addEventListener("change", (event) => {
        const target = event?.target;
        const selectedRouteBefore = getCheckedIds("route")[0] || "";
        let preserveHardware = true;
        if (target?.dataset.category === "route" && target.checked) {
            preserveHardware = false;
            document.querySelectorAll('input[id^="readout-"]').forEach(readout => {
                if (readout.dataset.routeId !== target.value) readout.checked = false;
            });
        } else if (target?.dataset.category === "readout" && target.checked) {
            const targetRouteId = cleanText(target.dataset.routeId);
            preserveHardware = selectedRouteBefore === targetRouteId;
            document.querySelectorAll('input[id^="route-"]').forEach(route => {
                if (route.value === targetRouteId) route.checked = true;
            });
            document.querySelectorAll('input[id^="readout-"]').forEach(readout => {
                if (readout !== target && readout.dataset.routeId !== targetRouteId) readout.checked = false;
            });
        } else if (target?.dataset.category === "route" && !target.checked) {
            document.querySelectorAll('input[id^="readout-"]').forEach(readout => {
                if (readout.dataset.routeId === target.value) readout.checked = false;
            });
        }
        if (currentInst) updateHardwareVisibility(currentInst, preserveHardware);
    });
''',
)

replace_once(
    js,
    '''        const routeSelections = getCheckedSelections("route");
        const runtime = runtimeAcquisitionFacts(dto);
''',
    '''        const routeSelections = getCheckedSelections("route");
        routeSelections
            .filter(item => item.topologyIncomplete)
            .forEach(item => prompts.push(
                `[PLEASE VERIFY: the recorded hardware topology for the ${item.displayLabel} light path is incomplete; confirm the illumination and detection components used]`
            ));
        const runtime = runtimeAcquisitionFacts(dto);
''',
)

replace_once(
    js,
    '''    addBtn.addEventListener("click", () => {
        if (!currentInst) return;

        const dto = currentInst;
        if (!instrumentDtoIsRenderable(dto)) {
''',
    '''    addBtn.addEventListener("click", () => {
        if (!currentInst) return;

        const methodSection = document.getElementById("section-method");
        const methodFirst = Boolean(methodSection && methodSection.style.display !== "none");
        const selectionStatus = document.getElementById("methods-selection-status");
        if (methodFirst && getCheckedIds("method").length === 0) {
            if (selectionStatus) {
                selectionStatus.textContent = "Choose the imaging method used for this acquisition.";
                selectionStatus.style.display = "";
            }
            return;
        }
        if (methodFirst && getCheckedIds("route").length === 0) {
            if (selectionStatus) {
                selectionStatus.textContent = "Choose the light path used for this acquisition.";
                selectionStatus.style.display = "";
            }
            return;
        }
        if (selectionStatus) {
            selectionStatus.textContent = "";
            selectionStatus.style.display = "none";
        }

        const dto = currentInst;
        if (!instrumentDtoIsRenderable(dto)) {
''',
)

# -----------------------------------------------------------------------------
# Empty optical positions: rely on structured component_type, not only labels.
# -----------------------------------------------------------------------------
replace_once(
    "scripts/dashboard/optical_path_view.py",
    '''                    "is_empty": clean_text(label).lower() in {"empty", "none", "blank"},
''',
    '''                    "is_empty": (
                        clean_text(position.get("component_type")).lower() == "empty"
                        or clean_text(label).lower() in {"empty", "none", "blank"}
                    ),
''',
)

# -----------------------------------------------------------------------------
# Route vocabulary: reflected brightfield is a reflected-light route, not fluorescence.
# This prevents the previous AxioZoom mapping from validating again.
# -----------------------------------------------------------------------------
replace_once(
    "vocab/optical_routes.yaml",
    '''      contrast_methods:
        - reflected_brightfield
        - optical_sectioning
  - id: transmitted_light
''',
    '''      contrast_methods:
        - optical_sectioning
  - id: reflected_light
    label: Reflected light
    display_label: Reflected light
    description: Reflected or incident-light route family used to illuminate opaque or thick specimens from above the sample.
    synonyms: [incident light, epi brightfield, reflected illumination]
    covers:
      imaging_modes: []
      contrast_methods:
        - reflected_brightfield
  - id: transmitted_light
''',
)

# -----------------------------------------------------------------------------
# Zeiss AxioZoom V16: use the recorded CL 9000 ring light for reflected brightfield.
# -----------------------------------------------------------------------------
replace_once(
    "instruments/Zeiss AxioZoom V16.yaml",
    '''  contrast_methods:
  - optical_sectioning
  - reflected_brightfield
- id: transmitted_light
''',
    '''  contrast_methods:
  - optical_sectioning
- id: reflected_light
  illumination_sequence:
  - source_id: cl_9000_led_can_ring_light
  detection_sequence:
  - optical_path_element_id: trinocular_port
  - branches:
      selection_mode: exclusive
      items:
      - branch_id: to_mono_camera
        label: To ORCA-Flash4.0 LT+
        sequence:
        - endpoint_id: detector_1
      - branch_id: to_color_camera
        label: To AxioCam 105
        sequence:
        - endpoint_id: detector_2
      - branch_id: to_eyepieces
        label: To Eyepieces
        sequence:
        - endpoint_id: eyepieces
  route_type: reflected_light
  contrast_methods:
  - reflected_brightfield
- id: transmitted_light
''',
)

# -----------------------------------------------------------------------------
# Validator: a method can be explicitly mapped yet have no recorded topology.
# Keep the mapping usable but surface the data-quality problem as a warning.
# -----------------------------------------------------------------------------
replace_once(
    "scripts/validation/instrument.py",
    '''        route_readouts = light_path.get('readouts')
        if isinstance(route_readouts, list):
            for readout in route_readouts:
                if isinstance(readout, str) and readout.strip():
                    canonical_readout = vocabulary.resolve_canonical('measurement_readouts', readout) or readout.strip()
                    covered_readouts.add(canonical_readout)

    for modality in sorted(required_route_coverage - covered_route_terms):
''',
    '''        route_readouts = light_path.get('readouts')
        if isinstance(route_readouts, list):
            for readout in route_readouts:
                if isinstance(readout, str) and readout.strip():
                    canonical_readout = vocabulary.resolve_canonical('measurement_readouts', readout) or readout.strip()
                    covered_readouts.add(canonical_readout)

        mapped_methods = [
            value
            for axis in ('imaging_modes', 'contrast_methods')
            for value in (light_path.get(axis) or [])
            if isinstance(value, str) and value.strip()
        ]
        illumination_sequence = light_path.get('illumination_sequence')
        detection_sequence = light_path.get('detection_sequence')
        if mapped_methods and not illumination_sequence and not detection_sequence:
            warnings.append(ValidationIssue(
                code='method_path_topology_empty',
                path=route_path,
                message=(
                    f"Instrument '{instrument_file.stem}' light path '{route_label}' maps method(s) "
                    f"{', '.join(mapped_methods)} but has no recorded illumination or detection sequence. "
                    "The method mapping is explicit, but downstream Methods text must treat the hardware topology as incomplete."
                ),
            ))

    for modality in sorted(required_route_coverage - covered_route_terms):
''',
)

# -----------------------------------------------------------------------------
# Browser regressions: add a method mapped to two physical paths and verify state.
# -----------------------------------------------------------------------------
test = "tests/test_methods_generator_method_first.py"
replace_once(
    test,
    '''        {
            "id": "unmapped-service-path",
            "display_label": "Unmapped service path",
            "route_type": "widefield_fluorescence",
            "route_type_label": "Widefield Fluorescence",
            "route_identity": {
                "imaging_modes": [],
                "contrast_methods": [],
                "readouts": [],
            },
            "relevant_hardware": {
                "sources": [], "filters": [], "splitters": [], "endpoints": [],
            },
            "branch_summary": {"branches": []},
        },
''',
    '''        {
            "id": "unmapped-service-path",
            "display_label": "Unmapped service path",
            "route_type": "widefield_fluorescence",
            "route_type_label": "Widefield Fluorescence",
            "route_identity": {
                "imaging_modes": [],
                "contrast_methods": [],
                "readouts": [],
            },
            "relevant_hardware": {
                "sources": [], "filters": [], "splitters": [], "endpoints": [],
            },
            "branch_summary": {"branches": []},
        },
        {
            "id": "smlm-path-a",
            "display_label": "SMLM path A",
            "route_type": "widefield_fluorescence",
            "route_type_label": "Widefield Fluorescence",
            "route_identity": {
                "imaging_modes": [{"id": "smlm", "display_label": "SMLM"}],
                "contrast_methods": [],
                "readouts": [],
            },
            "relevant_hardware": {
                "sources": [laser], "filters": [], "splitters": [], "endpoints": [camera_a],
            },
            "branch_summary": {"branches": []},
        },
        {
            "id": "smlm-path-b",
            "display_label": "SMLM path B",
            "route_type": "widefield_fluorescence",
            "route_type_label": "Widefield Fluorescence",
            "route_identity": {
                "imaging_modes": [{"id": "smlm", "display_label": "SMLM"}],
                "contrast_methods": [],
                "readouts": [],
            },
            "relevant_hardware": {
                "sources": [lamp], "filters": [], "splitters": [], "endpoints": [brightfield_camera],
            },
            "branch_summary": {"branches": []},
        },
''',
)

replace_once(
    test,
    '''        self.assertEqual(methods.count(), 2)
''',
    '''        self.assertEqual(methods.count(), 3)
''',
)

replace_once(
    test,
    '''    def test_method_first_selection_reveals_only_compatible_route_hardware(self):
        expect(self.page.locator("#section-method")).to_be_visible()
''',
    '''    def test_add_requires_method_then_physical_path(self):
        self.page.click("#add-btn")
        expect(self.page.locator("#methods-selection-status")).to_contain_text("Choose the imaging method")
        self.page.check("#method-2")
        self.page.click("#add-btn")
        expect(self.page.locator("#methods-selection-status")).to_contain_text("Choose the light path")
        self.assertNotIn("SMLM imaging was performed", self.output())

    def test_multi_route_method_uses_single_route_radio_and_clears_old_hardware(self):
        self.page.check("#method-0")
        self.page.check("#light-0")
        self.page.check("#method-2")
        routes = self.page.locator('#route-list input[data-category="route"]:visible')
        self.assertEqual(routes.count(), 2)
        self.assertEqual(routes.nth(0).get_attribute("type"), "radio")
        self.assertEqual(routes.nth(1).get_attribute("type"), "radio")
        expect(routes.nth(0)).not_to_be_checked()
        expect(routes.nth(1)).not_to_be_checked()
        expect(self.page.locator("#section-light")).to_be_hidden()
        self.assertEqual(self.page.locator('#light-list input:checked').count(), 0)
        routes.nth(0).check()
        expect(routes.nth(0)).to_be_checked()
        expect(self.page.locator("#section-light")).to_be_visible()
        routes.nth(1).check()
        expect(routes.nth(0)).not_to_be_checked()
        expect(routes.nth(1)).to_be_checked()
        self.assertEqual(self.page.locator('#light-list input:checked').count(), 0)

    def test_method_first_selection_reveals_only_compatible_route_hardware(self):
        expect(self.page.locator("#section-method")).to_be_visible()
''',
)

# The existing switch test still uses method-1, which remains transmitted brightfield;
# SMLM is appended after the original two methods.

# Add a direct empty-position projection regression and an AxioZoom physical-route regression.
active_test = "tests/test_active_yaml_contracts.py"
replace_once(
    active_test,
    '''    def test_all_active_repo_methods_have_explicit_light_path_mapping(self) -> None:
''',
    '''    def test_axiozoom_reflected_brightfield_uses_recorded_reflected_source(self) -> None:
        data = yaml.safe_load((INSTRUMENTS_DIR / "Zeiss AxioZoom V16.yaml").read_text(encoding="utf-8")) or {}
        paths = [row for row in (data.get("light_paths") or []) if isinstance(row, dict)]
        matches = [row for row in paths if "reflected_brightfield" in (row.get("contrast_methods") or [])]
        self.assertEqual(len(matches), 1)
        route = matches[0]
        self.assertEqual(route.get("route_type"), "reflected_light")
        source_ids = [
            step.get("source_id")
            for step in (route.get("illumination_sequence") or [])
            if isinstance(step, dict) and step.get("source_id")
        ]
        self.assertEqual(source_ids, ["cl_9000_led_can_ring_light"])
        sources = {
            row.get("id"): row
            for row in ((data.get("hardware") or {}).get("sources") or [])
            if isinstance(row, dict) and row.get("id")
        }
        self.assertEqual(sources[source_ids[0]].get("role"), "reflected_illumination")

    def test_all_active_repo_methods_have_explicit_light_path_mapping(self) -> None:
''',
)

# Add browser test for structured empty positions using a non-literal-empty label.
replace_once(
    test,
    '''                "selection_mode": "exclusive",
                "route_ids": ["widefield"],
                "route_labels": ["Widefield fluorescence"],
            },
        ],
''',
    '''                "selection_mode": "exclusive",
                "route_ids": ["widefield"],
                "route_labels": ["Widefield fluorescence"],
            },
            {
                "id": "emp_bf",
                "display_label": "EMP_BF",
                "product_code": "EMPTY",
                "component_type": "empty",
                "selection_mode": "exclusive",
                "is_empty": True,
                "route_ids": ["widefield"],
                "route_labels": ["Widefield fluorescence"],
            },
        ],
''',
)

replace_once(
    test,
    '''    def test_internal_compatibility_marker_is_not_emitted(self):
''',
    '''    def test_structured_empty_position_emits_no_filter_sentence(self):
        self.page.check("#method-0")
        positions = self.page.locator('#filter-list input[id^="filterposition-"]')
        self.assertEqual(positions.count(), 3)
        positions.nth(2).check()
        self.page.click("#add-btn")
        self.assertIn("No filter was installed in Filter turret.", self.output())
        self.assertNotIn("EMP_BF in the Filter turret", self.output())

    def test_internal_compatibility_marker_is_not_emitted(self):
''',
)

# Remove this one-shot script/workflow from the final tree after it has done its job.
for rel in (
    "scripts/_tmp_fix_adversarial_method_bugs.py",
    ".github/workflows/tmp-fix-adversarial-method-bugs.yml",
):
    path = ROOT / rel
    if path.exists():
        path.unlink()
