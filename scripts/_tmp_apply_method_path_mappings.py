from pathlib import Path
from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[1]
INSTRUMENTS = ROOT / "instruments"
POLICY = ROOT / "schema" / "instrument_policy.yaml"
TESTS = ROOT / "tests" / "test_active_yaml_contracts.py"


yaml = YAML()
yaml.preserve_quotes = True
yaml.width = 1000


def load(path):
    with path.open("r", encoding="utf-8") as fh:
        return yaml.load(fh)


def save(path, data):
    with path.open("w", encoding="utf-8") as fh:
        yaml.dump(data, fh)


def as_list(value):
    return list(value) if isinstance(value, list) else []


vocab = load(ROOT / "vocab" / "optical_routes.yaml")
route_covers = {}
for term in as_list(vocab.get("terms")):
    if not isinstance(term, dict) or not term.get("id"):
        continue
    covers = term.get("covers") if isinstance(term.get("covers"), dict) else {}
    route_covers[str(term["id"])] = {
        "imaging_modes": set(str(v) for v in as_list(covers.get("imaging_modes")) if v),
        "contrast_methods": set(str(v) for v in as_list(covers.get("contrast_methods")) if v),
    }

changed_files = []
ambiguous = []
unsupported = []

for path in sorted(INSTRUMENTS.glob("*.yaml")):
    data = load(path)
    if not isinstance(data, dict):
        continue
    caps = data.get("capabilities") if isinstance(data.get("capabilities"), dict) else {}
    paths = [lp for lp in as_list(data.get("light_paths")) if isinstance(lp, dict)]
    if not paths:
        continue

    changed = False
    for axis in ("imaging_modes", "contrast_methods"):
        declared = [str(v) for v in as_list(caps.get(axis)) if v]
        if not declared:
            continue

        for method in declared:
            already = [lp for lp in paths if method in [str(v) for v in as_list(lp.get(axis)) if v]]
            if already:
                continue

            candidates = []
            for lp in paths:
                route_type = str(lp.get("route_type") or lp.get("id") or "")
                if method in route_covers.get(route_type, {}).get(axis, set()):
                    candidates.append(lp)

            if len(candidates) == 1:
                lp = candidates[0]
                values = as_list(lp.get(axis))
                values.append(method)
                lp[axis] = values
                changed = True
                print(f"MAP {path.name}: {axis}.{method} -> {lp.get('id')}")
            elif len(candidates) > 1:
                ambiguous.append((path.name, axis, method, [lp.get("id") for lp in candidates]))
            else:
                unsupported.append((path.name, axis, method))

    # Validate authored mappings against capabilities + route family coverage.
    for lp in paths:
        route_type = str(lp.get("route_type") or lp.get("id") or "")
        for axis in ("imaging_modes", "contrast_methods"):
            declared = set(str(v) for v in as_list(caps.get(axis)) if v)
            covered = route_covers.get(route_type, {}).get(axis, set())
            for method in [str(v) for v in as_list(lp.get(axis)) if v]:
                if method not in declared:
                    raise RuntimeError(
                        f"{path.name}: {lp.get('id')} maps {axis}.{method} but the capability is not declared"
                    )
                if method not in covered:
                    raise RuntimeError(
                        f"{path.name}: {lp.get('id')} maps {axis}.{method}, not covered by route type {route_type}"
                    )

    if changed:
        save(path, data)
        changed_files.append(path.name)

# Make method/path association fields first-class schema metadata.
policy = load(POLICY)
inserted_policy = False
for section in as_list(policy.get("sections")):
    rules = section.get("rules") if isinstance(section, dict) else None
    if not isinstance(rules, list):
        continue
    route_index = next((i for i, rule in enumerate(rules) if isinstance(rule, dict) and rule.get("path") == "light_paths[].route_type"), None)
    if route_index is None:
        continue
    existing = {rule.get("path") for rule in rules if isinstance(rule, dict)}
    additions = []
    if "light_paths[].imaging_modes" not in existing:
        additions.append({
            "path": "light_paths[].imaging_modes",
            "title": "Light path imaging modes",
            "status": "optional",
            "type": "list",
            "item_type": "string",
            "vocab": "imaging_modes",
            "used_by": ["dashboard", "method_generator"],
            "rationale": "Explicitly associates imaging methods with the physical light path that implements them, avoiding downstream method-to-route inference.",
        })
    if "light_paths[].contrast_methods" not in existing:
        additions.append({
            "path": "light_paths[].contrast_methods",
            "title": "Light path contrast methods",
            "status": "optional",
            "type": "list",
            "item_type": "string",
            "vocab": "contrast_methods",
            "used_by": ["dashboard", "method_generator"],
            "rationale": "Explicitly associates contrast methods with the physical light path that implements them, avoiding downstream method-to-route inference.",
        })
    for offset, rule in enumerate(additions, start=1):
        rules.insert(route_index + offset, rule)
        inserted_policy = True
    break

if inserted_policy:
    save(POLICY, policy)

# Repository contract: mapped methods must be valid and every unambiguous
# capability-to-route relationship must be authored explicitly.
test_text = TESTS.read_text(encoding="utf-8")
marker = "\n\nif __name__ == \"__main__\":\n"
method_name = "test_all_active_repo_methods_have_explicit_light_path_mapping"
if method_name not in test_text:
    test_method = r'''
    def test_all_active_repo_methods_have_explicit_light_path_mapping(self) -> None:
        """Methods must be explicitly associated with compatible physical light paths."""
        route_vocab = yaml.safe_load((REPO_ROOT / "vocab" / "optical_routes.yaml").read_text(encoding="utf-8")) or {}
        covers = {}
        for term in route_vocab.get("terms") or []:
            if not isinstance(term, dict) or not term.get("id"):
                continue
            term_covers = term.get("covers") if isinstance(term.get("covers"), dict) else {}
            covers[str(term["id"])] = {
                "imaging_modes": set(term_covers.get("imaging_modes") or []),
                "contrast_methods": set(term_covers.get("contrast_methods") or []),
            }

        violations = []
        for yaml_path in sorted(INSTRUMENTS_DIR.glob("*.yaml")):
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            if not isinstance(data, dict):
                continue
            caps = data.get("capabilities") if isinstance(data.get("capabilities"), dict) else {}
            paths = [lp for lp in (data.get("light_paths") or []) if isinstance(lp, dict)]
            if not paths:
                continue

            for axis in ("imaging_modes", "contrast_methods"):
                declared = set(caps.get(axis) or [])
                mapped = set()
                for lp in paths:
                    route_type = str(lp.get("route_type") or lp.get("id") or "")
                    allowed = covers.get(route_type, {}).get(axis, set())
                    authored = set(lp.get(axis) or [])
                    invalid = authored - declared
                    incompatible = authored - allowed
                    if invalid:
                        violations.append((yaml_path.name, lp.get("id"), axis, "not declared capability", sorted(invalid)))
                    if incompatible:
                        violations.append((yaml_path.name, lp.get("id"), axis, "not covered by route", sorted(incompatible)))
                    mapped.update(authored)

                for method in sorted(declared - mapped):
                    candidates = [
                        lp.get("id")
                        for lp in paths
                        if method in covers.get(str(lp.get("route_type") or lp.get("id") or ""), {}).get(axis, set())
                    ]
                    if len(candidates) == 1:
                        violations.append((yaml_path.name, candidates[0], axis, "unambiguous mapping not authored", method))

        self.assertEqual(
            violations,
            [],
            f"Active YAML method-to-path mappings must be explicit and route-compatible: {violations}",
        )
'''
    if marker not in test_text:
        raise RuntimeError("test insertion marker not found")
    TESTS.write_text(test_text.replace(marker, "\n" + test_method + marker, 1), encoding="utf-8")

print(f"UPDATED_YAMLS={len(changed_files)} {changed_files}")
print(f"AMBIGUOUS={ambiguous}")
print(f"UNSUPPORTED={unsupported}")
