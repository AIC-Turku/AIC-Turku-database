"""Regressions for the facts a Methods draft must carry about the light path.

These exercise the real instrument ledger through the real export, rather than a
hand-written DTO. The defects they pin were all invisible to the existing browser
tests because those tests supply `selectable_positions` with a `display_label`
already filled in, so the code that derives that label from YAML never ran.
"""
from __future__ import annotations

import unittest
from pathlib import Path

import yaml

from scripts.dashboard.instrument_view import build_objective_dto
from scripts.dashboard.optical_path_view import _selectable_positions_by_component
from scripts.lightpath.vm_payload import generate_virtual_microscope_payload
from scripts.validate import Vocabulary


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTRUMENTS_DIR = REPO_ROOT / "instruments"


def _vocabulary() -> Vocabulary:
    policy = yaml.safe_load((REPO_ROOT / "schema" / "instrument_policy.yaml").read_text(encoding="utf-8")) or {}
    return Vocabulary(vocab_registry=policy.get("vocab_registry") or {})


def _iter_active_instruments():
    for path in sorted(INSTRUMENTS_DIR.glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(payload, dict):
            yield path, payload


class PositionIdentityRegressions(unittest.TestCase):
    """A selectable position must identify the filter, never its holder."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.positions_by_instrument: dict[str, dict[str, list[dict]]] = {}
        cls.holder_labels: dict[str, dict[str, str]] = {}
        for path, payload in _iter_active_instruments():
            # The VM payload is the canonical stage that carries selected_execution,
            # which is where available_positions (and therefore identity) lives.
            light_paths = (generate_virtual_microscope_payload(payload) or {}).get("light_paths") or []
            positions = _selectable_positions_by_component(light_paths)
            if not positions:
                continue
            cls.positions_by_instrument[path.stem] = positions
            holders: dict[str, str] = {}
            for route in light_paths:
                execution = route.get("selected_execution") or {}
                for step in execution.get("selected_route_steps") or []:
                    if not isinstance(step, dict):
                        continue
                    inventory_id = str(step.get("hardware_inventory_id") or "").strip()
                    label = str(step.get("display_label") or "").strip()
                    if inventory_id and label:
                        holders.setdefault(inventory_id, label)
            cls.holder_labels[path.stem] = holders

    def test_position_label_is_never_the_holder_label(self) -> None:
        """"the Emission Filter Wheel in the Emission Filter Wheel" is not a fact.

        The holder names the container; the position names the filter that was
        actually in the path, which is the fact a fluorescence Methods section
        turns on.
        """
        leaks = []
        for stem, by_component in self.positions_by_instrument.items():
            holders = self.holder_labels.get(stem, {})
            for inventory_id, rows in by_component.items():
                holder = holders.get(inventory_id, "")
                for row in rows:
                    if holder and row["display_label"] == holder:
                        leaks.append((stem, inventory_id, row["id"], row["display_label"]))
        self.assertEqual(leaks, [], f"position labels collapsed to their holder: {leaks}")

    def test_recorded_filter_identities_survive_into_the_position_label(self) -> None:
        """Spot-check identities that a holder-name fallback silently swallowed."""
        expected = {
            ("Abberior STED", "optical_path_element:emission_filter_wheel", "Pos_1"): "525/25",
            ("Abberior STED", "optical_path_element:emission_filter_wheel", "Pos_3"): "685/35",
            ("Nikon Ti2-E Crest V3 Spinning Disk", "optical_path_element:crest_emission_wheel", "Pos_3"): "438/24",
            ("3i CSU-W1 Spinning Disk", "optical_path_element:xled_excitation_filters", "Pos_1"): "387/11",
            # Authored `model` on a filter-cube position must win over the turret name.
            ("Leica STELLARIS 8 FALCON FLIM", "optical_path_element:epi_filter_cube_turret", "led_405_cube"): "Filter cube LED 405",
        }
        for (stem, inventory_id, position_id), want in expected.items():
            rows = self.positions_by_instrument.get(stem, {}).get(inventory_id, [])
            found = {row["id"]: row["display_label"] for row in rows}
            self.assertIn(position_id, found, f"{stem}/{inventory_id}: {position_id} not offered")
            self.assertEqual(found[position_id], want, f"{stem}/{inventory_id}:{position_id}")

    def test_positions_of_one_holder_stay_distinguishable(self) -> None:
        """Two slots a user must choose between cannot render as the same label.

        A bare brightfield position and one carrying a polariser both record no
        filter; collapsing both to "Empty" makes the choice unanswerable.
        """
        collisions = []
        for stem, by_component in self.positions_by_instrument.items():
            for inventory_id, rows in by_component.items():
                seen: dict[str, str] = {}
                for row in rows:
                    label = row["display_label"]
                    if label in seen:
                        collisions.append((stem, inventory_id, seen[label], row["id"], label))
                    seen[label] = row["id"]
        self.assertEqual(collisions, [], f"indistinguishable positions: {collisions}")

    def test_key_only_positions_are_not_presented_as_an_identity(self) -> None:
        """A bare slot key is a distinguishable last resort, not a recorded identity."""
        for stem, by_component in self.positions_by_instrument.items():
            for rows in by_component.values():
                for row in rows:
                    if row["display_label"] == row["id"]:
                        self.assertFalse(
                            row["has_identity"],
                            f"{stem}: {row['id']} presents its slot key as an identity",
                        )

    def test_equivalent_position_on_two_routes_unions_route_membership(self) -> None:
        """Deduplication must preserve every route that records the same filter identity."""
        holder_id = "optical_path_element:test_wheel"

        def route(route_id: str, position_key: str) -> dict:
            return {
                "id": route_id,
                "display_label": route_id,
                "selected_execution": {
                    "selected_route_steps": [
                        {
                            "hardware_inventory_id": holder_id,
                            "display_label": "Test emission wheel",
                            "available_positions": [
                                {
                                    "position_key": position_key,
                                    "name": "525/25",
                                    "product_code": "ET525/25",
                                    "component_type": "filter",
                                    "selection_mode": "exclusive",
                                }
                            ],
                        }
                    ]
                },
            }

        rows = _selectable_positions_by_component([route("route-a", "slot-a"), route("route-b", "slot-b")])[holder_id]
        self.assertEqual(len(rows), 1)
        self.assertEqual(set(rows[0]["route_ids"]), {"route-a", "route-b"})
        self.assertEqual(set(rows[0]["route_labels"]), {"route-a", "route-b"})


class PublicationProseRegressions(unittest.TestCase):
    """Prose built from the real ledger must not contain generic filler."""

    FALLBACK_NOUNS = ("objective", "scanner", "camera", "detector", "module", "optical element")

    def test_no_generic_fallback_noun_is_published_as_an_identity(self) -> None:
        """"a 10x/0.3 Air objective (objective)" is noise, not a component.

        When every recorded identity field is a placeholder the parenthetical is
        dropped; the review block asks for the missing manufacturer and model.
        """
        vocabulary = _vocabulary()
        offenders = []
        for path, payload in _iter_active_instruments():
            for objective in ((payload.get("hardware") or {}).get("objectives") or []):
                if not isinstance(objective, dict):
                    continue
                dto = build_objective_dto(vocabulary, objective)
                sentence = str(dto.get("method_sentence") or "")
                phrase = str(dto.get("publication_phrase") or "")
                for noun in self.FALLBACK_NOUNS:
                    if f"({noun})" in sentence or f"({noun})" in phrase:
                        offenders.append((path.stem, sentence or phrase))
        self.assertEqual(offenders, [], f"fallback noun published as an identity: {offenders}")


if __name__ == "__main__":
    unittest.main()
