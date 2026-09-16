from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Expected patch marker not found in {path}: {old[:100]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Complete active YAML method -> physical-path mappings. Route vocabulary is used
# only to identify/validate compatible physical paths; consumers must read the
# resulting authored mapping rather than infer it at runtime.
route_vocab = yaml.safe_load((ROOT / "vocab/optical_routes.yaml").read_text(encoding="utf-8")) or {}
covers: dict[str, dict[str, set[str]]] = {}
for term in route_vocab.get("terms") or []:
    if not isinstance(term, dict) or not term.get("id"):
        continue
    meta = term.get("covers") if isinstance(term.get("covers"), dict) else {}
    covers[str(term["id"])] = {
        "imaging_modes": set(meta.get("imaging_modes") or []),
        "contrast_methods": set(meta.get("contrast_methods") or []),
    }


def add_values_to_route(text: str, route_id: str, axis: str, values: list[str]) -> str:
    if not values:
        return text
    lines = text.splitlines()
    light_paths_line = next((i for i, line in enumerate(lines) if line.startswith("light_paths:")), None)
    if light_paths_line is None:
        raise RuntimeError("light_paths block not found")
    starts = [i for i in range(light_paths_line + 1, len(lines)) if lines[i].startswith("- id: ")]
    target = None
    for pos, start in enumerate(starts):
        rid = lines[start].split(":", 1)[1].strip()
        if rid == route_id:
            end = starts[pos + 1] if pos + 1 < len(starts) else len(lines)
            target = (start, end)
            break
    if target is None:
        raise RuntimeError(f"Route {route_id!r} not found while editing YAML")
    start, end = target
    axis_line = next((i for i in range(start + 1, end) if lines[i] == f"  {axis}:"), None)
    if axis_line is not None:
        insert_at = axis_line + 1
        while insert_at < end and lines[insert_at].startswith("  - "):
            insert_at += 1
        existing = {
            lines[i][4:].strip()
            for i in range(axis_line + 1, insert_at)
            if lines[i].startswith("  - ")
        }
        additions = [f"  - {value}" for value in values if value not in existing]
        lines[insert_at:insert_at] = additions
    else:
        route_type_line = next(
            (i for i in range(start + 1, end) if lines[i].startswith("  route_type:")),
            None,
        )
        if route_type_line is None:
            raise RuntimeError(f"route_type missing for {route_id!r}")
        additions = [f"  {axis}:"] + [f"  - {value}" for value in values]
        lines[route_type_line + 1:route_type_line + 1] = additions
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


migration_notes: list[str] = []
for path in sorted((ROOT / "instruments").glob("*.yaml")):
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    caps = data.get("capabilities") if isinstance(data.get("capabilities"), dict) else {}
    paths = [lp for lp in (data.get("light_paths") or []) if isinstance(lp, dict)]
    if not paths:
        continue
    pending: dict[tuple[str, str], list[str]] = {}
    for axis in ("imaging_modes", "contrast_methods"):
        declared = set(caps.get(axis) or [])
        mapped = {
            value
            for lp in paths
            for value in (lp.get(axis) or [])
            if isinstance(value, str)
        }
        for method in sorted(declared - mapped):
            candidates = [
                str(lp.get("id") or "")
                for lp in paths
                if method
                in covers.get(
                    str(lp.get("route_type") or lp.get("id") or ""), {}
                ).get(axis, set())
            ]
            if len(candidates) != 1:
                raise RuntimeError(
                    f"{path.name}: {axis} {method!r} has {len(candidates)} compatible paths "
                    f"{candidates}; explicit authoring is required rather than guessing."
                )
            pending.setdefault((candidates[0], axis), []).append(method)
    for (route_id, axis), values in pending.items():
        text = add_values_to_route(text, route_id, axis, values)
        migration_notes.append(f"{path.name}: {axis} {values} -> {route_id}")
    path.write_text(text, encoding="utf-8")

print("Explicit mappings added:", migration_notes or "none; active YAML was already fully mapped")


# Methods Generator: only explicitly authored method/path associations create method
# choices. A bare route_type remains a physical route, not an inferred method.
replace_once(
    "assets/javascripts/methods_generator_app.js",
    """            const candidates = explicit.length ? explicit : [{\n                id: cleanText(route?.route_type),\n                display_label: cleanText(route?.route_type_label || route?.display_label),\n            }];""",
    """            const candidates = explicit;""",
)


# Production validator: enforce explicit cross-field mapping as a hard error for
# active instruments. Route vocabulary coverage is only a compatibility check.
validator = ROOT / "scripts/validation/instrument.py"
text = validator.read_text(encoding="utf-8")
marker = "\ndef validate_instrument_ledgers(\n"
if marker not in text:
    raise RuntimeError("validator insertion marker not found")
helper = r'''

def _append_explicit_method_path_issues(
    issues: list[ValidationIssue],
    payload: dict[str, Any],
    instrument_file: Path,
    vocabulary: Vocabulary,
    capabilities: dict[str, set[str]],
) -> None:
    """Enforce explicit capability-to-light-path mappings for active instruments.

    `capabilities` declares what the instrument can do. `light_paths[].imaging_modes`
    and `light_paths[].contrast_methods` declare which physical path implements each
    method. Route-family coverage verifies compatibility only and never supplies a
    missing mapping.
    """
    light_paths = payload.get('light_paths')
    if not isinstance(light_paths, list):
        light_paths = []

    for axis in ('imaging_modes', 'contrast_methods'):
        declared = set(capabilities.get(axis, set()))
        mapped: set[str] = set()

        for index, light_path in enumerate(light_paths):
            if not isinstance(light_path, dict):
                continue
            route_type_raw = light_path.get('route_type') or light_path.get('id')
            route_type = (
                vocabulary.resolve_canonical('optical_routes', route_type_raw) or str(route_type_raw or '').strip()
                if isinstance(route_type_raw, str)
                else ''
            )
            route_term = vocabulary.get_term('optical_routes', route_type) if route_type else None
            route_covers: set[str] = set()
            if route_term is not None and isinstance(route_term.metadata, dict):
                cover_map = route_term.metadata.get('covers')
                if isinstance(cover_map, dict):
                    route_covers = {
                        str(value).strip()
                        for value in (cover_map.get(axis) or [])
                        if isinstance(value, str) and value.strip()
                    }

            authored = {
                (vocabulary.resolve_canonical(axis, value) or value)
                for value in (light_path.get(axis) or [])
                if isinstance(value, str) and value.strip()
            }
            mapped.update(authored)

            for method in sorted(authored - declared):
                issues.append(ValidationIssue(
                    code='light_path_method_not_declared',
                    path=f"{instrument_file.as_posix()}:light_paths[{index}].{axis}",
                    message=(
                        f"Light path maps method '{method}' but capabilities.{axis} does not declare it. "
                        "Declare the capability or remove the path mapping."
                    ),
                ))

            for method in sorted(authored - route_covers):
                issues.append(ValidationIssue(
                    code='light_path_method_route_incompatible',
                    path=f"{instrument_file.as_posix()}:light_paths[{index}].{axis}",
                    message=(
                        f"Method '{method}' is explicitly mapped to route_type '{route_type}', but that "
                        "route family does not cover the method according to vocab/optical_routes.yaml."
                    ),
                ))

        for method in sorted(declared - mapped):
            issues.append(ValidationIssue(
                code='capability_method_unmapped',
                path=f"{instrument_file.as_posix()}:capabilities.{axis}",
                message=(
                    f"Declared method '{method}' has no explicit light_paths[].{axis} mapping. "
                    "Author the physical method-to-path relationship in YAML; consumers must not infer it from route_type."
                ),
            ))
'''
text = text.replace(marker, helper + marker, 1)
call_marker = '''        _append_light_path_route_warnings(
            warnings=warnings,
            payload=payload,
            instrument_file=instrument_file,
            vocabulary=vocabulary,
            capabilities=capability_axes,
            is_retired_instrument=is_retired_instrument,
            allow_legacy_modalities=allow_legacy_modalities,
        )
'''
if call_marker not in text:
    raise RuntimeError("validator call marker not found")
text = text.replace(
    call_marker,
    call_marker
    + '''
        if not is_retired_instrument:
            _append_explicit_method_path_issues(
                issues=issues,
                payload=payload,
                instrument_file=instrument_file,
                vocabulary=vocabulary,
                capabilities=capability_axes,
            )
''',
    1,
)
validator.write_text(text, encoding="utf-8")


# Repository-level regression: every declared active method must be explicitly mapped,
# even where more than one route family might be compatible in the abstract.
replace_once(
    "tests/test_active_yaml_contracts.py",
    '''                for method in sorted(declared - mapped):
                    candidates = [
                        lp.get("id")
                        for lp in paths
                        if method in covers.get(str(lp.get("route_type") or lp.get("id") or ""), {}).get(axis, set())
                    ]
                    if len(candidates) == 1:
                        violations.append((yaml_path.name, candidates[0], axis, "unambiguous mapping not authored", method))''',
    '''                for method in sorted(declared - mapped):
                    candidates = [
                        lp.get("id")
                        for lp in paths
                        if method in covers.get(str(lp.get("route_type") or lp.get("id") or ""), {}).get(axis, set())
                    ]
                    violations.append((
                        yaml_path.name, axis, "declared capability not explicitly mapped", method, candidates
                    ))''',
)


# Browser fixture: model transmitted brightfield on the contrast-method axis.
replace_once(
    "tests/test_methods_generator_method_first.py",
    '''                "imaging_modes": [{"id": "transmitted_light", "display_label": "Transmitted Light"}],
                "contrast_methods": [],''',
    '''                "imaging_modes": [],
                "contrast_methods": [{"id": "transmitted_brightfield", "display_label": "Transmitted Brightfield"}],''',
)

# Add a third physical route with no method mapping; it must not become a method option.
browser_test = ROOT / "tests/test_methods_generator_method_first.py"
bt = browser_test.read_text(encoding="utf-8")
route_anchor = '''        },
    ]
    return {
        "id": "scope-method-first",'''
unmapped_route = '''        },
        {
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
    ]
    return {
        "id": "scope-method-first",'''
if route_anchor not in bt:
    raise RuntimeError("browser route insertion marker not found")
bt = bt.replace(route_anchor, unmapped_route, 1)
test_anchor = '''    def test_method_first_selection_reveals_only_compatible_route_hardware(self):
'''
extra_test = '''    def test_unmapped_route_does_not_become_an_inferred_method(self):
        methods = self.page.locator('#method-list input[data-category="method"]')
        self.assertEqual(methods.count(), 2)
        expect(self.page.locator("#method-list")).not_to_contain_text("Unmapped service path")

'''
if test_anchor not in bt:
    raise RuntimeError("browser test insertion marker not found")
bt = bt.replace(test_anchor, extra_test + test_anchor, 1)
browser_test.write_text(bt, encoding="utf-8")


# Schema: document the active-instrument cross-field invariant. The per-path fields
# themselves remain optional because a path may implement only one of the two axes.
replace_once(
    "schema/instrument_policy.yaml",
    "rationale: Canonical imaging-mode capability axis (not a route identifier).",
    "rationale: Canonical imaging-mode capability axis (not a route identifier). For active instruments, every declared method must be explicitly associated with at least one compatible light_paths[].imaging_modes entry.",
)
replace_once(
    "schema/instrument_policy.yaml",
    "rationale: Canonical contrast-method capability axis.",
    "rationale: Canonical contrast-method capability axis. For active instruments, every declared method must be explicitly associated with at least one compatible light_paths[].contrast_methods entry.",
)
replace_once(
    "schema/instrument_policy.yaml",
    "rationale: Explicitly associates imaging methods with the physical light path that implements them, avoiding downstream method-to-route inference.",
    "rationale: Explicitly associates imaging methods with the physical light path that implements them. On active instruments, mapped methods must also be declared in capabilities.imaging_modes, must be compatible with route_type, and every declared imaging mode must be mapped to at least one path.",
)
replace_once(
    "schema/instrument_policy.yaml",
    "rationale: Explicitly associates contrast methods with the physical light path that implements them, avoiding downstream method-to-route inference.",
    "rationale: Explicitly associates contrast methods with the physical light path that implements them. On active instruments, mapped methods must also be declared in capabilities.contrast_methods, must be compatible with route_type, and every declared contrast method must be mapped to at least one path.",
)


# One-shot migration machinery must not survive the migration commit.
for temporary in (
    ROOT / "scripts/_tmp_minimize_method_path_diff.py",
    ROOT / "scripts/_tmp_finish_method_path_migration.py",
    ROOT / ".github/workflows/tmp-minimize-method-path-diff.yml",
):
    if temporary.exists():
        temporary.unlink()
