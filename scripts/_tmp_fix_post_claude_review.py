from pathlib import Path


def replace_exact(path: str, old: str, new: str) -> None:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one replacement, found {count}")
    file_path.write_text(text.replace(old, new), encoding="utf-8")


# 1. Keep acquisition software out of the automatic method opening. The
# microscope identity is exported as a separate structured phrase; software
# remains a user-confirmed action.
replace_exact(
    "scripts/dashboard/instrument_view.py",
    '''    microscope_identity = " ".join(part for part in [clean_text(canonical_instrument.get("manufacturer")), clean_text(canonical_instrument.get("model"))] if part).strip()\n    stand = clean_text(canonical_instrument.get("stand_orientation"))\n    stand_label = _vocab_display(vocabulary, "stand_orientations", stand) if stand else stand\n    base_sentence = f"Images were acquired using the {microscope_identity} {stand_label.lower()} microscope, controlled by {acquisition_software}." if microscope_identity and stand_label else f"Images were acquired using the {microscope_identity} microscope, controlled by {acquisition_software}."\n''',
    '''    microscope_identity = " ".join(part for part in [clean_text(canonical_instrument.get("manufacturer")), clean_text(canonical_instrument.get("model"))] if part).strip()\n    stand = clean_text(canonical_instrument.get("stand_orientation"))\n    stand_label = _vocab_display(vocabulary, "stand_orientations", stand) if stand else stand\n    display_name = clean_text(inst.get("display_name"))\n    if microscope_identity and stand_label:\n        instrument_reference = f"the {microscope_identity} {stand_label.lower()} microscope"\n    elif microscope_identity:\n        instrument_reference = f"the {microscope_identity} microscope"\n    elif display_name:\n        instrument_reference = f"the {display_name}"\n    else:\n        instrument_reference = "the microscope"\n    base_sentence = f"Images were acquired using the {microscope_identity} {stand_label.lower()} microscope, controlled by {acquisition_software}." if microscope_identity and stand_label else f"Images were acquired using the {microscope_identity} microscope, controlled by {acquisition_software}."\n''',
)
replace_exact(
    "scripts/dashboard/instrument_view.py",
    '''        "methods": {\n            "base_sentence": base_sentence,\n''',
    '''        "methods": {\n            "base_sentence": base_sentence,\n            # Identity only. Acquisition software is intentionally excluded so the\n            # Methods Generator reports it only after the user confirms it was used.\n            "instrument_reference": instrument_reference,\n''',
)

replace_exact(
    "assets/javascripts/methods_generator_app.js",
    '''        // `base_sentence` is composed from the recorded manufacturer, model and\n        // stand orientation. The method leads the sentence, but that identity is\n        // canonical instrument fact and must survive: dropping it leaves a reader\n        // unable to tell which microscope was used.\n        const instrumentClause = identitySentence\n            .replace(/^Images were acquired using\\s+/i, "")\n            .replace(/\\.$/, "");\n        const instrumentName = instrumentClause\n            || cleanText(dto.display_name) || cleanText(dto.id) || "the microscope";\n''',
    '''        // Use the structured identity-only phrase. `base_sentence` also carries\n        // acquisition software for legacy consumers, and parsing it here would\n        // publish software even when the user did not confirm that action.\n        const instrumentName = cleanText(methods.instrument_reference)\n            || cleanText(dto.display_name) || cleanText(dto.id) || "the microscope";\n''',
)

# 2. Method-specific settings and physical-path settings are complementary.
# A confocal-family path does not turn STED into confocal imaging, but scan
# mechanics can still be relevant to a STED/ISM acquisition.
replace_exact(
    "assets/javascripts/methods_generator_app.js",
    '''    const MODALITY_SETTINGS_PROMPTS = {\n        confocal_point: reportingRecommendation(\n            "confocal pinhole diameter (in Airy units), scan zoom, pixel dwell time, and line/frame averaging"),\n        confocal_spinning_disk: reportingRecommendation(\n            "camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice)"),\n        multiphoton: reportingRecommendation(\n            "excitation wavelength, mean power at the sample, and pulse width"),\n        light_sheet: reportingRecommendation(\n            "light-sheet thickness, sheet numerical aperture, and the detection/illumination objective pairing"),\n        tirf: reportingRecommendation(\n            "TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available"),\n        sted: reportingRecommendation(\n            "STED depletion wavelength and power at the sample, time-gating settings where used, and the phase-mask/beam-shaping configuration"),\n        sim: reportingRecommendation(\n            "SIM pattern/orientation settings and the reconstruction software/version and parameters used"),\n        smlm: reportingRecommendation(\n            "number of frames, exposure time, activation/excitation settings, localization software/version, and drift-correction method"),\n        ism: reportingRecommendation(\n            "detector/reconstruction mode and the reconstruction software/version and settings used"),\n    };\n''',
    '''    const METHOD_SETTINGS_PROMPTS = {\n        multiphoton: reportingRecommendation(\n            "excitation wavelength, mean power at the sample, and pulse width"),\n        light_sheet: reportingRecommendation(\n            "light-sheet thickness, sheet numerical aperture, and the detection/illumination objective pairing"),\n        tirf: reportingRecommendation(\n            "TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available"),\n        sted: reportingRecommendation(\n            "STED depletion wavelength and power at the sample, time-gating settings where used, and the phase-mask/beam-shaping configuration"),\n        sim: reportingRecommendation(\n            "SIM pattern/orientation settings and the reconstruction software/version and parameters used"),\n        smlm: reportingRecommendation(\n            "number of frames, exposure time, activation/excitation settings, localization software/version, and drift-correction method"),\n        ism: reportingRecommendation(\n            "detector/reconstruction mode and the reconstruction software/version and settings used"),\n    };\n    const PATH_SETTINGS_PROMPTS = {\n        confocal_point: reportingRecommendation(\n            "scan zoom, pixel dwell time, line/frame averaging, and, when a confocal pinhole was used, its diameter (in Airy units)"),\n        confocal_spinning_disk: reportingRecommendation(\n            "camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice)"),\n    };\n''',
)
replace_exact(
    "assets/javascripts/methods_generator_app.js",
    '''    function modalitySettingsPrompts(methodSelections, routeSelections, readoutSelections) {\n        // The technique the user confirmed decides which settings a reader needs.\n        // A route family is not a technique: asking a STED acquisition for confocal\n        // pinhole and dwell time - because STED runs on the confocal path - is the\n        // route-implies-method inference this page is built to avoid. The route\n        // family is used only for records that carry no method mapping at all,\n        // which is the retired/legacy case.\n        const prompts = uniqueTexts(\n            methodSelections.length\n                ? methodSelections.map(item => MODALITY_SETTINGS_PROMPTS[cleanText(item.id).toLowerCase()] || "")\n                : routeSelections.map(item => MODALITY_SETTINGS_PROMPTS[item.routeType] || "")\n        );\n        readoutSelections.forEach((item) => {\n            const prompt = READOUT_SETTINGS_PROMPTS[cleanText(item.displayLabel).toLowerCase()];\n            if (prompt) prompts.push(prompt);\n        });\n        return uniqueTexts(prompts);\n    }\n''',
    '''    function modalitySettingsPrompts(methodSelections, routeSelections, readoutSelections) {\n        // Method and path answer different questions. The selected method supplies\n        // technique-specific settings (for example STED depletion power); the\n        // physical route can add implementation settings (for example scan dwell\n        // time) without claiming that the route family is itself the method. For\n        // legacy records with no method mapping, retain the old route-as-fallback\n        // recommendation so retired instruments do not lose useful guidance.\n        const methodPrompts = methodSelections.map(\n            item => METHOD_SETTINGS_PROMPTS[cleanText(item.id).toLowerCase()] || "");\n        const pathPrompts = routeSelections.map(\n            item => PATH_SETTINGS_PROMPTS[cleanText(item.routeType).toLowerCase()] || "");\n        const legacyMethodPrompts = methodSelections.length\n            ? []\n            : routeSelections.map(\n                item => METHOD_SETTINGS_PROMPTS[cleanText(item.routeType).toLowerCase()] || "");\n        const prompts = uniqueTexts([...methodPrompts, ...pathPrompts, ...legacyMethodPrompts]);\n        readoutSelections.forEach((item) => {\n            const prompt = READOUT_SETTINGS_PROMPTS[cleanText(item.displayLabel).toLowerCase()];\n            if (prompt) prompts.push(prompt);\n        });\n        return uniqueTexts(prompts);\n    }\n''',
)

# 3. When scientifically identical positions have different slot keys on two
# routes, collapse the duplicate but union its route membership.
replace_exact(
    "scripts/dashboard/optical_path_view.py",
    '''            seen_identities = {\n                (row["display_label"], row["product_code"], row["component_type"].lower())\n                for row in known\n            }\n''',
    '''            by_identity = {\n                (row["display_label"], row["product_code"], row["component_type"].lower()): row\n                for row in known\n            }\n''',
)
replace_exact(
    "scripts/dashboard/optical_path_view.py",
    '''                twin = (label, clean_text(position.get("product_code")), clean_text(position.get("component_type")).lower())\n                if twin in seen_identities:\n                    continue\n                seen_identities.add(twin)\n                row = {\n''',
    '''                twin = (label, clean_text(position.get("product_code")), clean_text(position.get("component_type")).lower())\n                duplicate = by_identity.get(twin)\n                if duplicate is not None:\n                    if route_id and route_id not in duplicate["route_ids"]:\n                        duplicate["route_ids"].append(route_id)\n                    if route_label and route_label not in duplicate["route_labels"]:\n                        duplicate["route_labels"].append(route_label)\n                    continue\n                row = {\n''',
)
replace_exact(
    "scripts/dashboard/optical_path_view.py",
    '''                by_key[key] = row\n                known.append(row)\n''',
    '''                by_key[key] = row\n                by_identity[twin] = row\n                known.append(row)\n''',
)

# 4. The dashboard mapping covers imaging modes and contrast methods, not every
# broader capability axis such as FLIM readouts or assay operations.
replace_exact(
    "scripts/templates/instrument_spec.md.j2",
    '''  <div class="aic-muted" style="margin-bottom: 6px;">Each method below is explicitly associated in the instrument record with the physical light path that implements it. A capability that appears above but not here has no recorded path yet.</div>\n''',
    '''  <div class="aic-muted" style="margin-bottom: 6px;">Each method below is explicitly associated in the instrument record with the physical light path that implements it. An imaging mode or contrast method that appears above but not here has no recorded method-to-path mapping yet.</div>\n''',
)

# 5. Publication wording for ISM/Airyscan.
replace_exact(
    "vocab/imaging_modes.yaml",
    '''  publication_phrase: "Airyscan (image scanning) imaging"\n''',
    '''  publication_phrase: "Image scanning microscopy (ISM; Airyscan)"\n''',
)

# Regression: realistic base_sentence contains software, while the structured
# instrument reference does not. Software appears only after its action is ticked.
replace_exact(
    "tests/test_methods_generator_method_first.py",
    '''        "methods": {\n            "base_sentence": (\n                "Images were acquired using the Method First Scope "\n                "(Acme MF-1), an inverted microscope."\n            )\n        },\n        "software": [],\n''',
    '''        "methods": {\n            "base_sentence": (\n                "Images were acquired using the Method First Scope "\n                "(Acme MF-1), an inverted microscope, controlled by Acme Acquire (v1.0)."\n            ),\n            "instrument_reference": "the Method First Scope (Acme MF-1), an inverted microscope",\n        },\n        "software": [\n            {"name": "Acme Acquire", "version": "1.0", "role": "acquisition"},\n        ],\n''',
)
replace_exact(
    "tests/test_methods_generator_method_first.py",
    '''    def test_light_path_is_not_offered_before_the_method_decision(self):\n''',
    '''    def test_acquisition_software_is_only_reported_when_confirmed(self):\n        self.page.check("#method-0")\n        self.page.click("#add-btn")\n        self.assertNotIn("Acme Acquire", self.output())\n\n        self.page.check("#confirmed-0")\n        self.page.click("#add-btn")\n        self.assertIn(\n            "Instrument control and image acquisition were performed using Acme Acquire (v1.0).",\n            self.output(),\n        )\n        self.assertEqual(self.output().count("Acme Acquire"), 1)\n\n    def test_light_path_is_not_offered_before_the_method_decision(self):\n''',
)
replace_exact(
    "tests/test_methods_generator_method_first.py",
    '''    def test_technique_prompts_come_from_the_method_not_the_route_family(self):\n        """A route family is not a technique.\n\n        STED runs on the confocal path, so reading the family as the technique\n        asks a STED acquisition for confocal pinhole and dwell-time settings.\n        """\n        self.page.check('#method-list input[value="sted"]')\n        self.page.click("#add-btn")\n        output = self.output()\n        self.assertIn("STED depletion wavelength", output)\n        self.assertNotIn("confocal pinhole diameter", output)\n''',
    '''    def test_method_and_path_reporting_prompts_are_both_preserved(self):\n        """Technique and physical-path settings are complementary, not aliases.\n\n        STED on a point-scanning path needs STED-specific reporting as well as\n        relevant scan mechanics, without declaring the acquisition to be\n        confocal imaging or assuming that a confocal pinhole was used.\n        """\n        self.page.check('#method-list input[value="sted"]')\n        self.page.click("#add-btn")\n        output = self.output()\n        self.assertIn("STED depletion wavelength", output)\n        self.assertIn("pixel dwell time", output)\n        self.assertIn("when a confocal pinhole was used", output)\n''',
)

# Regression for cross-route identity deduplication.
replace_exact(
    "tests/test_methods_position_identity_regressions.py",
    '''\n\nclass PublicationProseRegressions(unittest.TestCase):\n''',
    '''\n\n    def test_equivalent_position_on_two_routes_unions_route_membership(self) -> None:\n        """A deduplicated filter must remain selectable on every route that records it."""\n        holder_id = "optical_path_element:test_wheel"\n\n        def route(route_id: str, position_key: str) -> dict:\n            return {\n                "id": route_id,\n                "display_label": route_id,\n                "selected_execution": {\n                    "selected_route_steps": [\n                        {\n                            "hardware_inventory_id": holder_id,\n                            "display_label": "Test emission wheel",\n                            "available_positions": [\n                                {\n                                    "position_key": position_key,\n                                    "name": "525/25",\n                                    "product_code": "ET525/25",\n                                    "component_type": "filter",\n                                    "selection_mode": "exclusive",\n                                }\n                            ],\n                        }\n                    ]\n                },\n            }\n\n        rows = _selectable_positions_by_component([route("route-a", "slot-a"), route("route-b", "slot-b")])[holder_id]\n        self.assertEqual(len(rows), 1)\n        self.assertEqual(set(rows[0]["route_ids"]), {"route-a", "route-b"})\n        self.assertEqual(set(rows[0]["route_labels"]), {"route-a", "route-b"})\n\n\nclass PublicationProseRegressions(unittest.TestCase):\n''',
)

# DTO-level regression: the builder itself must publish an identity-only phrase.
replace_exact(
    "tests/test_software_status_semantics.py",
    '''    def test_dashboard_message_for_not_applicable(self):\n''',
    '''    def test_methods_instrument_reference_excludes_acquisition_software(self):\n        dto = build_instrument_mega_dto(\n            _Vocab(),\n            {\n                "id": "s1",\n                "display_name": "Scope One",\n                "canonical": {\n                    "instrument": {"manufacturer": "Acme", "model": "M1"},\n                    "software": [{"name": "Acme Acquire", "version": "1.0", "role": "acquisition"}],\n                    "software_status": "recorded",\n                    "modalities": [],\n                    "modules": [],\n                    "hardware": {},\n                },\n            },\n            {"light_paths": []},\n        )\n        self.assertEqual("the Acme M1 microscope", dto["methods"]["instrument_reference"])\n        self.assertNotIn("Acme Acquire", dto["methods"]["instrument_reference"])\n        self.assertIn("Acme Acquire", dto["methods"]["base_sentence"])\n\n    def test_dashboard_message_for_not_applicable(self):\n''',
)

print("Applied post-Claude review fixes")
