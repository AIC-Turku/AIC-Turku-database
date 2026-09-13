from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel: str, content: str) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def replace_once(rel: str, old: str, new: str) -> None:
    text = read(rel)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{rel}: expected exactly one literal replacement, found {count}")
    write(rel, text.replace(old, new, 1))


def regex_once(rel: str, pattern: str, replacement: str) -> None:
    text = read(rel)
    matches = list(re.finditer(pattern, text, flags=re.S | re.M))
    if len(matches) != 1:
        raise RuntimeError(f"{rel}: expected exactly one regex replacement, found {len(matches)} for {pattern!r}")
    match = matches[0]
    write(rel, text[: match.start()] + replacement + text[match.end() :])
