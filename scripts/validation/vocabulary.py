from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from scripts.validation.model import VocabularyTerm


class Vocabulary:
    """Loads vocabulary files and validates values against canonical IDs/synonyms."""

    def __init__(
        self,
        vocab_dir: Path = Path("vocab"),
        vocab_registry: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.vocab_dir = vocab_dir
        self.vocab_registry = vocab_registry
        self.terms_by_vocab: dict[str, dict[str, VocabularyTerm]] = {}
        self.valid_ids_by_vocab: dict[str, set[str]] = {}
        self.synonyms_by_vocab: dict[str, dict[str, str]] = {}
        self._load_all()

    @staticmethod
    def _normalize(value: str) -> str:
        return value.strip()

    def _load_all(self) -> None:
        if self.vocab_registry:
            vocab_items = []
            for vocab_name, vocab_spec in self.vocab_registry.items():
                if not isinstance(vocab_spec, dict):
                    continue
                inline_allowed = vocab_spec.get("allowed_values")
                if vocab_spec.get("source") == "inline" and isinstance(inline_allowed, list):
                    self.terms_by_vocab[vocab_name] = {
                        value: VocabularyTerm(
                            id=value,
                            label=value,
                            description="",
                            synonyms=[],
                            metadata={},
                        )
                        for value in [str(item).strip() for item in inline_allowed if str(item).strip()]
                    }
                    self.valid_ids_by_vocab[vocab_name] = set(self.terms_by_vocab[vocab_name].keys())
                    self.synonyms_by_vocab[vocab_name] = {}
                    continue

                raw_file = vocab_spec.get("file") or vocab_spec.get("path")
                if not isinstance(raw_file, str) or not raw_file.strip():
                    continue
                vocab_items.append((vocab_name, Path(raw_file.strip())))
        else:
            vocab_items = [(vocab_file.stem, vocab_file) for vocab_file in sorted(self.vocab_dir.glob("*.yaml"))]

        for vocab_name, vocab_file in vocab_items:
            payload, load_error = _load_yaml(vocab_file)
            if load_error is not None or payload is None:
                continue

            raw_terms = payload.get("terms")
            if not isinstance(raw_terms, list):
                continue

            terms: dict[str, VocabularyTerm] = {}
            valid_ids: set[str] = set()
            synonym_lookup: dict[str, str] = {}
            for raw_term in raw_terms:
                if not isinstance(raw_term, dict):
                    continue

                raw_id = raw_term.get("id")
                if not isinstance(raw_id, str) or not raw_id.strip():
                    continue

                canonical_id = raw_id.strip()
                label = raw_term.get("label")
                description = raw_term.get("description")
                raw_synonyms = raw_term.get("synonyms")
                term_synonyms = [
                    synonym.strip()
                    for synonym in (raw_synonyms if isinstance(raw_synonyms, list) else [])
                    if isinstance(synonym, str) and synonym.strip()
                ]

                terms[canonical_id] = VocabularyTerm(
                    id=canonical_id,
                    label=label.strip() if isinstance(label, str) else canonical_id,
                    description=description.strip() if isinstance(description, str) else "",
                    synonyms=term_synonyms,
                    metadata={
                        key: value
                        for key, value in raw_term.items()
                        if key not in {"id", "label", "description", "synonyms"}
                    },
                )
                valid_ids.add(canonical_id)

                for synonym in term_synonyms:
                    synonym_lookup[synonym.casefold()] = canonical_id

            self.terms_by_vocab[vocab_name] = terms
            self.valid_ids_by_vocab[vocab_name] = valid_ids
            self.synonyms_by_vocab[vocab_name] = synonym_lookup

    def check(self, vocab_name: str, value: Any) -> tuple[bool, str | None]:
        if not isinstance(value, str):
            return False, None

        cleaned = self._normalize(value)
        if not cleaned:
            return False, None

        if cleaned in self.valid_ids_by_vocab.get(vocab_name, set()):
            return True, None

        canonical = self.synonyms_by_vocab.get(vocab_name, {}).get(cleaned.casefold())
        if canonical is not None:
            return False, canonical

        return False, None

    def resolve_canonical(self, vocab_name: str, value: Any) -> str | None:
        if not isinstance(value, str):
            return None

        cleaned = self._normalize(value)
        if not cleaned:
            return None

        if cleaned in self.valid_ids_by_vocab.get(vocab_name, set()):
            return cleaned

        return self.synonyms_by_vocab.get(vocab_name, {}).get(cleaned.casefold())

    def get_term(self, vocab_name: str, canonical_id: str) -> VocabularyTerm | None:
        return self.terms_by_vocab.get(vocab_name, {}).get(canonical_id)


def _load_yaml(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return None, str(exc)

    if payload is None:
        return None, "YAML document is empty."
    if not isinstance(payload, dict):
        return None, f"Expected YAML mapping/object at top level, found {type(payload).__name__}."

    return payload, None
