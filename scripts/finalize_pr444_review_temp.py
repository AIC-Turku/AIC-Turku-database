from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, found {count}: {old[:120]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_objective_labels() -> None:
    path = ROOT / "scripts" / "dashboard" / "instrument_view.py"
    replace_once(
        path,
        '''    correction = _vocab_display(vocabulary, "objective_corrections", obj.get("correction") or obj.get("correction_class"))\n    mag = _fmt_num(obj.get("magnification") or obj.get("mag"))\n''',
        '''    correction = _vocab_display(vocabulary, "objective_corrections", obj.get("correction") or obj.get("correction_class"))\n    specialty_labels = [\n        _vocab_display(vocabulary, "objective_specialties", item)\n        for item in clean_string_list(obj.get("specialties"))\n    ]\n    mag = _fmt_num(obj.get("magnification") or obj.get("mag"))\n''',
    )
    replace_once(
        path,
        '''        ("Specialties", ", ".join(clean_string_list(obj.get("specialties"))) or None),\n''',
        '''        ("Specialties", ", ".join(label for label in specialty_labels if label) or None),\n''',
    )


def patch_vm_source_labels() -> None:
    path = ROOT / "scripts" / "lightpath" / "spectral_ops.py"
    replace_once(
        path,
        '''from scripts.display_labels import resolve_stage_role_label\n''',
        '''from scripts.display_labels import (\n    resolve_light_source_kind_label,\n    resolve_stage_role_label,\n    resolve_vocab_label,\n)\n''',
    )
    replace_once(
        path,
        '''    role = _source_role(source)\n\n    position: dict[str, Any] = {\n''',
        '''    role = _source_role(source)\n    vocabulary = get_active_vocab()\n    kind_label = (\n        resolve_light_source_kind_label(kind, vocabulary)\n        if vocabulary is not None\n        else ""\n    )\n    role_label = (\n        resolve_vocab_label(vocabulary, "light_source_roles", role)\n        if role and vocabulary is not None\n        else ""\n    )\n\n    position: dict[str, Any] = {\n''',
    )
    replace_once(
        path,
        '''        "type": kind,\n        "kind": kind,\n        "role": role,\n''',
        '''        "type": kind,\n        "kind": kind,\n        "kind_label": kind_label,\n        "role": role,\n        "role_label": role_label,\n''',
    )


def patch_event_labels() -> None:
    path = ROOT / "scripts" / "dashboard" / "site_render.py"
    replace_once(
        path,
        '''def build_event_display(\n    payload: dict[str, Any],\n    *,\n    vocabulary: Any,\n    event_date: str,\n    instrument_display_name: str,\n) -> dict[str, str]:\n''',
        '''def build_event_display(\n    payload: dict[str, Any],\n    *,\n    vocabulary: Any,\n    event_date: str,\n    instrument_display_name: str,\n) -> dict[str, Any]:\n''',
    )
    replace_once(
        path,
        '''    return {\n        "record_type_label": record_type_label,\n        "reason_label": reason_label or "—",\n        # Both fields are vocabulary-backed in schema/maintenance_policy.yaml.\n        "service_provider_label": vocab_display(\n            "service_provider", payload.get("service_provider")\n        ) or "—",\n        "status_after_label": vocab_display(\n            "maintenance_status", payload.get("microscope_status_after")\n        ),\n        "instrument_display_name": instrument_display_name,\n        "page_title": " · ".join(part for part in (record_type_label, event_date) if part),\n    }\n''',
        '''    performed_display: list[dict[str, str]] = []\n    for task in payload.get("performed") or []:\n        if not isinstance(task, dict):\n            continue\n        performed_display.append(\n            {\n                "qc_type_label": vocab_display("qc_type", task.get("qc_type")) or "—",\n                "details": str(task.get("details") or "—"),\n            }\n        )\n\n    return {\n        "record_type_label": record_type_label,\n        "reason_label": reason_label or "—",\n        "action_label": vocab_display(\n            "maintenance_action", payload.get("action")\n        ) or "—",\n        # Both fields are vocabulary-backed in schema/maintenance_policy.yaml.\n        "service_provider_label": vocab_display(\n            "service_provider", payload.get("service_provider")\n        ) or "—",\n        "status_after_label": vocab_display(\n            "maintenance_status", payload.get("microscope_status_after")\n        ),\n        "performed": performed_display,\n        "instrument_display_name": instrument_display_name,\n        "page_title": " · ".join(part for part in (record_type_label, event_date) if part),\n    }\n''',
    )

    template = ROOT / "scripts" / "templates" / "event_detail.md.j2"
    replace_once(
        template,
        '''{% set maintenance_reason_details = payload.get('reason_details') or payload.get('reason') or '—' %}\n{% set maintenance_action_details = payload.get('action_details') or payload.get('action') or '—' %}\n''',
        '''{% set maintenance_reason_details = payload.get('reason_details') or display.reason_label or '—' %}\n{% set maintenance_action_details = payload.get('action_details') or display.action_label or '—' %}\n''',
    )
    replace_once(
        template,
        '''{% if payload.get('performed') %}\n## Tests performed\n\n| Test type | Details |\n|---|---|\n{% for task in payload.get('performed', []) %}| **{{ task.get('qc_type', '—') | replace('_', ' ') | title }}** | {{ task.get('details', '—') }} |\n{% endfor %}\n\n{% endif %}\n''',
        '''{% if display.performed %}\n## Tests performed\n\n| Test type | Details |\n|---|---|\n{% for task in display.performed %}| **{{ task.get('qc_type_label', '—') }}** | {{ task.get('details', '—') }} |\n{% endfor %}\n\n{% endif %}\n''',
    )


def patch_tests() -> None:
    path = ROOT / "tests" / "test_public_presentation_contracts.py"
    replace_once(
        path,
        '''        titles = set()\n        for page in pages:\n            first_lines = page.read_text(encoding="utf-8").splitlines()[:3]\n            title_line = next(line for line in first_lines if line.startswith("title:"))\n            title = title_line.split("title:", 1)[1].strip()\n            self.assertNotEqual(title, "Instrument details")\n            titles.add(title)\n        self.assertEqual(len(titles), len(pages))\n''',
        '''        for page in pages:\n            first_lines = page.read_text(encoding="utf-8").splitlines()[:3]\n            title_line = next(line for line in first_lines if line.startswith("title:"))\n            title = title_line.split("title:", 1)[1].strip()\n            self.assertTrue(title)\n            self.assertNotEqual(title, "Instrument details")\n''',
    )

    marker = '''    def test_virtual_microscope_survives_a_missing_chart_library(self) -> None:\n'''
    insert = '''    def test_objective_specialties_use_vocabulary_labels(self) -> None:\n        from scripts.dashboard.instrument_view import build_objective_dto\n        from scripts.validation.vocabulary import Vocabulary\n\n        dto = build_objective_dto(\n            Vocabulary(REPO_ROOT / "vocab"),\n            {\n                "model": "Example objective",\n                "specialties": ["correction_collar", "phase"],\n            },\n        )\n        rendered = "\\n".join(dto["spec_lines"])\n        self.assertIn("Correction Collar", rendered)\n        self.assertIn("Phase", rendered)\n        self.assertNotIn("correction_collar", rendered)\n\n    def test_virtual_microscope_source_cards_receive_vocabulary_labels(self) -> None:\n        from scripts.lightpath.model import get_active_vocab, set_active_vocab\n        from scripts.lightpath.spectral_ops import _source_position\n        from scripts.validation.vocabulary import Vocabulary\n\n        previous = get_active_vocab()\n        set_active_vocab(Vocabulary(REPO_ROOT / "vocab"))\n        try:\n            source = _source_position(\n                1,\n                {\n                    "kind": "white_light_laser",\n                    "role": "excitation",\n                    "tunable_min_nm": 470,\n                    "tunable_max_nm": 670,\n                },\n            )\n        finally:\n            set_active_vocab(previous)\n\n        self.assertEqual(source["kind_label"], "White Light Laser")\n        self.assertEqual(source["role_label"], "Excitation")\n\n    def test_virtual_microscope_route_tags_use_human_labels(self) -> None:\n        app_js = (\n            REPO_ROOT / "scripts" / "templates" / "virtual_microscope_app.js"\n        ).read_text(encoding="utf-8")\n        self.assertIn(\n            "normalizeSourceRoutes(source).map(normalizeRouteLabel)",\n            app_js,\n        )\n        self.assertNotIn(\n            "`routes: ${normalizeSourceRoutes(source).join(', ')}`",\n            app_js,\n        )\n\n'''
    text = path.read_text(encoding="utf-8")
    if text.count(marker) != 1:
        raise SystemExit(f"{path}: expected one developer-language marker")
    path.write_text(text.replace(marker, insert + marker, 1), encoding="utf-8")

    qc_path = ROOT / "tests" / "test_dashboard_qc_metrics.py"
    replace_once(
        qc_path,
        '''        qc_rendered = template.render(\n            event_id="2026-05-13_vendor_pm_qc",\n            date="2026-05-13",\n            instrument="scope-example",\n            instrument_id="scope-example",\n            operator="operator",\n            raw_yaml_content="record_type: qc_session",\n            payload=self.payload,\n            qc_metrics=build_qc_metric_view(self.payload),\n            qc_laser_context=build_qc_laser_context_view(self.payload),\n            display=build_event_display(\n                self.payload,\n                vocabulary=vocabulary,\n                event_date="2026-05-13",\n                instrument_display_name="Example Microscope",\n            ),\n        )\n''',
        '''        qc_payload = {\n            **self.payload,\n            "performed": [{"qc_type": "psf", "details": "PSF check"}],\n        }\n        qc_rendered = template.render(\n            event_id="2026-05-13_vendor_pm_qc",\n            date="2026-05-13",\n            instrument="scope-example",\n            instrument_id="scope-example",\n            operator="operator",\n            raw_yaml_content="record_type: qc_session",\n            payload=qc_payload,\n            qc_metrics=build_qc_metric_view(qc_payload),\n            qc_laser_context=build_qc_laser_context_view(qc_payload),\n            display=build_event_display(\n                qc_payload,\n                vocabulary=vocabulary,\n                event_date="2026-05-13",\n                instrument_display_name="Example Microscope",\n            ),\n        )\n''',
    )
    replace_once(
        qc_path,
        '''        self.assertIn("Example Microscope", qc_rendered)\n\n        maintenance_payload = {\n''',
        '''        self.assertIn("Example Microscope", qc_rendered)\n        self.assertIn("| **PSF** | PSF check |", qc_rendered)\n\n        maintenance_payload = {\n''',
    )
    replace_once(
        qc_path,
        '''            "service_provider": "vendor",\n            "microscope_status_after": "limited",\n''',
        '''            "service_provider": "vendor",\n            "action": "service",\n            "microscope_status_after": "limited",\n''',
    )
    replace_once(
        qc_path,
        '''        self.assertEqual(maintenance_display["service_provider_label"], "Vendor")\n        self.assertEqual(maintenance_display["status_after_label"], "Limited Service")\n''',
        '''        self.assertEqual(maintenance_display["service_provider_label"], "Vendor")\n        self.assertEqual(maintenance_display["action_label"], "Service")\n        self.assertEqual(maintenance_display["status_after_label"], "Limited Service")\n''',
    )


def main() -> None:
    patch_objective_labels()
    patch_vm_source_labels()
    patch_event_labels()
    patch_tests()


if __name__ == "__main__":
    main()
