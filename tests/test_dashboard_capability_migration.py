from __future__ import annotations

import unittest
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from scripts.build_context import normalize_instrument_dto
from scripts.dashboard.site_render import _annotate_display_labels, _build_vocabulary


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTRUMENTS_DIR = REPO_ROOT / "instruments"


def _template_env() -> Environment:
    templates_dir = REPO_ROOT / "scripts" / "templates"
    return Environment(loader=FileSystemLoader(templates_dir), autoescape=False)


def _load_optical_routes_vocab() -> set[str]:
    """Return valid optical route IDs from vocab/optical_routes.yaml."""
    import yaml  # type: ignore[import]
    vocab_path = REPO_ROOT / "vocab" / "optical_routes.yaml"
    data = yaml.safe_load(vocab_path.read_text(encoding="utf-8"))
    ids: set[str] = set()
    for term in data.get("terms", []):
        if isinstance(term, dict) and term.get("id"):
            ids.add(term["id"])
    return ids


class CapabilityMigrationTests(unittest.TestCase):
    def test_strict_vs_non_strict_diagnostics_severity_matrix(self) -> None:
        active_missing_caps = {
            "instrument": {"instrument_id": "scope-active", "display_name": "Scope Active"},
            "modalities": ["confocal_point"],
        }
        with self.assertRaises(RuntimeError):
            normalize_instrument_dto(active_missing_caps, Path("scope-active.yaml"), retired=False)

        active_with_legacy_top_level_modalities = {
            "instrument": {"instrument_id": "scope-active-legacy", "display_name": "Scope Active Legacy"},
            "modalities": ["confocal_point"],
            "capabilities": {"imaging_modes": ["confocal_point"]},
        }
        with self.assertRaises(RuntimeError):
            normalize_instrument_dto(active_with_legacy_top_level_modalities, Path("scope-active-legacy.yaml"), retired=False)

        active_with_legacy_lightpath_modalities = {
            "instrument": {"instrument_id": "scope-active-2", "display_name": "Scope Active 2"},
            "capabilities": {"imaging_modes": ["confocal_point"]},
            "light_paths": [{"id": "confocal_point", "modalities": ["flim"]}],
        }
        normalized = normalize_instrument_dto(active_with_legacy_lightpath_modalities, Path("scope-active-2.yaml"), retired=False)
        self.assertEqual(normalized["capabilities"]["imaging_modes"], ["confocal_point"])

        retired_missing_caps = {
            "instrument": {"instrument_id": "scope-retired-1", "display_name": "Scope Retired"},
            "modalities": ["confocal_point"],
        }
        out = normalize_instrument_dto(retired_missing_caps, Path("scope-retired-1.yaml"), retired=True)
        self.assertIn("imaging_modes", out["capabilities"])

    def test_capability_filter_options_use_axis_ids_and_labels(self) -> None:
        vocabulary = _build_vocabulary(Path.cwd())
        instruments = [{
            "id": "scope1",
            "display_name": "Scope 1",
            "modalities": ["confocal"],
            "capabilities": {"imaging_modes": ["confocal_point"], "readouts": ["flim"]},
            "modules": [],
        }]
        _annotate_display_labels(instruments, [], vocabulary)
        ids = instruments[0]["capabilities_primary_ids"]
        self.assertIn("imaging_modes:confocal_point", ids)
        self.assertIn("readouts:flim", ids)
        self.assertNotIn("confocal", ids)

    def test_index_template_uses_capability_filter_options(self) -> None:
        tpl = _template_env().get_template("index.md.j2")
        rendered = tpl.render(
            counts={"total": 1, "green": 1, "yellow": 0, "red": 0},
            instruments=[{
                "id": "scope1",
                "display_name": "Scope 1",
                "manufacturer": "Acme",
                "model": "X",
                "image_filename": "placeholder.svg",
                "status": {"color": "green", "badge": "Online"},
                "capabilities_primary": [{"label": "Confocal point scanning"}],
                "capabilities_primary_ids": ["imaging_modes:confocal_point"],
            }],
            capability_filter_options=[{"id": "imaging_modes:confocal_point", "label": "Imaging: Confocal point scanning"}],
        )
        self.assertIn("Imaging: Confocal point scanning", rendered)
        self.assertIn('data-capabilities="imaging_modes:confocal_point"', rendered)

    def test_instrument_spec_route_type_and_readouts_are_separate(self) -> None:
        tpl = _template_env().get_template("instrument_spec.md.j2")
        dto = {
            "identity": {"display_name": "Scope", "id": "scope", "image_filename": "placeholder.svg", "manufacturer": "", "model": "", "stand_orientation": {"display_label": ""}, "ocular_availability": {"display_label": ""}, "location": "", "year_of_purchase": "", "funding": ""},
            "status": {"color": "green", "badge": "Online", "reason": "ok"},
            "capabilities": {k: [] for k in ["imaging_modes", "contrast_methods", "readouts", "workflows", "assay_operations", "non_optical"]},
            "modalities": [],
            "modules": [],
            "software": [],
            "hardware": {
                "environment": {"present": False},
                "light_sources": [],
                "scanner": {"present": False},
                "detectors": [],
                "objectives": [],
                "magnification_changers": [],
                "optical_modulators": [],
                "illumination_logic": [],
                "stages": [],
                "hardware_autofocus": {"present": False},
                "triggering": {"present": False},
                "optical_path": {"sections": [], "authoritative_route_contract": {"routes": [{"id": "route1", "display_label": "Confocal route", "illumination_mode": "confocal_point", "route_identity": {"route_type": "confocal_point", "route_type_label": "Confocal point scanning", "readouts": [{"id": "flim", "display_label": "FLIM"}, {"id": "fcs", "display_label": "FCS"}]}}]}},
            },
        }
        rendered = tpl.render(
            instrument={"dto": dto},
            latest_metrics={}, metric_names={}, policy={"missing_required": [], "missing_conditional": [], "alias_fallbacks": []}
        )
        self.assertIn("Route type:", rendered)
        self.assertIn("Confocal point scanning", rendered)
        self.assertIn("FLIM", rendered)
        self.assertIn("FCS", rendered)

    def test_all_active_instruments_have_explicit_capabilities(self) -> None:
        """Every active (non-retired) instrument YAML must have at least one non-empty capabilities axis."""
        import yaml  # type: ignore[import]
        missing: list[str] = []
        for yaml_path in sorted(INSTRUMENTS_DIR.glob("*.yaml")):
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            caps = data.get("capabilities")
            if not isinstance(caps, dict) or not any(
                isinstance(v, list) and v for v in caps.values()
            ):
                missing.append(yaml_path.name)
        self.assertFalse(
            missing,
            f"Active instruments missing non-empty capabilities: {missing}. "
            "Add explicit capabilities.* axes to these YAML files.",
        )

    def test_all_active_instruments_light_path_ids_are_valid_optical_routes(self) -> None:
        """Every light_path id in active instrument YAMLs must be a recognised optical route term."""
        import yaml  # type: ignore[import]
        valid_route_ids = _load_optical_routes_vocab()
        invalid: list[str] = []
        for yaml_path in sorted(INSTRUMENTS_DIR.glob("*.yaml")):
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            light_paths = data.get("light_paths")
            if not isinstance(light_paths, list):
                continue
            for lp in light_paths:
                if not isinstance(lp, dict):
                    continue
                route_id = (lp.get("id") or "").strip()
                if route_id and route_id not in valid_route_ids:
                    invalid.append(f"{yaml_path.name}: light_path id='{route_id}'")
        self.assertFalse(
            invalid,
            "Light path IDs are not recognised optical route vocabulary terms. "
            "Use route types from vocab/optical_routes.yaml; move readout-axis terms "
            "(flim, fcs, spectral_imaging) to light_paths[].readouts:\n"
            + "\n".join(f"  - {item}" for item in invalid),
        )

    def test_normalize_instrument_dto_raises_for_active_instrument_missing_capabilities(self) -> None:
        """normalize_instrument_dto must raise RuntimeError for active (non-retired) instruments
        that have no canonical capabilities, preventing silent legacy-modality fallback."""
        payload = {
            "instrument": {"instrument_id": "scope-test-fallback", "display_name": "Test"},
            "modalities": ["confocal_point"],
            # No 'capabilities' key → should be a hard error for active instruments
        }
        with self.assertRaises(RuntimeError) as ctx:
            normalize_instrument_dto(payload, Path("test_fallback.yaml"), retired=False)
        self.assertIn("capabilities", str(ctx.exception).lower())

    def test_normalize_instrument_dto_allows_fallback_for_retired_instruments(self) -> None:
        """normalize_instrument_dto must allow legacy-modalities fallback for retired instruments."""
        import unittest.mock as mock
        payload = {
            "instrument": {"instrument_id": "scope-retired", "display_name": "Retired Scope"},
            "modalities": ["confocal_point"],
            # No 'capabilities' key — acceptable for retired instruments
        }
        with mock.patch("scripts.build_context.build_instrument_completeness_report") as report_builder:
            report_builder.return_value = mock.Mock(
                sections=[], missing_required=[], missing_conditional=[], alias_fallbacks=[]
            )
            result = normalize_instrument_dto(payload, Path("test_retired.yaml"), retired=True)
        self.assertIsNotNone(result)
        self.assertEqual(result["capabilities"].get("imaging_modes"), ["confocal_point"])


class RouteReadoutPropagationTests(unittest.TestCase):
    """Tests that route-level readouts flow from YAML through the canonical DTO chain."""

    def _build_stellaris_vm_payload(self) -> dict:
        import yaml  # type: ignore[import]
        from scripts.lightpath.vm_payload import generate_virtual_microscope_payload

        yaml_path = REPO_ROOT / "instruments" / "Leica STELLARIS 8 FALCON FLIM.yaml"
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        return generate_virtual_microscope_payload(data)

    def _build_lambert_vm_payload(self) -> dict:
        import yaml  # type: ignore[import]
        from scripts.lightpath.vm_payload import generate_virtual_microscope_payload

        yaml_path = REPO_ROOT / "instruments" / "Lambert FLIM.yaml"
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        return generate_virtual_microscope_payload(data)

    def test_stellaris_confocal_route_identity_has_readouts(self) -> None:
        """STELLARIS confocal_point route_identity must include spectral_imaging, flim, fcs."""
        payload = self._build_stellaris_vm_payload()
        light_paths = payload.get("light_paths") or []
        confocal = next(
            (lp for lp in light_paths if lp.get("id") == "confocal_point"),
            None,
        )
        self.assertIsNotNone(confocal, "confocal_point route not found in STELLARIS light_paths")
        route_identity = confocal.get("route_identity") or {}
        readout_ids = route_identity.get("readouts") or []
        self.assertIn("spectral_imaging", readout_ids,
                      f"spectral_imaging not in route_identity.readouts; got: {readout_ids}")
        self.assertIn("flim", readout_ids,
                      f"flim not in route_identity.readouts; got: {readout_ids}")
        self.assertIn("fcs", readout_ids,
                      f"fcs not in route_identity.readouts; got: {readout_ids}")

    def test_stellaris_confocal_route_readouts_field_populated(self) -> None:
        """STELLARIS confocal_point light_paths entry must have a readouts list."""
        payload = self._build_stellaris_vm_payload()
        light_paths = payload.get("light_paths") or []
        confocal = next(
            (lp for lp in light_paths if lp.get("id") == "confocal_point"),
            None,
        )
        self.assertIsNotNone(confocal)
        readouts = confocal.get("readouts") or []
        self.assertIn("flim", readouts)
        self.assertIn("fcs", readouts)
        self.assertIn("spectral_imaging", readouts)

    def test_lambert_widefield_route_identity_has_flim(self) -> None:
        """Lambert FLIM widefield_fluorescence route_identity must include flim."""
        payload = self._build_lambert_vm_payload()
        light_paths = payload.get("light_paths") or []
        widefield = next(
            (lp for lp in light_paths if lp.get("id") == "widefield_fluorescence"),
            None,
        )
        self.assertIsNotNone(widefield, "widefield_fluorescence not found in Lambert light_paths")
        route_identity = widefield.get("route_identity") or {}
        readout_ids = route_identity.get("readouts") or []
        self.assertIn("flim", readout_ids,
                      f"flim not in Lambert widefield route_identity.readouts; got: {readout_ids}")

    def test_authoritative_route_contract_includes_readouts_for_stellaris(self) -> None:
        """authoritative_route_contract.routes must include readouts for STELLARIS confocal route."""
        import yaml  # type: ignore[import]
        from scripts.lightpath.vm_payload import generate_virtual_microscope_payload
        from scripts.dashboard.optical_path_view import build_optical_path_view_dto
        from scripts.dashboard.site_render import _build_vocabulary

        yaml_path = REPO_ROOT / "instruments" / "Leica STELLARIS 8 FALCON FLIM.yaml"
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        lightpath_dto = generate_virtual_microscope_payload(data)
        vocabulary = _build_vocabulary(REPO_ROOT)
        optical_dto = build_optical_path_view_dto(lightpath_dto, vocabulary=vocabulary)

        arc = optical_dto.get("authoritative_route_contract") or {}
        routes = arc.get("routes") or []
        confocal = next((r for r in routes if r.get("id") == "confocal_point"), None)
        self.assertIsNotNone(confocal, "confocal_point not in authoritative_route_contract.routes")
        self.assertEqual(confocal.get("route_type"), "confocal_point")
        route_readouts = confocal.get("readouts") or []
        readout_ids = [r.get("id") for r in route_readouts if isinstance(r, dict)]
        self.assertIn("flim", readout_ids, f"flim not in route readouts; got: {route_readouts}")
        self.assertIn("fcs", readout_ids, f"fcs not in route readouts; got: {route_readouts}")

    def test_route_identity_readouts_are_dicts_with_display_label(self) -> None:
        """route_identity.readouts in authoritative_route_contract must be dicts with display_label."""
        import yaml  # type: ignore[import]
        from scripts.lightpath.vm_payload import generate_virtual_microscope_payload
        from scripts.dashboard.optical_path_view import build_optical_path_view_dto
        from scripts.dashboard.site_render import _build_vocabulary

        yaml_path = REPO_ROOT / "instruments" / "Leica STELLARIS 8 FALCON FLIM.yaml"
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        lightpath_dto = generate_virtual_microscope_payload(data)
        vocabulary = _build_vocabulary(REPO_ROOT)
        optical_dto = build_optical_path_view_dto(lightpath_dto, vocabulary=vocabulary)

        arc = optical_dto.get("authoritative_route_contract") or {}
        routes = arc.get("routes") or []
        confocal = next((r for r in routes if r.get("id") == "confocal_point"), None)
        self.assertIsNotNone(confocal)
        self.assertNotIn("modality", confocal.get("route_identity") or {})
        self.assertNotIn("modalities", confocal.get("route_identity") or {})
        route_readouts = confocal.get("readouts") or []
        self.assertTrue(len(route_readouts) > 0, "Expected non-empty readouts list")
        for ro in route_readouts:
            self.assertIsInstance(ro, dict, f"Readout entry must be a dict; got: {ro}")
            self.assertIn("id", ro, f"Readout dict must have 'id'; got: {ro}")
            self.assertIn("display_label", ro, f"Readout dict must have 'display_label'; got: {ro}")
            self.assertTrue(ro["display_label"], f"display_label must not be empty; got: {ro}")

    def _load_stellaris_inst_with_lightpath(self) -> tuple:
        """Load STELLARIS instrument, canonical DTO, and lightpath_dto.

        Returns (normalized_dto, lightpath_dto, optical_path_dto, vocabulary).
        """
        import yaml  # type: ignore[import]
        import copy
        import unittest.mock as mock
        from scripts.build_context import normalize_instrument_dto
        from scripts.lightpath.vm_payload import generate_virtual_microscope_payload
        from scripts.dashboard.optical_path_view import build_optical_path_view_dto
        from scripts.dashboard.site_render import _build_vocabulary

        yaml_path = REPO_ROOT / "instruments" / "Leica STELLARIS 8 FALCON FLIM.yaml"
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        vocabulary = _build_vocabulary(REPO_ROOT)

        with mock.patch("scripts.build_context.build_instrument_completeness_report") as rb:
            rb.return_value = mock.Mock(
                sections=[], missing_required=[], missing_conditional=[], alias_fallbacks=[]
            )
            normalized = normalize_instrument_dto(data, yaml_path, retired=False)

        lightpath_dto = generate_virtual_microscope_payload(normalized["canonical"])
        optical_dto = build_optical_path_view_dto(lightpath_dto, vocabulary=vocabulary)

        # Inject authoritative_route_contract as build_context does during full builds
        arc = copy.deepcopy(optical_dto.get("authoritative_route_contract") or {})
        lightpath_dto.setdefault("projections", {}).setdefault("llm", {})["authoritative_route_contract"] = arc

        return normalized, lightpath_dto, optical_dto, vocabulary

    def test_methods_export_canonical_routes_non_empty_for_stellaris(self) -> None:
        """methods_export.routes must not be empty for STELLARIS (has light_paths)."""
        from scripts.dashboard.methods_export import build_methods_generator_instrument_export

        normalized, lightpath_dto, _, _ = self._load_stellaris_inst_with_lightpath()
        inst = {**normalized, "lightpath_dto": lightpath_dto}
        methods_dto = build_methods_generator_instrument_export(inst)

        routes = methods_dto.get("routes") or []
        self.assertTrue(
            len(routes) > 0,
            f"methods_export.routes must not be empty for STELLARIS; got: {routes}",
        )
        confocal = next((r for r in routes if r.get("id") == "confocal_point"), None)
        self.assertIsNotNone(confocal, "confocal_point route not in methods_export.routes")
        readouts = confocal.get("readouts") or []
        self.assertIn("flim", readouts, f"flim not in confocal route readouts; got: {readouts}")

    def test_llm_route_contract_includes_readouts_for_stellaris(self) -> None:
        """LLM authoritative_route_contract routes must include readouts for STELLARIS."""
        from scripts.dashboard.llm_export import build_llm_inventory_payload

        normalized, lightpath_dto, _, _ = self._load_stellaris_inst_with_lightpath()
        inst = {**normalized, "lightpath_dto": lightpath_dto}
        facility = {"short_name": "TestFacility", "contact_url": "", "public_site_url": ""}
        llm_payload = build_llm_inventory_payload(facility, [inst])

        records = llm_payload.get("active_microscopes") or []
        self.assertTrue(len(records) > 0, "Expected at least one LLM record")
        rec = records[0]

        arc = (rec.get("llm_context") or {}).get("authoritative_route_contract") or {}
        routes = arc.get("routes") or []
        confocal = next((r for r in routes if r.get("id") == "confocal_point"), None)
        self.assertIsNotNone(
            confocal, "confocal_point not in LLM authoritative_route_contract.routes"
        )
        self.assertEqual(confocal.get("route_type"), "confocal_point")
        route_identity = confocal.get("route_identity") or {}
        readouts = route_identity.get("readouts") or []
        readout_ids = [r.get("id") if isinstance(r, dict) else r for r in readouts]
        self.assertIn("flim", readout_ids, f"flim not in LLM route readouts; got: {readouts}")

    def test_lambert_and_oni_route_type_readout_contract(self) -> None:
        import yaml  # type: ignore[import]
        from scripts.lightpath.vm_payload import generate_virtual_microscope_payload

        lambert = yaml.safe_load((REPO_ROOT / "instruments" / "Lambert FLIM.yaml").read_text(encoding="utf-8"))
        oni = yaml.safe_load((REPO_ROOT / "instruments" / "ONI Nanoimager.yaml").read_text(encoding="utf-8"))
        lambert_lp = generate_virtual_microscope_payload(lambert).get("light_paths") or []
        oni_lp = generate_virtual_microscope_payload(oni).get("light_paths") or []
        lroute = next((r for r in lambert_lp if r.get("id") == "widefield_fluorescence"), {})
        oroute = next((r for r in oni_lp if r.get("id") == "tirf"), {})
        self.assertEqual((lroute.get("route_identity") or {}).get("route_type"), "widefield_fluorescence")
        self.assertIn("flim", (lroute.get("route_identity") or {}).get("readouts") or [])
        self.assertEqual((oroute.get("route_identity") or {}).get("route_type"), "tirf")
        self.assertIn("fret", (oroute.get("route_identity") or {}).get("readouts") or [])

    def test_llm_payload_labels_modalities_as_compatibility(self) -> None:
        """LLM record must include modalities_note labeling flat modalities as compatibility-only."""
        from scripts.dashboard.llm_export import build_llm_inventory_payload

        normalized, lightpath_dto, _, _ = self._load_stellaris_inst_with_lightpath()
        inst = {**normalized, "lightpath_dto": lightpath_dto}
        facility = {"short_name": "TestFacility", "contact_url": "", "public_site_url": ""}
        llm_payload = build_llm_inventory_payload(facility, [inst])

        records = llm_payload.get("active_microscopes") or []
        self.assertTrue(len(records) > 0)
        rec = records[0]

        note = rec.get("modalities_note") or ""
        self.assertTrue(
            note,
            "LLM record must include modalities_note explaining flat modalities is compatibility-only",
        )
        self.assertIn(
            "compatibility", note.lower(),
            f"modalities_note must mention compatibility; got: {note}",
        )

    def test_no_active_instrument_triggers_capability_fallback(self) -> None:
        """No active instrument YAML should trigger the capability fallback (RuntimeError)."""
        import yaml  # type: ignore[import]
        import unittest.mock as mock
        from scripts.build_context import normalize_instrument_dto

        errors: list[str] = []
        for yaml_path in sorted(INSTRUMENTS_DIR.glob("*.yaml")):
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            try:
                with mock.patch("scripts.build_context.build_instrument_completeness_report") as rb:
                    rb.return_value = mock.Mock(
                        sections=[], missing_required=[], missing_conditional=[], alias_fallbacks=[]
                    )
                    normalize_instrument_dto(data, yaml_path, retired=False)
            except RuntimeError as exc:
                errors.append(f"{yaml_path.name}: {exc}")
        self.assertFalse(
            errors,
            "Active instruments triggered the capabilities fallback (add explicit "
            "capabilities.* axes):\n" + "\n".join(f"  - {e}" for e in errors),
        )

    def test_readout_terms_not_used_as_light_path_ids(self) -> None:
        """Readout-axis terms must not appear as light_paths[].id in any active instrument YAML.

        The valid readout IDs are loaded from vocab/measurement_readouts.yaml to stay
        in sync with the authoritative vocabulary.
        """
        import yaml  # type: ignore[import]

        # Load readout term IDs from the canonical vocabulary file
        readout_vocab_path = REPO_ROOT / "vocab" / "measurement_readouts.yaml"
        readout_vocab = yaml.safe_load(readout_vocab_path.read_text(encoding="utf-8"))
        readout_terms = {
            str(term["id"])
            for term in (readout_vocab.get("terms") or [])
            if isinstance(term, dict) and term.get("id")
        }

        invalid: list[str] = []
        for yaml_path in sorted(INSTRUMENTS_DIR.glob("*.yaml")):
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            for lp in (data.get("light_paths") or []):
                if not isinstance(lp, dict):
                    continue
                route_id = (lp.get("id") or "").strip()
                if route_id in readout_terms:
                    invalid.append(f"{yaml_path.name}: light_path id={route_id!r}")
        self.assertFalse(
            invalid,
            "Readout-axis terms used as light_paths[].id. "
            "Move them to light_paths[].readouts instead:\n"
            + "\n".join(f"  - {item}" for item in invalid),
        )


    def test_instrument_spec_template_hides_legacy_modalities_and_shows_flat_capability_chips(self) -> None:
        from scripts.dashboard.instrument_view import build_instrument_mega_dto
        from scripts.dashboard.site_render import _annotate_display_labels
        normalized, lightpath_dto, _, vocabulary = self._load_stellaris_inst_with_lightpath()
        inst = {**normalized, "lightpath_dto": lightpath_dto}
        dto = build_instrument_mega_dto(vocabulary, inst, lightpath_dto)
        inst["dto"] = dto
        _annotate_display_labels([inst], [], vocabulary)
        rendered = _template_env().get_template("instrument_spec.md.j2").render(instrument=inst, latest_metrics={}, metric_names={}, policy={"missing_required": [], "missing_conditional": [], "alias_fallbacks": []})
        self.assertNotIn("Legacy modalities", rendered)
        for label in ("FLIM", "FCS", "Spectral Imaging", "Confocal point scanning", "Widefield fluorescence", "Transmitted brightfield"):
            self.assertIn(label, rendered)
        self.assertIn("Show grouped capability axes", rendered)

    def test_instrument_spec_template_renders_route_readouts_not_dash(self) -> None:
        """instrument_spec.md.j2 must render FLIM and FCS chips for STELLARIS, not just dashes."""
        from scripts.dashboard.instrument_view import build_instrument_mega_dto
        from scripts.dashboard.site_render import _annotate_display_labels

        normalized, lightpath_dto, optical_dto, vocabulary = self._load_stellaris_inst_with_lightpath()
        inst = {**normalized, "lightpath_dto": lightpath_dto}

        # Build the full instrument mega DTO that the template consumes
        dto = build_instrument_mega_dto(vocabulary, inst, lightpath_dto)
        inst["dto"] = dto
        _annotate_display_labels([inst], [], vocabulary)

        tpl_env = _template_env()
        tpl = tpl_env.get_template("instrument_spec.md.j2")
        rendered = tpl.render(
            instrument=inst,
            latest_metrics={},
            metric_names={},
            policy={"missing_required": [], "missing_conditional": [], "alias_fallbacks": []},
        )
        self.assertIn("FLIM", rendered,
                      "FLIM readout chip must appear in rendered route section for STELLARIS")
        self.assertIn("FCS", rendered,
                      "FCS readout chip must appear in rendered route section for STELLARIS")
