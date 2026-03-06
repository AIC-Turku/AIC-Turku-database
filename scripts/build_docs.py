"""Generate Markdown documentation from vocabulary YAML files."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Term:
    term_id: str
    label: str
    description: str
    synonyms: list[str]


@dataclass
class Vocabulary:
    key: str
    title: str
    terms: list[Term]


TITLE_OVERRIDES: dict[str, str] = {
    "modalities": "Modalities",
    "objective_immersion": "Objective Immersion",
    "detector_kinds": "Detectors",
    "scanner_types": "Scanner Types",
    "light_source_kinds": "Light Sources",
    "modules": "Modules",
    "objective_corrections": "Objective Corrections",
    "maintenance_reason": "Maintenance Reasons",
    "maintenance_action": "Maintenance Actions",
}

VOCAB_ORDER: list[str] = [
    "modalities",
    "objective_immersion",
    "detector_kinds",
    "scanner_types",
    "light_source_kinds",
    "modules",
    "objective_corrections",
    "maintenance_reason",
    "maintenance_action",
]


SYSTEM_PROMPT = (
    "You are an expert bioimaging facility AI assistant. "
    "Your job is to help researchers map their experimental needs to the exact terminology "
    "used in our facility's database."
)

INTENT_GUIDANCE: list[tuple[str, str, str]] = [
    (
        "fast live cell",
        "confocal_spinning_disk",
        "Use for low-phototoxicity, high-speed 3D imaging in living samples.",
    ),
    (
        "deep tissue",
        "multiphoton",
        "Prefer for deeper penetration and reduced out-of-plane photodamage.",
    ),
    (
        "membrane events near coverslip",
        "tirf",
        "Ideal for sub-200 nm interface processes such as membrane trafficking.",
    ),
    (
        "highest spatial resolution",
        "sted",
        "Recommend when users need sub-diffraction super-resolution and can tolerate specialized workflows.",
    ),
    (
        "label-free live cell morphology",
        "phase_contrast",
        "Best first choice for unlabeled transparent cells in routine culture vessels.",
    ),
]


def prettify_title(vocab_key: str) -> str:
    if vocab_key in TITLE_OVERRIDES:
        return TITLE_OVERRIDES[vocab_key]
    return vocab_key.replace("_", " ").title()


def load_vocab(vocab_file: Path) -> Vocabulary:
    raw_terms = _parse_terms(vocab_file)

    terms: list[Term] = []
    for item in raw_terms:
        if not isinstance(item, dict):
            continue

        raw_id = item.get("id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue

        label = item.get("label")
        description = item.get("description")
        synonyms = item.get("synonyms")

        normalized_synonyms = [
            synonym.strip()
            for synonym in (synonyms if isinstance(synonyms, list) else [])
            if isinstance(synonym, str) and synonym.strip()
        ]

        terms.append(
            Term(
                term_id=raw_id.strip(),
                label=label.strip() if isinstance(label, str) and label.strip() else raw_id.strip(),
                description=description.strip() if isinstance(description, str) else "",
                synonyms=normalized_synonyms,
            )
        )

    terms.sort(key=lambda term: term.label.casefold())
    return Vocabulary(key=vocab_file.stem, title=prettify_title(vocab_file.stem), terms=terms)


def _parse_scalar(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if value[0] in {'"', "'"} and value[-1] == value[0]:
        return ast.literal_eval(value)
    return value


def _parse_synonyms(value: str) -> list[str]:
    parsed = ast.literal_eval(value.strip())
    if not isinstance(parsed, list):
        return []
    return [item.strip() for item in parsed if isinstance(item, str) and item.strip()]


def _parse_terms(vocab_file: Path) -> list[dict[str, Any]]:
    lines = vocab_file.read_text(encoding="utf-8").splitlines()
    terms: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped == "terms:":
            continue

        if stripped.startswith("- "):
            if current:
                terms.append(current)
            current = {}
            body = stripped[2:].strip()
            if body and ":" in body:
                key, value = body.split(":", 1)
                current[key.strip()] = _parse_scalar(value)
            continue

        if current is None or ":" not in stripped:
            continue

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key == "synonyms" and value:
            current[key] = _parse_synonyms(value)
        else:
            current[key] = _parse_scalar(value)

    if current:
        terms.append(current)

    return terms


def _sort_vocabularies(vocabularies: list[Vocabulary]) -> list[Vocabulary]:
    order = {key: idx for idx, key in enumerate(VOCAB_ORDER)}
    return sorted(vocabularies, key=lambda vocab: (order.get(vocab.key, len(order)), vocab.title.casefold()))


def render_human_dictionary(vocabularies: list[Vocabulary]) -> str:
    lines: list[str] = [
        "# Vocabulary Dictionary",
        "",
        "This page is generated from files under `vocab/`. Do not edit manually.",
        "",
    ]

    for vocab in vocabularies:
        lines.extend([f"## {vocab.title}", "", "| Label | ID | Synonyms | Description |", "| --- | --- | --- | --- |"])
        for term in vocab.terms:
            synonyms = ", ".join(term.synonyms) if term.synonyms else "—"
            description = term.description.replace("|", "\\|")
            lines.append(f"| {term.label} | `{term.term_id}` | {synonyms} | {description} |")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_llm_guide(vocabularies: list[Vocabulary]) -> str:
    lines: list[str] = [
        "# LLM Microscopy Assistant Context",
        "",
        "This page is generated from files under `vocab/`. Do not edit manually.",
        "",
        "## System Prompt",
        "",
        f"> {SYSTEM_PROMPT}",
        "",
        "## Assistant Rules",
        "",
        "- Always prefer canonical term IDs shown below when translating user intent.",
        "- Explain recommendations in plain language, but include exact database IDs in backticks.",
        "- If users provide ambiguous language, ask one clarifying question and still provide best-match IDs.",
        "- Never invent IDs that are not listed in this document.",
        "",
        "## Intent Mapping Guidance",
        "",
    ]

    for phrase, term_id, rationale in INTENT_GUIDANCE:
        lines.append(f"- When a user asks for **\"{phrase}\"**, recommend `{term_id}`. {rationale}")

    lines.extend(["", "## Controlled Vocabulary (Canonical IDs)", ""])

    for vocab in vocabularies:
        lines.extend([f"### {vocab.title} (`{vocab.key}`)", ""])
        for term in vocab.terms:
            synonyms = ", ".join(f"`{syn}`" for syn in term.synonyms) if term.synonyms else "none"
            lines.extend(
                [
                    f"- **{term.label}**",
                    f"  - ID: `{term.term_id}`",
                    f"  - Synonyms: {synonyms}",
                    f"  - Definition: {term.description}",
                ]
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def discover_vocab(vocab_dir: Path) -> list[Vocabulary]:
    vocab_files = sorted(path for path in vocab_dir.glob("*.yaml") if path.is_file())
    return _sort_vocabularies([load_vocab(path) for path in vocab_files])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vocab-dir", type=Path, default=Path("vocab"))
    parser.add_argument("--docs-dir", type=Path, default=Path("docs"))
    args = parser.parse_args()

    vocabularies = discover_vocab(args.vocab_dir)
    args.docs_dir.mkdir(parents=True, exist_ok=True)

    human_path = args.docs_dir / "vocabulary_dictionary.md"
    llm_path = args.docs_dir / "llm_microscopy_assistant.md"

    human_path.write_text(render_human_dictionary(vocabularies), encoding="utf-8")
    llm_path.write_text(render_llm_guide(vocabularies), encoding="utf-8")

    print(f"Wrote {human_path}")
    print(f"Wrote {llm_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
