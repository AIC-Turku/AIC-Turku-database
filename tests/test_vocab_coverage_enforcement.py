"""Vocabulary coverage enforcement tests (PR 7).

These tests catch vocabulary coverage gaps before they reach production.
They verify that:
1. All capabilities.* terms used in active YAMLs exist in their respective vocab file.
2. All modules[].type values used in active YAMLs exist in vocab/modules.yaml.
3. No active YAML contains a hardware.*.modalities field (removed in PR 4).
4. vocab/modules.yaml uses provides_capability, not the deprecated provides_modality.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTRUMENTS_DIR = REPO_ROOT / "instruments"
VOCAB_DIR = REPO_ROOT / "vocab"

# Map each capabilities axis to the vocab file that owns its terms.
_CAPABILITIES_AXIS_VOCAB: dict[str, Path] = {
    "imaging_modes": VOCAB_DIR / "imaging_modes.yaml",
    "contrast_methods": VOCAB_DIR / "contrast_methods.yaml",
    "assay_operations": VOCAB_DIR / "assay_operations.yaml",
    "readouts": VOCAB_DIR / "measurement_readouts.yaml",
    "workflows": VOCAB_DIR / "workflow_tags.yaml",
    "non_optical": VOCAB_DIR / "non_optical_capabilities.yaml",
}


def _load_vocab_ids(vocab_path: Path) -> set[str]:
    """Return the set of canonical IDs from a standard vocab file."""
    data = yaml.safe_load(vocab_path.read_text(encoding="utf-8"))
    return {
        t["id"]
        for t in data.get("terms", [])
        if isinstance(t, dict) and t.get("id")
    }


def _active_instrument_yamls() -> list[Path]:
    """Return all non-retired instrument YAML paths."""
    return [
        p
        for p in sorted(INSTRUMENTS_DIR.rglob("*.yaml"))
        if "retired" not in p.parts
    ]


def _load_yaml_safe(path: Path) -> dict[str, Any] | None:
    """Load YAML; return None on YAML parse error or non-dict content."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


class VocabCoverageEnforcementTests(unittest.TestCase):
    """Enforcement tests: vocabulary coverage gaps must not reach production."""

    def test_all_capabilities_terms_in_active_yamls_are_in_vocab(self) -> None:
        """All capabilities.* terms used in active YAMLs must appear in their vocab file.

        For each axis (imaging_modes, contrast_methods, assay_operations, readouts,
        workflows, non_optical) every term referenced in an active instrument YAML
        must exist as a canonical ID in the corresponding vocab file.
        """
        # Pre-load canonical IDs for each axis.
        axis_ids: dict[str, set[str]] = {
            axis: _load_vocab_ids(vocab_path)
            for axis, vocab_path in _CAPABILITIES_AXIS_VOCAB.items()
        }

        violations: list[str] = []

        for yaml_path in _active_instrument_yamls():
            data = _load_yaml_safe(yaml_path)
            if data is None:
                continue
            caps = data.get("capabilities")
            if not isinstance(caps, dict):
                continue

            for axis, valid_ids in axis_ids.items():
                terms = caps.get(axis)
                if not isinstance(terms, list):
                    continue
                for term in terms:
                    if term not in valid_ids:
                        vocab_file = _CAPABILITIES_AXIS_VOCAB[axis].name
                        violations.append(
                            f"{yaml_path.name}: capabilities.{axis}['{term}'] "
                            f"not found in {vocab_file}"
                        )

        self.assertEqual(
            violations,
            [],
            "capabilities.* terms used in active YAMLs must exist in their vocab:\n"
            + "\n".join(violations),
        )

    def test_all_module_types_in_active_yamls_are_in_modules_vocab(self) -> None:
        """All modules[].type values used in active YAMLs must exist in vocab/modules.yaml."""
        modules_vocab_path = VOCAB_DIR / "modules.yaml"
        valid_module_ids = _load_vocab_ids(modules_vocab_path)

        violations: list[str] = []

        for yaml_path in _active_instrument_yamls():
            data = _load_yaml_safe(yaml_path)
            if data is None:
                continue
            modules = data.get("modules")
            if not isinstance(modules, list):
                continue
            for entry in modules:
                if not isinstance(entry, dict):
                    continue
                module_type = entry.get("type")
                if module_type and module_type not in valid_module_ids:
                    violations.append(
                        f"{yaml_path.name}: modules[].type '{module_type}' "
                        f"not found in {modules_vocab_path.name}"
                    )

        self.assertEqual(
            violations,
            [],
            "modules[].type values in active YAMLs must exist in vocab/modules.yaml:\n"
            + "\n".join(violations),
        )

    def test_no_active_yaml_has_hardware_modalities_field(self) -> None:
        """No active YAML may contain a hardware.*.modalities field.

        The modalities field was removed from all hardware sub-sections in PR 4.
        Any reintroduction must be caught here.
        """
        violations: list[str] = []

        for yaml_path in _active_instrument_yamls():
            data = _load_yaml_safe(yaml_path)
            if data is None:
                continue
            hardware = data.get("hardware")
            if not isinstance(hardware, dict):
                continue
            for section_key, section_val in hardware.items():
                if isinstance(section_val, dict) and "modalities" in section_val:
                    violations.append(
                        f"{yaml_path.name}: hardware.{section_key}.modalities is present"
                    )
                elif isinstance(section_val, list):
                    for idx, item in enumerate(section_val):
                        if isinstance(item, dict) and "modalities" in item:
                            violations.append(
                                f"{yaml_path.name}: hardware.{section_key}[{idx}].modalities is present"
                            )

        self.assertEqual(
            violations,
            [],
            "Active YAMLs must not contain hardware.*.modalities (removed in PR 4):\n"
            + "\n".join(violations),
        )

    def test_modules_yaml_uses_provides_capability_not_provides_modality(self) -> None:
        """vocab/modules.yaml must use provides_capability, not provides_modality.

        The provides_modality key was replaced by provides_capability in PR 2.
        Any reintroduction of provides_modality must be caught here.
        """
        modules_vocab_path = VOCAB_DIR / "modules.yaml"
        data = yaml.safe_load(modules_vocab_path.read_text(encoding="utf-8"))

        violations: list[str] = []
        for term in data.get("terms", []):
            if not isinstance(term, dict):
                continue
            tags = term.get("tags", {})
            if not isinstance(tags, dict):
                continue
            if "provides_modality" in tags:
                violations.append(
                    f"modules.yaml: term '{term.get('id')}' uses deprecated "
                    f"provides_modality instead of provides_capability"
                )

        self.assertEqual(
            violations,
            [],
            "vocab/modules.yaml must not use provides_modality (use provides_capability):\n"
            + "\n".join(violations),
        )


if __name__ == "__main__":
    unittest.main()
