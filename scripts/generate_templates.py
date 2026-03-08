#!/usr/bin/env python3
"""Generate starter templates directly from schema policy files."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
import argparse
import json
import subprocess


@dataclass
class Rule:
    path: str
    title: str
    rationale: str
    value_type: str
    group: str
    allowed_values: list[object] = field(default_factory=list)
    item_type: str | None = None
    vocab: str | None = None


@dataclass
class Node:
    kind: str = "mapping"  # mapping | list | scalar
    children: dict[str, "Node"] = field(default_factory=dict)
    item: "Node" | None = None
    rule: Rule | None = None


SCHEMA_TARGETS = (
    (Path("schema/instrument_policy.yaml"), Path("templates/microscope_template.yaml")),
    (Path("schema/QC_policy.yaml"), Path("templates/QC_template.yaml")),
    (Path("schema/maintenance_policy.yaml"), Path("templates/maintenance_template.yaml")),
)


def _load_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore

        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except ModuleNotFoundError:
        command = [
            "ruby",
            "-ryaml",
            "-rjson",
            "-e",
            "print JSON.generate(YAML.load_file(ARGV[0]))",
            str(path),
        ]
        raw = subprocess.check_output(command, text=True)
        payload = json.loads(raw)

    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a top-level mapping.")
    return payload


def _default_title(path: str) -> str:
    leaf = path.split(".")[-1].replace("[]", "")
    return leaf.replace("_", " ").strip().title() or path


def _default_group(path: str) -> str:
    top = path.split(".")[0].replace("[]", "")
    return top.replace("_", " ").strip().title()


def _extract_rules(schema: dict) -> list[Rule]:
    rules: list[Rule] = []
    seen_paths: set[str] = set()

    sections = schema.get("sections")
    if isinstance(sections, list) and sections:
        for section in sections:
            if not isinstance(section, dict):
                continue
            group = str(section.get("title") or "General")
            for raw in section.get("rules", []) or []:
                if not isinstance(raw, dict):
                    continue
                path = raw.get("path")
                if not isinstance(path, str) or not path.strip() or path in seen_paths:
                    continue
                seen_paths.add(path)
                rules.append(
                    Rule(
                        path=path,
                        title=str(raw.get("title") or _default_title(path)),
                        rationale=str(raw.get("rationale") or ""),
                        value_type=str(raw.get("type") or "string"),
                        group=group,
                        allowed_values=list(raw.get("allowed_values") or []),
                        item_type=(str(raw.get("item_type")) if raw.get("item_type") is not None else None),
                        vocab=(str(raw.get("vocab")) if raw.get("vocab") is not None else None),
                    )
                )
    else:
        raw_rules: Iterable[dict] = schema.get("field_rules", [])
        for raw in raw_rules:
            path = raw.get("path")
            if not isinstance(path, str) or not path.strip() or path in seen_paths:
                continue
            seen_paths.add(path)
            rules.append(
                Rule(
                    path=path,
                    title=str(raw.get("title") or _default_title(path)),
                    rationale=str(raw.get("rationale") or ""),
                    value_type=str(raw.get("type") or "string"),
                    group=_default_group(path),
                    allowed_values=list(raw.get("allowed_values") or []),
                    item_type=(str(raw.get("item_type")) if raw.get("item_type") is not None else None),
                    vocab=(str(raw.get("vocab")) if raw.get("vocab") is not None else None),
                )
            )
    return rules


def _load_vocab_values(schema: dict) -> dict[str, list[str]]:
    registry = schema.get("vocab_registry")
    if not isinstance(registry, dict):
        return {}

    values: dict[str, list[str]] = {}
    for vocab_name, spec in registry.items():
        if not isinstance(spec, dict):
            continue

        if spec.get("source") == "inline" and isinstance(spec.get("allowed_values"), list):
            values[str(vocab_name)] = [str(v) for v in spec["allowed_values"]]
            continue

        path = spec.get("path") or spec.get("file")
        if not isinstance(path, str) or not path.strip():
            continue

        vocab_payload = _load_yaml(Path(path))
        terms = vocab_payload.get("terms")
        if not isinstance(terms, list):
            continue

        ids: list[str] = []
        for term in terms:
            if isinstance(term, dict) and isinstance(term.get("id"), str):
                ids.append(term["id"])
        values[str(vocab_name)] = ids

    return values


def _ensure_child(mapping_node: Node, key: str, kind: str = "mapping") -> Node:
    if key not in mapping_node.children:
        mapping_node.children[key] = Node(kind=kind)
        return mapping_node.children[key]

    child = mapping_node.children[key]
    if child.kind != kind:
        if kind == "mapping" and child.kind == "scalar":
            child.kind = "mapping"
        elif kind == "list" and child.kind == "scalar":
            child.kind = "list"
            if child.item is None:
                child.item = Node(kind="scalar")
    return child


def _rule_leaf_kind(rule: Rule) -> str:
    return "list" if rule.value_type == "list" else "scalar"


def _insert_rule(root: Node, rule: Rule) -> None:
    tokens = rule.path.split(".")
    current = root

    for index, token in enumerate(tokens):
        is_last = index == len(tokens) - 1

        if token.endswith("[]"):
            key = token[:-2]
            list_node = _ensure_child(current, key, kind="list")
            if list_node.item is None or list_node.item.kind == "scalar":
                list_node.item = Node(kind="mapping")

            if is_last:
                list_node.rule = rule
                return

            current = list_node.item
            continue

        desired_kind = _rule_leaf_kind(rule) if is_last else "mapping"
        child = _ensure_child(current, token, kind=desired_kind)

        if is_last:
            child.rule = rule
            if desired_kind == "list" and child.item is None:
                child.item = Node(kind="scalar")
        else:
            current = child


def _rule_default_value(rule: Rule | None) -> object:
    if rule is None:
        return ""

    if rule.allowed_values:
        return rule.allowed_values[0]

    if rule.value_type in {"integer", "year"}:
        return 0
    if rule.value_type in {"number", "float"}:
        return 0.0
    if rule.value_type in {"bool", "boolean"}:
        return False
    if rule.value_type in {"mapping", "object"}:
        return {}
    return ""


def _yaml_scalar(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value))


def _top_key(path: str) -> str:
    return path.split(".")[0].replace("[]", "")


def _build_group_lookup(rules: list[Rule]) -> dict[str, str]:
    pretty_names = {
        "instrument": "Instrument",
        "modalities": "Imaging Modalities",
        "modules": "Hardware Modules",
        "software": "Software",
        "hardware": "Hardware Configuration",
    }
    lookup: OrderedDict[str, str] = OrderedDict()
    for rule in rules:
        key = _top_key(rule.path)
        lookup.setdefault(key, pretty_names.get(key, key.replace("_", " ").title()))
    return dict(lookup)


def _banner(title: str) -> list[str]:
    clean = title.strip().upper() or "SECTION"
    return ["# -----------------------------------------------------------------------------", f"# {clean}", "# -----------------------------------------------------------------------------"]


def _allowed_values_comment(rule: Rule, vocab_values: dict[str, list[str]]) -> str | None:
    if rule.allowed_values:
        return "Allowed values: " + ", ".join(str(v) for v in rule.allowed_values)
    if rule.vocab and rule.vocab in vocab_values and vocab_values[rule.vocab]:
        return "Allowed values (canonical IDs): " + ", ".join(vocab_values[rule.vocab])
    return None


def _inline_comment(rule: Rule | None, vocab_values: dict[str, list[str]]) -> str:
    if rule is None:
        return ""

    line = rule.title
    if rule.rationale:
        line += f": {rule.rationale}"

    allowed = _allowed_values_comment(rule, vocab_values)
    if allowed:
        line += f" | {allowed}"

    return f"  # {line}"


def _render_node(
    node: Node,
    indent: int,
    vocab_values: dict[str, list[str]],
    top_key_groups: dict[str, str],
    top_level: bool = False,
) -> list[str]:
    lines: list[str] = []
    prefix = " " * indent

    current_group: str | None = None
    for key, child in node.children.items():
        if top_level:
            group = top_key_groups.get(key, key.replace("_", " ").title())
            if current_group != group:
                if lines:
                    lines.append("")
                lines.extend(_banner(group))
                current_group = group

        inline_comment = _inline_comment(child.rule, vocab_values)
        if child.kind == "scalar":
            lines.append(f"{prefix}{key}: {_yaml_scalar(_rule_default_value(child.rule))}{inline_comment}")
            continue

        if child.kind == "list":
            lines.append(f"{prefix}{key}:{inline_comment}")
            lines.extend(_render_list(child, indent + 2, vocab_values, top_key_groups))
            continue

        lines.append(f"{prefix}{key}:{inline_comment}")
        lines.extend(_render_node(child, indent + 2, vocab_values, top_key_groups, top_level=False))

    return lines


def _render_list(node: Node, indent: int, vocab_values: dict[str, list[str]], top_key_groups: dict[str, str]) -> list[str]:
    prefix = " " * indent

    item = node.item or Node(kind="scalar", rule=node.rule)
    if item.kind == "scalar":
        return [f"{prefix}- {_yaml_scalar(_rule_default_value(item.rule or node.rule))}"]

    lines = [f"{prefix}-"]
    lines.extend(_render_node(item, indent + 2, vocab_values, top_key_groups, top_level=False))
    return lines


def build_template(schema_path: Path) -> str:
    schema = _load_yaml(schema_path)
    rules = _extract_rules(schema)

    root = Node(kind="mapping")
    for rule in rules:
        _insert_rule(root, rule)

    vocab_values = _load_vocab_values(schema)
    top_key_groups = _build_group_lookup(rules)

    rendered = [
        "# AUTO-GENERATED FILE. Do not edit manually.",
        f"# Source schema: {schema_path.as_posix()}",
        "",
        *_render_node(root, indent=0, vocab_values=vocab_values, top_key_groups=top_key_groups, top_level=True),
        "",
    ]
    return "\n".join(rendered)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if generated output differs from templates on disk.")
    args = parser.parse_args()

    dirty: list[Path] = []
    for schema_path, template_path in SCHEMA_TARGETS:
        output = build_template(schema_path)
        if args.check:
            existing = template_path.read_text(encoding="utf-8") if template_path.exists() else ""
            if existing != output:
                dirty.append(template_path)
        else:
            template_path.write_text(output, encoding="utf-8")
            print(f"Generated {template_path}")

    if args.check and dirty:
        print("Out-of-date templates:")
        for path in dirty:
            print(f" - {path}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
