from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import yaml

def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _iter_yaml_files(base_dir: Path) -> Iterable[Path]:
    if not base_dir.exists() or not base_dir.is_dir():
        return []
    return [p for p in sorted(base_dir.rglob("*")) if p.is_file() and p.suffix.lower() in {".yaml", ".yml"}]


def _load_yaml(
    path: Path, *, reject_duplicate_keys: bool = False
) -> tuple[dict[str, Any] | None, str | None]:
    safe_loader = getattr(yaml, "SafeLoader", None)
    if safe_loader is None:
        text = path.read_text(encoding="utf-8")
        try:
            from ruamel.yaml import YAML as RuamelYAML
            from ruamel.yaml.error import YAMLError as RuamelYAMLError
        except ImportError:
            if reject_duplicate_keys:
                return None, "YAML loader cannot enforce duplicate-key rejection."
            try:
                payload = yaml.safe_load(text)
            except (OSError, yaml.YAMLError) as exc:
                return None, str(exc)
        else:
            try:
                fallback_yaml = RuamelYAML(typ="safe")
                fallback_yaml.allow_duplicate_keys = not reject_duplicate_keys
                payload = fallback_yaml.load(text)
            except (OSError, RuamelYAMLError) as exc:
                return None, str(exc)
        if payload is None:
            return None, "YAML document is empty."
        if not isinstance(payload, dict):
            return None, f"Expected YAML mapping/object at top level, found {type(payload).__name__}."
        return payload, None

    loader = safe_loader
    if reject_duplicate_keys:
        class UniqueKeyLoader(safe_loader):
            pass

        def construct_unique_mapping(
            active_loader: yaml.SafeLoader, node: yaml.nodes.MappingNode, deep: bool = False
        ) -> dict[Any, Any]:
            mapping: dict[Any, Any] = {}
            for key_node, value_node in node.value:
                key = active_loader.construct_object(key_node, deep=deep)
                if key in mapping:
                    raise yaml.YAMLError(
                        f"Duplicate YAML key {key!r} at line {key_node.start_mark.line + 1}."
                    )
                mapping[key] = active_loader.construct_object(value_node, deep=deep)
            return mapping

        UniqueKeyLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            construct_unique_mapping,
        )
        loader = UniqueKeyLoader

    try:
        payload = yaml.load(path.read_text(encoding="utf-8"), Loader=loader)
    except (OSError, yaml.YAMLError) as exc:
        return None, str(exc)

    if payload is None:
        return None, "YAML document is empty."
    if not isinstance(payload, dict):
        return None, f"Expected YAML mapping/object at top level, found {type(payload).__name__}."

    return payload, None
