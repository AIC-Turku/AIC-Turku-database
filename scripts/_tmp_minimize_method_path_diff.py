# Temporary one-shot helper: rebuild mapping changes without YAML formatting churn.
from pathlib import Path
import subprocess
import yaml

ROOT = Path(__file__).resolve().parents[1]
PRE_MAPPING = "a3017ad3b939f2077936d8c8dcc2b63f161de3b0"
TARGETS = [
    "3i CSU-W1 Spinning Disk Med C.yaml",
    "3i CSU-W1 Spinning Disk.yaml",
    "Andor BC43 Benchtop Confocal.yaml",
    "EVOS fl.yaml",
    "Lambert FLIM.yaml",
    "Leica DM IRBE.yaml",
    "Leica DM RB.yaml",
    "Leica DMRE.yaml",
    "Leica STELLARIS 8 FALCON FLIM.yaml",
    "Leica Thunder.yaml",
    "MSquared Aurora Airy Beam.yaml",
    "Nikon Eclipse Ti2-E.yaml",
    "Nikon Ti2-E Crest V3 Spinning Disk.yaml",
    "Olympus BX60.yaml",
    "Zeiss AxioZoom V16.yaml",
    "Zeiss LSM 510 JPK AFM.yaml",
    "Zeiss LSM 880 with AiryScan.yaml",
    "Zeiss TIRF.yaml",
    "xCELLigence RTCA eSight.yaml",
]


def git_show(path: str) -> str:
    return subprocess.check_output(["git", "show", f"{PRE_MAPPING}:{path}"], cwd=ROOT, text=True)


def route_covers():
    data = yaml.safe_load((ROOT / "vocab" / "optical_routes.yaml").read_text(encoding="utf-8")) or {}
    out = {}
    for term in data.get("terms") or []:
        if not isinstance(term, dict) or not term.get("id"):
            continue
        covers = term.get("covers") if isinstance(term.get("covers"), dict) else {}
        out[str(term["id"])] = {
            "imaging_modes": set(covers.get("imaging_modes") or []),
            "contrast_methods": set(covers.get("contrast_methods") or []),
        }
    return out


COVERS = route_covers()


def final_mappings(data):
    caps = data.get("capabilities") if isinstance(data.get("capabilities"), dict) else {}
    paths = [lp for lp in (data.get("light_paths") or []) if isinstance(lp, dict)]
    result = {}
    for lp in paths:
        pid = str(lp.get("id") or "")
        axes = {}
        for axis in ("imaging_modes", "contrast_methods"):
            values = list(lp.get(axis) or [])
            declared = list(caps.get(axis) or [])
            for method in declared:
                candidates = [
                    candidate
                    for candidate in paths
                    if method in COVERS.get(str(candidate.get("route_type") or candidate.get("id") or ""), {}).get(axis, set())
                ]
                if len(candidates) == 1 and candidates[0] is lp and method not in values:
                    values.append(method)
            if values:
                axes[axis] = values
        result[pid] = axes
    return result


def minimally_insert(text: str, mapping: dict) -> str:
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("- id: ") and i > 0 and lines[i-1].startswith("light_paths:")]
    if starts:
        first = starts[0]
        starts = [i for i in range(first, len(lines)) if lines[i].startswith("- id: ")]
    else:
        return text
    starts.append(len(lines))
    additions = []
    for si in range(len(starts) - 1):
        start, end = starts[si], starts[si + 1]
        pid = lines[start].split(":", 1)[1].strip()
        axes = mapping.get(pid) or {}
        if not axes:
            continue
        block = lines[start:end]
        existing_keys = {line.strip().split(":", 1)[0] for line in block if line.startswith("  ") and ":" in line}
        route_index = next((start + j for j, line in enumerate(block) if line.startswith("  route_type:")), None)
        if route_index is None:
            continue
        insert = []
        for axis in ("imaging_modes", "contrast_methods"):
            vals = axes.get(axis) or []
            if vals and axis not in existing_keys:
                insert.append(f"  {axis}:")
                insert.extend(f"  - {v}" for v in vals)
        if insert:
            additions.append((route_index + 1, insert))
    for index, insert in reversed(additions):
        lines[index:index] = insert
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


for name in TARGETS:
    rel = f"instruments/{name}"
    original = git_show(rel)
    data = yaml.safe_load(original) or {}
    updated = minimally_insert(original, final_mappings(data))
    (ROOT / rel).write_text(updated, encoding="utf-8")

policy_path = ROOT / "schema" / "instrument_policy.yaml"
policy = git_show("schema/instrument_policy.yaml")
marker = "  - path: light_paths[].readouts\n"
addition = """  - path: light_paths[].imaging_modes\n    title: Light path imaging modes\n    status: optional\n    type: list\n    item_type: string\n    vocab: imaging_modes\n    used_by: [dashboard, method_generator]\n    rationale: Explicitly associates imaging methods with the physical light path that implements them, avoiding downstream method-to-route inference.\n\n  - path: light_paths[].contrast_methods\n    title: Light path contrast methods\n    status: optional\n    type: list\n    item_type: string\n    vocab: contrast_methods\n    used_by: [dashboard, method_generator]\n    rationale: Explicitly associates contrast methods with the physical light path that implements them, avoiding downstream method-to-route inference.\n\n"""
if marker not in policy:
    raise RuntimeError("schema insertion marker not found")
policy_path.write_text(policy.replace(marker, addition + marker, 1), encoding="utf-8")

tests_path = ROOT / "tests" / "test_active_yaml_contracts.py"
tests = git_show("tests/test_active_yaml_contracts.py")
method = r'''
    def test_all_active_repo_methods_have_explicit_light_path_mapping(self) -> None:
        """Unambiguous method-to-route relationships must be authored in YAML."""
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
                    authored = set(lp.get(axis) or [])
                    allowed = covers.get(route_type, {}).get(axis, set())
                    if authored - declared:
                        violations.append((yaml_path.name, lp.get("id"), axis, "not declared", sorted(authored - declared)))
                    if authored - allowed:
                        violations.append((yaml_path.name, lp.get("id"), axis, "route-incompatible", sorted(authored - allowed)))
                    mapped.update(authored)
                for value in sorted(declared - mapped):
                    candidates = [
                        lp.get("id") for lp in paths
                        if value in covers.get(str(lp.get("route_type") or lp.get("id") or ""), {}).get(axis, set())
                    ]
                    if len(candidates) == 1:
                        violations.append((yaml_path.name, candidates[0], axis, "unambiguous mapping not authored", value))
        self.assertEqual(violations, [], f"Explicit method-to-light-path mapping violations: {violations}")
'''
anchor = '\n\nif __name__ == "__main__":\n'
if anchor not in tests:
    raise RuntimeError("test insertion marker not found")
tests_path.write_text(tests.replace(anchor, "\n" + method + anchor, 1), encoding="utf-8")

print("Minimal method-path mapping diff rebuilt")
