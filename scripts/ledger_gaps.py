"""Derive the open ledger questions from the instrument records.

`docs/ledger_gaps.md` lists what the YAML records do not yet say, grouped by the
question a facility staff member would have to answer. It exists because those
gaps are what the public tools cannot work around: a light source with no recorded
role makes the Methods draft ask the author what the source was for, and a
detector no light path reaches cannot be reported at all.

The file is generated so it cannot drift from the records. Run this after changing
an instrument ledger and commit the result; `--check` fails when the committed file
no longer matches the YAML, which is what CI and reviewers use.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "docs" / "ledger_gaps.md"

# Values that record the absence of a fact rather than a fact.
PLACEHOLDERS = {"unknown", "placeholder", "n/a", "na", "none", "-", "--", "?", ""}


def is_placeholder(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text in PLACEHOLDERS or text.startswith("unknown") or text.startswith("placeholder")


def clean(value: Any) -> str:
    return str(value or "").strip()


# A position that does not shape a passband has no bands to record. Asking a DIC
# analyser for its excitation band is not a gap, it is a category error, and it
# made the reported total larger than the number of real questions.
SPECTRAL_COMPONENT_TYPES = {
    "filter_cube", "cube", "excitation_filter", "emission_filter", "dichroic",
    "multiband_dichroic", "polychroic", "bandpass", "longpass", "shortpass",
    "notch", "beamsplitter",
}

# The shapes an authored passband takes. A dichroic records an edge, not a band; a
# filter cube records its spectra on the sub-components. Reading only a top-level
# `bands` list reported nine fully specified cubes and two longpass filters with a
# recorded cut-on as unanswered.
SPECTRAL_KEYS = ("bands", "cut_on_nm", "cutoffs_nm", "center_nm", "width_nm")
NESTED_COMPONENT_KEYS = ("excitation_filter", "dichroic", "emission_filter")


def has_spectral_detail(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    return any(payload.get(key) for key in SPECTRAL_KEYS)


def position_spectrum_is_missing(position: dict[str, Any]) -> bool:
    """True when a position that should carry a passband records none."""
    component_type = clean(position.get("component_type")).lower()
    if component_type not in SPECTRAL_COMPONENT_TYPES:
        return False
    if has_spectral_detail(position):
        return False
    return not any(has_spectral_detail(position.get(key)) for key in NESTED_COMPONENT_KEYS)


# A holder whose every recorded position selects a fluorescence band cannot be set
# to anything a brightfield or phase-contrast acquisition could have used.
FLUORESCENCE_PASSBAND_TYPES = {
    "bandpass", "multiband_bandpass", "longpass", "shortpass", "notch",
}
FLUORESCENCE_STAGE_ROLES = {"excitation", "emission", "cube"}


def element_ids_on_route(light_path: dict[str, Any]) -> set[str]:
    found: set[str] = set()

    def walk(items: Any) -> None:
        for item in items or []:
            if not isinstance(item, dict):
                continue
            element_id = clean(item.get("optical_path_element_id"))
            if element_id:
                found.add(element_id)
            branches = item.get("branches")
            if isinstance(branches, dict):
                for branch in branches.get("items") or []:
                    if isinstance(branch, dict):
                        walk(branch.get("sequence"))

    walk(light_path.get("illumination_sequence"))
    walk(light_path.get("detection_sequence"))
    return found


def holder_cannot_serve_route(element: dict[str, Any]) -> bool:
    """True when every recorded position selects a fluorescence band."""
    if clean(element.get("stage_role")).lower() not in FLUORESCENCE_STAGE_ROLES:
        return False
    positions = element.get("positions") or {}
    if not isinstance(positions, dict) or not positions:
        return False
    return all(
        isinstance(position, dict)
        and clean(position.get("component_type")).lower() in FLUORESCENCE_PASSBAND_TYPES
        for position in positions.values()
    )


def instrument_files() -> list[Path]:
    active = sorted((REPO_ROOT / "instruments").glob("*.yaml"))
    retired = sorted((REPO_ROOT / "instruments" / "retired").glob("*.yaml"))
    return [path for path in active + retired if "Test_Scope" not in path.name]


def collect_gaps() -> dict[str, dict[str, list[str]]]:
    gaps: dict[str, dict[str, list[str]]] = collections.defaultdict(lambda: collections.defaultdict(list))
    for path in instrument_files():
        record = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        identity = record.get("instrument") or {}
        name = clean(identity.get("display_name")) or path.stem
        hardware = record.get("hardware") or {}

        for source in hardware.get("sources") or []:
            if clean(source.get("role")):
                continue
            label = " ".join(
                clean(part)
                for part in (source.get("wavelength_nm"), source.get("kind"),
                             source.get("manufacturer"), source.get("model"))
                if clean(part)
            )
            gaps["source_role"][name].append(label or clean(source.get("id")))

        detectors = hardware.get("detectors") or []
        for detector in detectors:
            if is_placeholder(detector.get("manufacturer")) or is_placeholder(detector.get("model")):
                gaps["detector_identity"][name].append(
                    f"{clean(detector.get('manufacturer')) or '(no manufacturer)'} / "
                    f"{clean(detector.get('model')) or '(no model)'}"
                )
        labels = [f"{clean(d.get('manufacturer'))} {clean(d.get('model'))}".strip() for d in detectors]
        for label, count in collections.Counter(labels).items():
            if count > 1 and label:
                gaps["detector_duplicate"][name].append(f"{label} ×{count}")

        # A detector no light path terminates at cannot be selected, so an
        # acquisition that used it cannot report it.
        referenced = set(re.findall(r'"endpoint_id":\s*"([^"]+)"', json.dumps(record.get("light_paths"))))
        for detector in detectors:
            detector_id = clean(detector.get("id"))
            if detector_id and detector_id not in referenced:
                gaps["detector_unreachable"][name].append(
                    f"{detector_id} ({clean(detector.get('model')) or 'no model'})"
                )

        for objective in hardware.get("objectives") or []:
            if is_placeholder(objective.get("manufacturer")) or is_placeholder(objective.get("model")):
                gaps["objective_identity"][name].append(
                    f"{clean(objective.get('manufacturer'))}/{clean(objective.get('model'))}"
                )

        for module in record.get("modules") or []:
            if is_placeholder(module.get("model")):
                gaps["module_model"][name].append(
                    f"{clean(module.get('type'))} ({clean(module.get('manufacturer')) or 'no manufacturer'})"
                )

        scanner = hardware.get("scanner") or {}
        scanner_type = clean(scanner.get("type"))
        if scanner_type and scanner_type != "none" and (
            is_placeholder(scanner.get("manufacturer")) or is_placeholder(scanner.get("model"))
        ):
            gaps["scanner_identity"][name].append(f"type={scanner_type}")

        software = record.get("software") or []
        acquisition = [row for row in software if clean(row.get("role")).lower() == "acquisition"]
        # `software_status: not_applicable` is the recorded answer to this question:
        # a manual stand with no acquisition software. Asking anyway turned three
        # answered records into open questions for staff.
        software_status = clean(record.get("software_status")).lower()
        if not acquisition and software_status != "not_applicable":
            gaps["no_acquisition_software"][name].append("no row with role: acquisition")
        for row in acquisition:
            if is_placeholder(row.get("name")):
                gaps["software_name"][name].append("role: acquisition recorded with no name")
            elif is_placeholder(row.get("version")):
                gaps["software_version"][name].append(clean(row.get("name")))

        if clean(identity.get("stand_orientation")).lower() in {"other", "unknown", ""}:
            gaps["stand_orientation"][name].append(clean(identity.get("stand_orientation")) or "(unset)")

        elements_by_id = {
            clean(element.get("id")): element
            for element in hardware.get("optical_path_elements") or []
            if isinstance(element, dict) and clean(element.get("id"))
        }
        for light_path in record.get("light_paths") or []:
            if not isinstance(light_path, dict):
                continue
            if [mode for mode in (light_path.get("imaging_modes") or []) if clean(mode)]:
                continue
            route_label = clean(light_path.get("route_type")) or clean(light_path.get("id"))
            for element_id in sorted(element_ids_on_route(light_path)):
                element = elements_by_id.get(element_id)
                if not element or not holder_cannot_serve_route(element):
                    continue
                gaps["route_position_mismatch"][name].append(
                    f"{clean(element.get('name')) or element_id} on the {route_label} path"
                )

        for element in hardware.get("optical_path_elements") or []:
            for key, position in (element.get("positions") or {}).items():
                if not isinstance(position, dict):
                    continue
                if not position_spectrum_is_missing(position):
                    continue
                gaps["filter_bands"][name].append(
                    f"{clean(element.get('name')) or clean(element.get('id'))} / "
                    f"{clean(position.get('name')) or key}"
                )
    return gaps


# Each gap, in the words of the question a staff member has to answer, with why it
# matters where the consequence is not obvious from the field name.
SECTIONS: list[tuple[str, str, str]] = [
    ("source_role", "Light-source role",
     "For each recorded source, what is its role on the light path: excitation, "
     "transmitted illumination, reflected illumination, depletion, activation or "
     "alignment?\n\nThis is the single request that still appears on an otherwise "
     "complete Methods draft. Without it the generator cannot say whether a line "
     "excited the sample or illuminated it, so it asks the author instead, and the "
     "illumination verb differs between instruments for identical physics."),
    ("detector_identity", "Detector identity",
     "Which detector or camera is this, by manufacturer and model?\n\nA recorded "
     "`Unknown` is the record saying it does not know, so the Methods draft omits "
     "the detector from the prose and asks for it."),
    ("detector_unreachable", "Detectors no light path reaches",
     "Should a light path terminate at these detectors, and through which "
     "branches?\n\nThey are recorded hardware, but no `light_paths[].endpoint_id` "
     "names them, so no tool can offer them. An acquisition that used one cannot "
     "report it."),
    ("detector_duplicate", "Detectors recorded under one name",
     "Do these detectors have port or channel names that can be recorded?\n\nTwo "
     "cameras sharing a manufacturer and model are told apart only by their branch "
     "labels. Where a branch label exists the draft uses it; where it does not, the "
     "draft has to ask which camera served which channel."),
    ("objective_identity", "Objective identity",
     "Which objective is installed, by manufacturer and model?"),
    ("module_model", "Module model",
     "Which model is this module?"),
    ("scanner_identity", "Scanner identity",
     "Is the scanner a named unit (for example a Yokogawa CSU-W1 or a CrestOptics "
     "X-Light V3), or should it inherit the instrument's manufacturer?\n\nWithout "
     "this the draft asks for the manufacturer of, say, a Leica tandem scanner on a "
     "Leica system, which reads oddly to an author."),
    ("software_name", "Acquisition software not named",
     "What acquisition software is installed, and which version?\n\nA row recorded "
     "as `role: acquisition` with no name means the instrument offers the user no "
     "software checkbox at all, so a draft from it cannot state how the images were "
     "acquired."),
    ("no_acquisition_software", "No acquisition software recorded",
     "Is there acquisition software on this stand?\n\nIf there genuinely is none — a "
     "visual stand, or a standalone camera — recording that explicitly is more "
     "useful than leaving it blank, because the tools can then stop asking."),
    ("software_version", "Acquisition software version",
     "Which version is installed?\n\nA version recorded as not tracked is more "
     "useful than an empty string, for the same reason."),
    ("stand_orientation", "Stand orientation",
     "Is there a better vocabulary term than `other` for this stand?"),
    ("route_position_mismatch", "Filter holders no recorded position can serve",
     "Does this path really pass through this holder, and if it does, what is it set "
     "to for a non-fluorescence acquisition?\n\nEvery recorded position in the holder "
     "selects a fluorescence band, but the path it is recorded on declares no "
     "fluorescence imaging mode. Either the path does not pass through the holder, or "
     "the holder has an open position that is not written down. Until this is "
     "resolved the Methods draft offers no position for that path, because none of "
     "the recorded ones could be the answer."),
    ("filter_bands", "Filter positions with no transmission bands",
     "For each position: what are the excitation band, dichroic edge and emission "
     "band, and the manufacturer and catalogue number?\n\nThe Methods draft prints "
     "what a filter passes when the bands are recorded and only its catalogue "
     "number when they are not, so these positions produce the least useful "
     "sentences in a fluorescence draft."),
]


def render(gaps: dict[str, dict[str, list[str]]]) -> str:
    total = sum(len(items) for section in gaps.values() for items in section.values())
    lines = [
        "# Open ledger questions",
        "",
        "<!-- Generated by scripts/ledger_gaps.py. Do not edit by hand. -->",
        "",
        "What the instrument records do not yet say, grouped by the question a staff",
        "member would have to answer. These are the gaps the public tools cannot work",
        "around: they are why a Methods draft asks the author to confirm something, or",
        "cannot describe a component at all.",
        "",
        "Nothing here should be filled in by assumption. Where a field is genuinely not",
        "applicable, recording that explicitly is better than leaving it blank, because",
        "the tools can then stop asking.",
        "",
        f"**{total} open questions across {len(instrument_files())} records.**",
        "",
        "Regenerate with `python -m scripts.ledger_gaps` after changing any instrument",
        "ledger; `python -m scripts.ledger_gaps --check` fails when this file is stale.",
        "",
    ]
    for key, heading, question in SECTIONS:
        section = gaps.get(key) or {}
        if not section:
            continue
        count = sum(len(items) for items in section.values())
        lines.append(f"## {heading}")
        lines.append("")
        lines.append(f"{question}")
        lines.append("")
        lines.append(f"{count} across {len(section)} record{'s' if len(section) != 1 else ''}:")
        lines.append("")
        for name in sorted(section):
            items = section[name]
            shown = "; ".join(items[:6])
            if len(items) > 6:
                shown += f"; … (+{len(items) - 6} more)"
            lines.append(f"- **{name}** — {shown}")
        lines.append("")
    if not any(gaps.values()):
        lines.append("No open questions: every checked field is recorded.")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="Fail if docs/ledger_gaps.md no longer matches the instrument records.")
    args = parser.parse_args()

    output = render(collect_gaps())
    if args.check:
        existing = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
        if existing != output:
            print(f"{OUTPUT_PATH.relative_to(REPO_ROOT)} is out of date.")
            print("Run `python -m scripts.ledger_gaps` and commit the result.")
            return 1
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(output, encoding="utf-8")
    print(f"Generated {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
