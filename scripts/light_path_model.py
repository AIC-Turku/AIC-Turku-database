"""Derive the canonical light-path reference from the schema and the records.

`docs/light_path_model.md` is the developer reference for how light paths are
authored, validated, and consumed. Most of what such a document used to say by
hand — which fields exist, which are required, which vocabulary they draw on —
is already stated in `schema/instrument_policy.yaml`, and a hand-written copy of
it drifts the moment a rule changes. So the field inventory, the validator
diagnostics, and the DTO shape are generated from the code that defines them.

What stays authored here is what the schema cannot express: why `route_type` is
not a method, why an authored method-to-path mapping is required rather than
inferred, and which structures are deliberately not canonical. Those paragraphs
live in this module and are the only part a human edits.

The generated sections double as a drift report: fields authored in the ledgers
that no schema rule covers, and rules no record uses, are listed explicitly
rather than left to be discovered.

Run this after changing the schema, the light-path validator, the DTO builders,
or an instrument ledger, and commit the result; `--check` fails when the
committed file no longer matches, which is what CI and reviewers use.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "docs" / "light_path_model.md"
POLICY_PATH = REPO_ROOT / "schema" / "instrument_policy.yaml"
CANONICAL_SECTION = "canonical_light_paths_v2"

# Validator codes that belong to the light-path contract. Matched as substrings
# so a newly added code appears in the document without editing this list.
DIAGNOSTIC_MARKERS = (
    "light_path",
    "method_path",
    "capability_method",
    "capability_route",
    "route_readouts",
    "legacy_topology",
    "filter_cube",
    "sted_completeness",
)

DIAGNOSTIC_SOURCES = (
    REPO_ROOT / "scripts" / "validation",
    REPO_ROOT / "scripts" / "lightpath",
)

# One line per diagnostic, explaining what an author should do about it. A code
# with no entry is rendered with a placeholder, which is the signal to add one.
DIAGNOSTIC_NOTES = {
    "invalid_light_path": (
        "Hard error. The route structure itself is unusable — a sequence "
        "references an id that does not exist, or a tagged union entry carries "
        "no recognised key."
    ),
    "light_path_endpoint_warning": (
        "A route does not terminate at an explicit endpoint, so the DTO has to "
        "guess where the light ends up."
    ),
    "light_path_route_type_missing": (
        "A route declares no `route_type`. Suppressed when the record still "
        "carries the legacy `light_paths[].modalities` spelling, which is the "
        "only reason pre-`route_type` records still validate."
    ),
    "light_path_id_not_in_optical_routes": (
        "A route id that is not an `optical_routes` term, used where "
        "`route_type` was absent. Readout terms such as `flim` or `fcs` belong "
        "in `light_paths[].readouts`, not in the route id."
    ),
    "light_path_name_deprecated": (
        "`light_paths[].name` is deprecated on active instruments: the display "
        "label comes from `vocab/optical_routes.yaml` via `route_type`. Move "
        "anything meaningful to `notes`."
    ),
    "light_path_method_not_declared": (
        "A method is mapped to a light path but not declared in `capabilities`."
    ),
    "light_path_method_route_incompatible": (
        "A mapped method is not compatible with that path's route family "
        "according to `covers` in `vocab/optical_routes.yaml`."
    ),
    "capability_method_unmapped": (
        "A method declared in `capabilities` is mapped to no light path, so no "
        "tool can say which hardware performs it."
    ),
    "capability_route_uncovered": (
        "A declared capability matches no `light_paths[].route_type`."
    ),
    "instrument_readout_uncovered_by_route_readouts": (
        "A declared capability readout matches no `light_paths[].readouts` entry."
    ),
    "method_path_topology_empty": (
        "A path that maps methods records no illumination or no detection "
        "sequence, so the Methods draft has to ask the author what was used."
    ),
    "method_path_route_type_unresolved": (
        "A path that maps methods names a route family the vocabulary does not "
        "know, so compatibility cannot be checked at all."
    ),
    "legacy_topology_present": (
        "A migration-only field is still authored. Move it to "
        "`hardware.sources`, `hardware.optical_path_elements`, "
        "`hardware.endpoints`, and `light_paths`."
    ),
    "non_authoritative_filter_cube": (
        "Filter-cube detail is authored somewhere other than the canonical "
        "optical-path element positions."
    ),
    "sted_completeness_gap": (
        "A STED-capable record is missing the hardware facts a STED methods "
        "paragraph needs: a source with `role: depletion`, its `timing_mode`, "
        "or a detector with `supports_time_gating`."
    ),
}

GROUP_NOTES = {
    "hardware.sources": (
        "Installed illumination sources. The inventory `illumination_sequence[]` "
        "references; identity has to be stable enough for those references."
    ),
    "hardware.optical_path_elements": (
        "Installed mechanisms that alter or route light — excitation and "
        "emission filter wheels, cube turrets, dichroic mechanisms, selectors, "
        "splitters. Reusable nodes referenced by ordered route sequences. "
        "`positions{}` holds what is actually installed in each slot, which is "
        "where reported filter specs come from."
    ),
    "hardware.eyepieces": "Eyepiece inventory, normalised into endpoints.",
    "hardware.endpoints": (
        "Explicit route terminals: detector, camera-port, and eyepiece "
        "endpoints. Normalised together with `hardware.detectors[]` and "
        "`hardware.eyepieces[]` before DTO consumption."
    ),
    "hardware.detectors": (
        "Only the spectral-collection fields belong to the light-path contract; "
        "the rest of the detector record is defined in the `detectors` section."
    ),
    "light_paths": (
        "The ordered route declarations. Each one is a single explicit "
        "traversable path through the inventory, and they are the topology "
        "truth: nothing downstream may reconstruct routing from anywhere else."
    ),
}


# --------------------------------------------------------------------------
# authored prose — the only part of this document a human edits
# --------------------------------------------------------------------------

AUTHORED_SEMANTICS = [
    "## 3. What the schema cannot say",
    "",
    "The tables above say which fields exist. They cannot say how to read them, and",
    "every rule below exists because reading them the obvious way produced a wrong",
    "answer somewhere downstream.",
    "",
    "### A route family is not a technique",
    "",
    "`route_type` is the physical route family and must never be read as the method.",
    "A family is coarse: STED, RESOLFT and ISM all run on a `confocal_point` path,",
    "and TIRF, SIM and SMLM all run on a `widefield_fluorescence` path. Reading the",
    "family as the technique is how a Methods draft ends up calling a TIRF",
    "acquisition widefield.",
    "",
    "### Capability and implementation are separate statements",
    "",
    "`capabilities.imaging_modes` and `capabilities.contrast_methods` say what the",
    "instrument *can do*. `light_paths[].imaging_modes` and",
    "`light_paths[].contrast_methods` say *which physical path implements each one*.",
    "They are different claims and both are authored. `light_paths[].readouts` is the",
    "third: what a path measures — FLIM, FCS, spectral — as opposed to how it forms",
    "the image.",
    "",
    "### `covers` is a compatibility gate, not an implementation claim",
    "",
    "`covers` in `vocab/optical_routes.yaml` says a family *can* carry a method; it",
    "does not say this particular path does. What distinguishes STED from confocal,",
    "or SIM from widefield, is hardware the family does not capture, so the mapping is",
    "authored rather than inferred.",
    "",
    "A term that omits `covers` entirely, or omits one axis of it, leaves that axis",
    "unchecked. This is deliberate: a facility reusing this repository is not required",
    "to author AIC's coverage metadata. An axis written as an explicit empty list *is*",
    "an authored statement and is enforced.",
    "",
    "### Sequences are ordering, not membership",
    "",
    "`illumination_sequence[]` is the real traversal before the sample plane and",
    "`detection_sequence[]` the real traversal after it. They are ordered because the",
    "order is the physical fact being recorded; a consumer that treats either as a set",
    "has discarded the part that mattered.",
    "",
    "### `modalities` are validation aids, never topology",
    "",
    "`modalities` on `hardware.sources`, `hardware.optical_path_elements` or",
    "`hardware.endpoints` may be used to sanity-check route membership and to catch",
    "invalid route assignments. They must not be treated as the primary topology",
    "definition. Where sequence ordering and modality hints disagree, the ordered route",
    "declarations win and the disagreement is a validation finding.",
    "",
    "`light_paths[].modalities` is something else again: the pre-`route_type` spelling.",
    "The parser still reads it — it surfaces as `_legacy_route_modalities` and is used",
    "to attribute hardware to routes — and its presence suppresses",
    "`light_path_route_type_missing`. But a record still using it declares no route",
    "family, so no method can be mapped to that path and no tool can name the",
    "technique it implements.",
    "",
    "### The fork belongs to the route, not to the hardware",
    "",
    "Branching is explicitly representable, but the fork is owned by `light_paths`:",
    "",
    "- only `light_paths[].detection_sequence[]` items carry a tagged `branches` block;",
    "- each block declares `selection_mode` and `items[]`;",
    "- each item declares `branch_id`, an optional `label`, and a linear `sequence[]`;",
    "- branch-local sequences may add further `optical_path_element_id` entries and",
    "  terminate at an explicit `endpoint_id` when the downstream endpoint is known;",
    "- nested branch blocks inside branch-local sequences are out of scope.",
    "",
    "```yaml",
    "light_paths:",
    "  - id: epi",
    "    route_type: widefield_fluorescence",
    "    detection_sequence:",
    "      - optical_path_element_id: trinocular_port_selector",
    "      - branches:",
    "          selection_mode: exclusive",
    "          items:",
    "            - branch_id: camera_route",
    "              label: To Camera",
    "              sequence:",
    "                - optical_path_element_id: optovar_1p5x",
    "                - endpoint_id: detector_1",
    "            - branch_id: eyepiece_route",
    "              label: To Eyepieces",
    "              sequence:",
    "                - endpoint_id: eyepieces",
    "```",
    "",
    "Selectors and splitters remain inventory entries under",
    "`hardware.optical_path_elements[]`, but their canonical role is limited to",
    "identifying the installed part and advertising capability metadata such as",
    "`selection_mode`, `supported_branch_modes` and `supported_branch_count`.",
    "Downstream routing truth must not be authored as",
    "`hardware.optical_path_elements[].branches[].target_ids`.",
    "",
    "### Endpoints are explicit",
    "",
    "`hardware.endpoints[]` are the route terminals referenced from route and",
    "branch-local sequences. They are normalised together with the endpoint-capable",
    "inventories — `hardware.detectors[]` and `hardware.eyepieces[]` — before DTO",
    "consumption, so a detector that no route terminates at is unreachable: it exists",
    "in the record but no acquisition can report it.",
    "",
]

AUTHORED_DTO_INTRO = [
    "## 5. DTO contract",
    "",
    "The flow is `YAML -> schema/validator -> canonical DTO -> derived views -> consumers`.",
    "Consumers read the DTO. Reconstructing topology from raw YAML in a consumer is",
    "how two layers end up disagreeing about the same instrument.",
    "",
    "`scripts/lightpath/vm_payload.py` builds the canonical DTO",
    "(`dto_schema: light_paths_v2`). It preserves route ordering, explicit endpoints,",
    "route-owned branch blocks with stable branch ids, and branch-local optics, and it",
    "invents no topology. `sources`, `optical_path_elements`, `endpoints` and",
    "`light_paths` are the authoritative contract; anything under `projections` is a",
    "derived adapter.",
    "",
]

AUTHORED_NOT_CANONICAL = [
    "## 6. What is not canonical",
    "",
    "These are compatibility layers, not authoring targets:",
    "",
    "- legacy `hardware.light_path.*` mechanism trees;",
    "- deprecated flat filter and splitter structures;",
    "- `hardware.optical_path_elements[].branches[].target_ids`;",
    "- `light_paths[].modalities` and `light_paths[].name`;",
    "- alias-only field spellings retained for compatibility;",
    "- derived runtime splitter fields such as `path1` / `path2`, kept only so",
    "  approximation-mode projections can consume older payloads.",
    "",
    "The code that still reads them is deliberately narrow:",
    "",
    "- `scripts/lightpath/legacy_import.py` — explicit legacy import adapter, for",
    "  migration and audit tooling only;",
    "- `scripts/validate.py` — compatibility facade over `scripts/validation/*`;",
    "- validator coverage that recognises legacy paths for audit-only diagnostics.",
    "",
    "New authoring targets the canonical model, and new tests assert canonical",
    "behaviour.",
    "",
]


# --------------------------------------------------------------------------
# schema
# --------------------------------------------------------------------------

def load_policy() -> dict[str, Any]:
    return yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8")) or {}


def canonical_rules(policy: dict[str, Any]) -> list[dict[str, Any]]:
    for section in policy.get("sections") or []:
        if (section.get("name") or section.get("id")) == CANONICAL_SECTION:
            return list(section.get("rules") or [])
    raise SystemExit(f"schema section '{CANONICAL_SECTION}' not found in {POLICY_PATH}")


def all_rule_paths(policy: dict[str, Any]) -> set[str]:
    paths: set[str] = set()
    for section in policy.get("sections") or []:
        for rule in section.get("rules") or []:
            path = rule.get("path")
            if path:
                paths.add(path)
            for alias in rule.get("aliases") or []:
                paths.add(alias)
    return paths


def rule_roots(rules: list[dict[str, Any]]) -> list[str]:
    """Top-level subtrees the canonical section owns, in schema order."""
    roots: list[str] = []
    for rule in rules:
        root = rule["path"].split("[")[0].split("{")[0]
        if root not in roots:
            roots.append(root)
    return roots


def exclusive_roots(policy: dict[str, Any], roots: list[str]) -> list[str]:
    """Roots no other schema section also defines rules under."""
    exclusive = []
    for root in roots:
        owned_elsewhere = any(
            (section.get("name") or section.get("id")) != CANONICAL_SECTION
            and any((rule.get("path") or "").startswith(root) for rule in section.get("rules") or [])
            for section in policy.get("sections") or []
        )
        if not owned_elsewhere:
            exclusive.append(root)
    return exclusive


# --------------------------------------------------------------------------
# instrument records
# --------------------------------------------------------------------------

def instrument_files() -> list[Path]:
    active = sorted((REPO_ROOT / "instruments").glob("*.yaml"))
    retired = sorted((REPO_ROOT / "instruments" / "retired").glob("*.yaml"))
    return [path for path in active + retired if "Test_Scope" not in path.name]


def _resolve(record: Any, dotted: str) -> Any:
    node: Any = record
    for part in dotted.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def authored_paths(roots: list[str], schema_paths: set[str]) -> dict[str, int]:
    """Count how often each authored field appears, in schema path spelling."""
    counts: dict[str, int] = {}

    def is_object_map(path: str) -> bool:
        prefix = path + "{}"
        return any(candidate.startswith(prefix) for candidate in schema_paths)

    def walk(value: Any, path: str) -> None:
        if isinstance(value, list):
            for item in value:
                walk(item, path + "[]")
            return
        if not isinstance(value, dict):
            return
        if is_object_map(path):
            for item in value.values():
                walk(item, path + "{}")
            return
        for key, child in value.items():
            child_path = f"{path}.{key}"
            counts[child_path] = counts.get(child_path, 0) + 1
            walk(child, child_path)

    for path in instrument_files():
        record = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for root in roots:
            value = _resolve(record, root)
            if value is None:
                continue
            counts[root] = counts.get(root, 0) + 1
            walk(value, root)
    return counts


# --------------------------------------------------------------------------
# validator diagnostics
# --------------------------------------------------------------------------

def diagnostic_codes() -> list[str]:
    codes: set[str] = set()
    for directory in DIAGNOSTIC_SOURCES:
        for source in sorted(directory.rglob("*.py")):
            text = source.read_text(encoding="utf-8")
            for code in re.findall(r"code=['\"]([a-z0-9_]+)['\"]", text):
                if any(marker in code for marker in DIAGNOSTIC_MARKERS):
                    codes.add(code)
    return sorted(codes)


# --------------------------------------------------------------------------
# DTO shape
# --------------------------------------------------------------------------

def dto_shapes() -> dict[str, list[str]]:
    """Union of keys the DTO builders emit across every instrument record."""
    from scripts.dashboard.optical_path_view import build_optical_path_view_dto
    from scripts.lightpath.vm_payload import generate_virtual_microscope_payload

    shapes: dict[str, set[str]] = {
        "canonical": set(),
        "canonical.metadata": set(),
        "canonical.simulation": set(),
        "canonical.light_paths[]": set(),
        "canonical.projections.virtual_microscope": set(),
        "view": set(),
    }

    def collect(bucket: str, value: Any) -> None:
        if isinstance(value, dict):
            shapes[bucket].update(value.keys())

    for path in instrument_files():
        record = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        canonical = generate_virtual_microscope_payload(record)
        collect("canonical", canonical)
        collect("canonical.metadata", canonical.get("metadata"))
        collect("canonical.simulation", canonical.get("simulation"))
        collect(
            "canonical.projections.virtual_microscope",
            (canonical.get("projections") or {}).get("virtual_microscope"),
        )
        for route in canonical.get("light_paths") or []:
            collect("canonical.light_paths[]", route)
        view = build_optical_path_view_dto(canonical, record.get("hardware") or {})
        collect("view", view)

    return {key: sorted(value) for key, value in shapes.items()}


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def _cell(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).replace("|", "\\|").strip()


def _status_cell(rule: dict[str, Any]) -> str:
    status = rule.get("status") or "optional"
    if status != "conditional":
        return status
    condition = rule.get("required_if") or {}
    if isinstance(condition, dict):
        if "parent_present" in condition:
            return f"conditional — when `{condition['parent_present']}` is present"
        if "item_field_in" in condition and isinstance(condition["item_field_in"], dict):
            clauses = [
                f"`{field}` is {' or '.join(f'`{value}`' for value in values)}"
                for field, values in condition["item_field_in"].items()
            ]
            return "conditional — when " + " and ".join(clauses)
    return f"conditional — {_cell(json.dumps(condition))}"


def _type_cell(rule: dict[str, Any]) -> str:
    value_type = rule.get("type") or ""
    item_type = rule.get("item_type")
    text = f"{value_type} of {item_type}" if item_type else str(value_type)
    minimum = rule.get("min_items")
    if minimum:
        text += f" (min {minimum})"
    return text or "—"


def _vocab_cell(rule: dict[str, Any]) -> str:
    vocab = rule.get("vocab")
    if not vocab:
        return "—"
    if (REPO_ROOT / "vocab" / f"{vocab}.yaml").exists():
        return f"[`{vocab}`](../vocab/{vocab}.yaml)"
    return f"`{vocab}`"


def _count_cell(counts: dict[str, int], path: str) -> str:
    count = counts.get(path)
    return str(count) if count else "—"


def render_group_table(rules: list[dict[str, Any]], counts: dict[str, int]) -> list[str]:
    lines = [
        "| Field | Status | Type | Vocabulary | In records | What it records |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for rule in rules:
        lines.append(
            "| `{path}` | {status} | {type} | {vocab} | {count} | {rationale} |".format(
                path=rule["path"],
                status=_status_cell(rule),
                type=_type_cell(rule),
                vocab=_vocab_cell(rule),
                count=_count_cell(counts, rule["path"]),
                rationale=_cell(rule.get("rationale") or rule.get("title")),
            )
        )
    return lines


def render(policy: dict[str, Any]) -> str:
    rules = canonical_rules(policy)
    schema_paths = all_rule_paths(policy)
    roots = rule_roots(rules)
    counts = authored_paths(roots, schema_paths)
    shapes = dto_shapes()
    codes = diagnostic_codes()
    records = instrument_files()

    required = [rule["path"] for rule in rules if rule.get("status") == "required"]
    conditional = [rule for rule in rules if rule.get("status") == "conditional"]

    lines: list[str] = [
        "# Canonical light-path model",
        "",
        "<!-- Generated by scripts/light_path_model.py. Do not edit by hand. -->",
        "",
        "This is the implementation contract for light paths: how they are authored in",
        "YAML, what the validator enforces, and what consumers are allowed to read.",
        "",
        "The field tables, the diagnostic list, and the DTO shapes below are generated",
        "from `schema/instrument_policy.yaml`, `scripts/validation/`, and the DTO",
        "builders, so they cannot drift from the code. The explanatory sections are",
        "authored in `scripts/light_path_model.py` and cover what the schema cannot",
        "state: why the model is shaped this way and which readings of it are wrong.",
        "",
        f"Generated from {len(rules)} schema rules in the `{CANONICAL_SECTION}` section",
        f"and {len(records)} instrument records.",
        "",
        "## 1. Canonical structure",
        "",
        "Authoritative light-path data is authored as a hardware inventory plus ordered",
        "routes over that inventory:",
        "",
        "```yaml",
        "hardware:",
        "  sources: []                 # what illuminates",
        "  optical_path_elements: []   # what shapes or splits the light",
        "  endpoints: []               # where the light ends up",
        "",
        "light_paths:",
        "  - id: <route_id>",
        "    route_type: <optical_routes term>",
        "    illumination_sequence: []",
        "    detection_sequence: []",
        "```",
        "",
        f"The {len(required)} fields the schema marks required are:",
        "",
    ]
    lines.extend(f"- `{path}`" for path in required)
    lines.extend([
        "",
        f"A further {len(conditional)} fields are conditionally required — required once",
        "their parent or a sibling value is present. Both are marked in the tables below.",
        "",
        "## 2. Field reference",
        "",
        "`In records` counts how many authored occurrences each field currently has",
        "across the instrument ledgers. A required field with a low count means records",
        "are missing it; an optional field with a count of `—` is defined but unused.",
        "",
    ])

    for root in roots:
        group_rules = [
            rule for rule in rules
            if rule["path"] == root or rule["path"].startswith(root + "[") or rule["path"].startswith(root + ".")
        ]
        if not group_rules:
            continue
        lines.append(f"### `{root}`")
        lines.append("")
        note = GROUP_NOTES.get(root)
        if note:
            lines.append(note)
            lines.append("")
        lines.extend(render_group_table(group_rules, counts))
        lines.append("")

    lines.extend(AUTHORED_SEMANTICS)

    lines.extend([
        "## 4. Validation",
        "",
        "The validator diagnostics that belong to the light-path contract, collected",
        "from `scripts/validation/` and `scripts/lightpath/`:",
        "",
        "| Code | What it means |",
        "| --- | --- |",
    ])
    for code in codes:
        note = DIAGNOSTIC_NOTES.get(code)
        if not note:
            note = "_No description recorded — add one to `DIAGNOSTIC_NOTES` in `scripts/light_path_model.py`._"
        lines.append(f"| `{code}` | {_cell(note)} |")
    lines.extend([
        "",
        "The method-mapping checks run against active instruments. Retired records are",
        "held to the structural rules only, which is why a retired ledger can still",
        "carry pre-`route_type` spellings.",
        "",
    ])

    lines.extend(AUTHORED_DTO_INTRO)
    lines.extend([
        f"Canonical DTO top-level keys ({len(shapes['canonical'])}):",
        "",
    ])
    lines.extend(f"- `{key}`" for key in shapes["canonical"])
    lines.extend([
        "",
        "Per-route keys under `light_paths[]`:",
        "",
    ])
    lines.extend(f"- `{key}`" for key in shapes["canonical.light_paths[]"])
    lines.extend([
        "",
        "`metadata`:",
        "",
    ])
    lines.extend(f"- `{key}`" for key in shapes["canonical.metadata"])
    lines.extend([
        "",
        "`simulation`:",
        "",
    ])
    lines.extend(f"- `{key}`" for key in shapes["canonical.simulation"])
    lines.extend([
        "",
        "`projections.virtual_microscope` — a derived runtime adapter, never topology truth:",
        "",
    ])
    lines.extend(f"- `{key}`" for key in shapes["canonical.projections.virtual_microscope"])
    lines.extend([
        "",
        "### Dashboard view DTO",
        "",
        "`scripts/dashboard/optical_path_view.py` builds the view DTO the dashboard, the",
        "Methods generator, and the LLM export actually read. It wraps the canonical DTO",
        "and adds publication-ready labels and per-route renderables; it adds no topology.",
        "",
        f"Top-level keys ({len(shapes['view'])}):",
        "",
    ])
    lines.extend(f"- `{key}`" for key in shapes["view"])
    lines.append("")

    lines.extend(AUTHORED_NOT_CANONICAL)

    lines.extend([
        "## 7. Schema and record drift",
        "",
        "Generated by comparing what the ledgers author against what the schema defines.",
        "Neither list is automatically a defect: an unruled field may be a deliberate",
        "free-text note, and an unused rule may be waiting for a record that needs it.",
        "Both are the places where the model and the data have parted company.",
        "",
        "### Authored with no schema rule",
        "",
    ])
    owned = exclusive_roots(policy, roots)
    unruled = sorted(
        (path, count) for path, count in counts.items()
        if path not in schema_paths and any(path.startswith(root) for root in owned)
    )
    if unruled:
        lines.append("| Field | In records |")
        lines.append("| --- | --- |")
        lines.extend(f"| `{path}` | {count} |" for path, count in unruled)
    else:
        lines.append("Every authored field under the canonical subtrees has a schema rule.")
    lines.extend([
        "",
        f"Scoped to the subtrees the `{CANONICAL_SECTION}` section owns outright "
        f"({', '.join(f'`{root}`' for root in owned)}).",
        "",
        "### Defined but never authored",
        "",
    ])
    unused = [rule["path"] for rule in rules if not counts.get(rule["path"])]
    if unused:
        lines.extend(f"- `{path}`" for path in unused)
    else:
        lines.append("Every canonical rule is used by at least one record.")
    lines.extend([
        "",
        "---",
        "",
        "Regenerate with `python -m scripts.light_path_model` after changing the schema,",
        "the light-path validator, the DTO builders, or an instrument ledger;",
        "`python -m scripts.light_path_model --check` fails when this file is stale.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="Fail if docs/light_path_model.md no longer matches the schema and records.")
    args = parser.parse_args()

    output = render(load_policy())
    if args.check:
        existing = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
        if existing != output:
            print(f"{OUTPUT_PATH.relative_to(REPO_ROOT)} is out of date.")
            print("Run `python -m scripts.light_path_model` and commit the result.")
            return 1
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(output, encoding="utf-8")
    print(f"Generated {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
