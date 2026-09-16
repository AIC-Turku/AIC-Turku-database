"""Adversarial regressions for the explicit method-to-light-path contract.

Each case mutates one real instrument record and runs the real validator, so the
assertions describe the authoring rules a curator actually meets rather than a
synthetic policy fixture.
"""
from __future__ import annotations

import copy
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.validation.instrument import validate_instrument_ledgers


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_INSTRUMENT = REPO_ROOT / "instruments" / "Zeiss TIRF.yaml"


class MethodPathValidationRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = yaml.safe_load(BASE_INSTRUMENT.read_text(encoding="utf-8"))

    def _run(self, mutate) -> tuple[set[str], set[str]]:
        payload = copy.deepcopy(self.base)
        mutate(payload)
        tmp = Path(tempfile.mkdtemp())
        try:
            instruments = tmp / "instruments"
            instruments.mkdir()
            (instruments / "Case.yaml").write_text(
                yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
            )
            previous = Path.cwd()
            os.chdir(REPO_ROOT)
            try:
                _, issues, warnings = validate_instrument_ledgers(instruments_dir=instruments)
            finally:
                os.chdir(previous)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return {i.code for i in issues}, {w.code for w in warnings}

    def test_unmodified_record_is_clean(self) -> None:
        errors, _ = self._run(lambda payload: None)
        self.assertNotIn("capability_method_unmapped", errors)
        self.assertNotIn("light_path_method_not_declared", errors)
        self.assertNotIn("light_path_method_route_incompatible", errors)

    def test_declared_capability_must_be_mapped_to_a_path(self) -> None:
        errors, _ = self._run(lambda payload: payload["capabilities"]["imaging_modes"].append("sim"))
        self.assertIn("capability_method_unmapped", errors)

    def test_mapped_method_must_be_a_declared_capability(self) -> None:
        errors, _ = self._run(lambda payload: payload["light_paths"][0]["imaging_modes"].append("smlm"))
        self.assertIn("light_path_method_not_declared", errors)

    def test_method_must_be_compatible_with_its_route_family(self) -> None:
        errors, _ = self._run(
            lambda payload: payload["light_paths"][1].__setitem__("imaging_modes", ["tirf"])
        )
        self.assertIn("light_path_method_route_incompatible", errors)

    def test_illumination_without_detection_is_reported(self) -> None:
        """A path that cannot detect cannot implement the method it claims.

        Requiring both halves to be empty let a half-recorded path pass silently.
        """
        _, warnings = self._run(
            lambda payload: payload["light_paths"][1].__setitem__("detection_sequence", [])
        )
        self.assertIn("method_path_topology_empty", warnings)

    def test_detection_without_illumination_is_reported(self) -> None:
        _, warnings = self._run(
            lambda payload: payload["light_paths"][1].__setitem__("illumination_sequence", [])
        )
        self.assertIn("method_path_topology_empty", warnings)

    def test_mapped_path_without_a_known_route_family_is_refused(self) -> None:
        """Compatibility cannot be checked against a family the vocabulary lacks.

        Leaving this unchecked meant omitting `route_type` silently disabled the
        route-compatibility gate for that path.
        """

        def mutate(payload):
            path = payload["light_paths"][0]
            path.pop("route_type", None)
            path["id"] = "my_custom_path"
            path["imaging_modes"] = ["sted"]
            payload["capabilities"]["imaging_modes"].append("sted")

        errors, _ = self._run(mutate)
        self.assertIn("method_path_route_type_unresolved", errors)


class RouteVocabularyPortabilityRegressions(unittest.TestCase):
    """A forked facility must not be forced to author AIC-specific metadata."""

    def _validate_with_route_vocab(self, mutate_terms) -> set[str]:
        source = REPO_ROOT / "vocab" / "optical_routes.yaml"
        original = source.read_text(encoding="utf-8")
        data = yaml.safe_load(original)
        mutate_terms(data["terms"])
        source.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        try:
            previous = Path.cwd()
            os.chdir(REPO_ROOT)
            try:
                _, issues, _ = validate_instrument_ledgers(instruments_dir=REPO_ROOT / "instruments")
            finally:
                os.chdir(previous)
        finally:
            source.write_text(original, encoding="utf-8")
        return {i.code for i in issues}

    def test_route_term_without_covers_metadata_skips_the_compatibility_check(self) -> None:
        def mutate(terms):
            for term in terms:
                if term["id"] == "widefield_fluorescence":
                    term.pop("covers", None)

        self.assertNotIn("light_path_method_route_incompatible", self._validate_with_route_vocab(mutate))

    def test_covers_authored_for_one_axis_only_leaves_the_other_axis_unchecked(self) -> None:
        """An axis a term does not mention is unknown, not "covers nothing"."""

        def mutate(terms):
            for term in terms:
                if term["id"] == "transmitted_light":
                    term["covers"] = {"imaging_modes": []}

        self.assertNotIn("light_path_method_route_incompatible", self._validate_with_route_vocab(mutate))

    def test_an_explicitly_empty_axis_still_rejects_methods(self) -> None:
        """`contrast_methods: []` is an authored statement and must be enforced."""

        def mutate(terms):
            for term in terms:
                if term["id"] == "transmitted_light":
                    term["covers"] = {"imaging_modes": [], "contrast_methods": []}

        self.assertIn("light_path_method_route_incompatible", self._validate_with_route_vocab(mutate))


class MethodPathMappingIsReviewableRegressions(unittest.TestCase):
    """The authored mapping must be visible outside the YAML file.

    A curator checking whether `ism` really belongs on the confocal path should
    not have to read `instruments/*.yaml`; family coverage alone answers a weaker
    question ("is it compatible?") than the mapping does ("which path records it?").
    """

    def test_llm_export_states_the_method_to_path_mapping(self) -> None:
        from scripts.dashboard.llm_export import _build_capability_route_reconciliation

        reconciliation = _build_capability_route_reconciliation(
            {"imaging_modes": ["tirf", "smlm"]},
            ["widefield_fluorescence"],
            {"widefield_fluorescence": {"covers_imaging_modes": ["tirf", "smlm"]}},
            [
                {
                    "id": "widefield_fluorescence",
                    "imaging_modes": ["tirf", "smlm"],
                    "contrast_methods": [],
                }
            ],
        )
        self.assertEqual(
            reconciliation["methods_by_recorded_light_path"],
            {"widefield_fluorescence": ["tirf", "smlm"]},
        )

    def test_instrument_page_template_renders_the_mapping(self) -> None:
        template = (REPO_ROOT / "scripts" / "templates" / "instrument_spec.md.j2").read_text(encoding="utf-8")
        self.assertIn("Methods and the light path that records them", template)
        self.assertIn("route.imaging_modes", template)
        self.assertIn("route.contrast_methods", template)


if __name__ == "__main__":
    unittest.main()
