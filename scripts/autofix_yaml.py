"""
Data-Driven Autofixer for the Database
Reads declarative policy schemas, maps vocabularies to JSON paths, 
and dynamically auto-fixes synonyms and legacy fields across all ledgers.
"""
from __future__ import annotations
import argparse
import yaml
from pathlib import Path

def get_base_path() -> Path:
    return Path.cwd().resolve()

def load_vocabs(vocab_dir: Path) -> dict:
    vocabs = {}
    if not vocab_dir.exists(): return vocabs
    
    for v_file in vocab_dir.glob("*.yaml"):
        with open(v_file, 'r', encoding='utf-8') as f:
            v_data = yaml.safe_load(f) or {}
            
        term_map = {}
        for term in v_data.get('terms', []):
            canon_id = term['id']
            # Map canonical ID to itself
            term_map[canon_id.lower()] = canon_id
            # Map all synonyms to canonical ID
            for syn in term.get('synonyms', []):
                term_map[str(syn).lower()] = canon_id
                
        vocabs[v_file.stem] = term_map
    return vocabs

def load_schema_rules(schema_file: Path) -> dict:
    """Returns a dict mapping dot-notation paths to vocabulary names."""
    if not schema_file.exists(): return {}
    with open(schema_file, 'r', encoding='utf-8') as f:
        policy = yaml.safe_load(f) or {}
        
    path_to_vocab = {}
    rules = []
    
    if 'sections' in policy:
        for sec in policy['sections']: rules.extend(sec.get('rules', []))
    if 'field_rules' in policy:
        rules.extend(policy['field_rules'])
        
    for rule in rules:
        if rule.get('vocab'):
            path_to_vocab[rule['path']] = rule['vocab']
            
    return path_to_vocab

def get_canonical(value: str, vocab_name: str, vocabs: dict) -> str:
    if not isinstance(value, str) or vocab_name not in vocabs:
        return value
    term_map = vocabs[vocab_name]
    return term_map.get(value.lower().strip(), value)

def fix_data_by_path(data: dict, parts: list[str], vocab_name: str, vocabs: dict) -> bool:
    """Recursively walks a dict based on a path (e.g., 'hardware.detectors[].kind') and updates values."""
    if not data or not parts: return False
    changed = False
    current = parts[0]
    
    if current.endswith('[]'):
        base = current[:-2]
        if isinstance(data, dict) and base in data and isinstance(data[base], list):
            for item in data[base]:
                if fix_data_by_path(item, parts[1:], vocab_name, vocabs):
                    changed = True
    else:
        if len(parts) == 1: # Reached the target key
            if isinstance(data, dict) and current in data:
                val = data[current]
                if val is None: return False
                
                is_list = isinstance(val, list)
                vals_to_check = val if is_list else [val]
                new_vals = []
                local_change = False
                
                for v in vals_to_check:
                    canon = get_canonical(v, vocab_name, vocabs)
                    if canon != v:
                        new_vals.append(canon)
                        local_change = True
                    else:
                        new_vals.append(v)
                        
                if local_change:
                    data[current] = new_vals if is_list else new_vals[0]
                    changed = True
        else:
            if isinstance(data, dict) and current in data:
                if fix_data_by_path(data[current], parts[1:], vocab_name, vocabs):
                    changed = True
                    
    return changed

def fix_legacy_fields(data: dict) -> bool:
    """Manually catches renamed/deprecated fields across older files."""
    changed = False

    # 1. Fix QC field names
    if "contact" in data and "performed_by" not in data:
        data["performed_by"] = data.pop("contact")
        changed = True

    # 2. Add other legacy maps
    legacy_map = {
        "event_id": "maintenance_id",
        "type": "reason",
        "parts_replaced": "action_details",
    }
    
    for old_k, new_k in legacy_map.items():
        if old_k in data:
            data[new_k] = data.pop(old_k)
            changed = True

    # 3. Move long-form action strings into action_details
    if "action" in data and len(str(data["action"])) > 20:
        data["action_details"] = data.pop("action")
        data["action"] = "other"
        changed = True
            
    # Quick fix for common service provider casing issues in older datasets
    if "service_provider" in data and data["service_provider"] == "Internal":
        data["service_provider"] = "internal"
        changed = True
        
    return changed

def autofix_file(filepath: Path, path_to_vocab: dict, vocabs: dict, check_only: bool) -> tuple[bool, int]:
    with open(filepath, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}

    changed = fix_legacy_fields(data)
    replacements = 1 if changed else 0

    for path, vocab_name in path_to_vocab.items():
        parts = path.split('.')
        if fix_data_by_path(data, parts, vocab_name, vocabs):
            changed = True
            replacements += 1

    if changed and not check_only:
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)

    return changed, replacements

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Data-Driven Vocabulary Auto-Fixer")
    parser.add_argument("--check", action="store_true", help="Check mode only. Fails script if changes are needed.")
    return parser.parse_args()

def main() -> int:
    args = parse_args()
    base = get_base_path()
    
    # Load all capabilities dynamically
    vocabs = load_vocabs(base / "vocab")
    
    # Load rules from schemas
    inst_rules = load_schema_rules(base / "schema" / "instrument_policy.yaml")
    qc_rules = load_schema_rules(base / "schema" / "QC_policy.yaml")
    maint_rules = load_schema_rules(base / "schema" / "maintenance_policy.yaml")

    targets = [
        (base / "instruments", inst_rules),
        (base / "qc/sessions", qc_rules),
        (base / "maintenance/events", maint_rules)
    ]

    changed_files = []
    total_replacements = 0

    for target_dir, rules in targets:
        if not target_dir.exists(): continue
        
        for file in list(target_dir.rglob("*.yaml")) + list(target_dir.rglob("*.yml")):
            changed, reps = autofix_file(file, rules, vocabs, args.check)
            if changed:
                changed_files.append(file)
                total_replacements += reps

    mode = "Would update" if args.check else "Updated"
    print(f"{mode} {len(changed_files)} file(s); replacements: {total_replacements}.")

    if changed_files:
        for cf in changed_files:
            print(f" - {cf.relative_to(base)}")
            
    if args.check and changed_files:
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
