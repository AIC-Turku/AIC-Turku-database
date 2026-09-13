from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.validation.io import _load_yaml
from scripts.validation.model import VocabularyTerm


class VocabularyDefinitionError(ValueError):
    """Raised when controlled-vocabulary definitions are ambiguous or malformed."""




def merge_vocab_registries(*registries: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Merge registry mappings without allowing silent namespace redefinition."""
    merged: dict[str, dict[str, Any]] = {}
    for registry in registries:
        if not isinstance(registry, dict):
            continue
        for name, spec in registry.items():
            if name in merged:
                existing = merged[name]
                if not isinstance(existing, dict) or not isinstance(spec, dict):
                    if existing != spec:
                        raise VocabularyDefinitionError(
                            f"Vocabulary namespace '{name}' is defined inconsistently across policies."
                        )
                    continue
                existing_path = existing.get("path") or existing.get("file")
                new_path = spec.get("path") or spec.get("file")
                if existing.get("source") != spec.get("source") or existing_path != new_path:
                    raise VocabularyDefinitionError(
                        f"Vocabulary namespace '{name}' is defined inconsistently across policies."
                    )
                for key in set(existing) & set(spec):
                    if key in {"path", "file"}:
                        continue
                    if existing[key] != spec[key]:
                        raise VocabularyDefinitionError(
                            f"Vocabulary namespace '{name}' has conflicting setting '{key}'."
                        )
                merged[name] = {**existing, **spec}
                continue
            merged[name] = dict(spec) if isinstance(spec, dict) else spec
    return merged

class Vocabulary:
    """Load and resolve controlled vocabularies with strict ambiguity checks."""

    def __init__(
        self,
        vocab_dir: Path = Path("vocab"),
        vocab_registry: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.vocab_dir = Path(vocab_dir)
        self.repo_root = self.vocab_dir.parent if self.vocab_dir.name == "vocab" else Path.cwd()
        self.vocab_registry = vocab_registry
        self.terms_by_vocab: dict[str, dict[str, VocabularyTerm]] = {}
        self.valid_ids_by_vocab: dict[str, set[str]] = {}
        self.synonyms_by_vocab: dict[str, dict[str, str]] = {}
        self.classifications_by_vocab: dict[str, dict[str, str]] = {}
        self.registry_spec_by_vocab: dict[str, dict[str, Any]] = {}
        self._load_all()

    @staticmethod
    def _normalize(value: str) -> str:
        return value.strip()

    @staticmethod
    def _load_vocab_file(path: Path) -> dict[str, Any]:
        payload, load_error = _load_yaml(path, reject_duplicate_keys=True)
        if load_error is not None:
            raise VocabularyDefinitionError(
                f"Failed loading vocabulary '{path.as_posix()}': {load_error}"
            )
        if not isinstance(payload, dict):
            raise VocabularyDefinitionError(f"Vocabulary '{path.as_posix()}' must be a YAML mapping.")
        return payload

    def _resolve_vocab_path(self, raw_path: str) -> Path:
        path = Path(raw_path.strip())
        if path.is_absolute():
            return path
        return self.repo_root / path

    def _register_terms(self, vocab_name: str, raw_terms: list[Any], *, source: str) -> None:
        terms: dict[str, VocabularyTerm] = {}
        valid_ids: set[str] = set()
        synonym_lookup: dict[str, str] = {}
        classification_lookup: dict[str, str] = {}
        canonical_casefold: dict[str, str] = {}

        for index, raw_term in enumerate(raw_terms):
            if not isinstance(raw_term, dict):
                raise VocabularyDefinitionError(f"{source}: term #{index + 1} must be a mapping.")
            raw_id = raw_term.get("id")
            if not isinstance(raw_id, str) or not raw_id.strip():
                raise VocabularyDefinitionError(f"{source}: term #{index + 1} needs a non-empty string id.")
            canonical_id = raw_id.strip()
            canonical_key = canonical_id.casefold()
            if canonical_id in valid_ids or canonical_key in canonical_casefold:
                previous = canonical_casefold.get(canonical_key, canonical_id)
                raise VocabularyDefinitionError(
                    f"{source}: duplicate canonical id '{canonical_id}' conflicts with '{previous}'."
                )

            label = raw_term.get("label")
            description = raw_term.get("description")

            raw_synonyms = raw_term.get("synonyms", [])
            if raw_synonyms is None:
                raw_synonyms = []
            if not isinstance(raw_synonyms, list):
                raise VocabularyDefinitionError(f"{source}: term '{canonical_id}' synonyms must be a list.")
            term_synonyms: list[str] = []
            seen_local: set[str] = set()
            for synonym in raw_synonyms:
                if not isinstance(synonym, str) or not synonym.strip():
                    raise VocabularyDefinitionError(f"{source}: term '{canonical_id}' has an invalid synonym.")
                cleaned = synonym.strip()
                key = cleaned.casefold()
                if key in seen_local:
                    continue
                seen_local.add(key)
                term_synonyms.append(cleaned)

            terms[canonical_id] = VocabularyTerm(
                id=canonical_id,
                label=label.strip() if isinstance(label, str) and label.strip() else canonical_id,
                description=description.strip() if isinstance(description, str) else "",
                synonyms=term_synonyms,
                metadata={
                    key: value
                    for key, value in raw_term.items()
                    if key not in {"id", "label", "description", "synonyms"}
                },
            )
            valid_ids.add(canonical_id)
            canonical_casefold[canonical_key] = canonical_id

        for canonical_id, term in terms.items():
            for synonym in term.synonyms:
                key = synonym.casefold()
                shadowed_id = canonical_casefold.get(key)
                if shadowed_id is not None and shadowed_id != canonical_id:
                    raise VocabularyDefinitionError(
                        f"{source}: synonym '{synonym}' for '{canonical_id}' shadows canonical id '{shadowed_id}'."
                    )
                previous = synonym_lookup.get(key)
                if previous is not None and previous != canonical_id:
                    raise VocabularyDefinitionError(
                        f"{source}: synonym '{synonym}' is ambiguous between '{previous}' and '{canonical_id}'."
                    )
                synonym_lookup[key] = canonical_id

        for canonical_id, term in terms.items():
            raw_classified = term.metadata.get("classified_values", [])
            if raw_classified is None:
                raw_classified = []
            if not isinstance(raw_classified, list):
                raise VocabularyDefinitionError(
                    f"{source}: term '{canonical_id}' classified_values must be a list."
                )
            seen_classified: set[str] = set()
            for classified_value in raw_classified:
                if not isinstance(classified_value, str) or not classified_value.strip():
                    raise VocabularyDefinitionError(
                        f"{source}: term '{canonical_id}' has an invalid classified value."
                    )
                cleaned = classified_value.strip()
                key = cleaned.casefold()
                if key in seen_classified:
                    continue
                seen_classified.add(key)
                shadowed_id = canonical_casefold.get(key)
                if shadowed_id is not None and shadowed_id != canonical_id:
                    raise VocabularyDefinitionError(
                        f"{source}: classified value '{cleaned}' for '{canonical_id}' shadows canonical id '{shadowed_id}'."
                    )
                synonym_owner = synonym_lookup.get(key)
                if synonym_owner is not None:
                    if synonym_owner != canonical_id:
                        raise VocabularyDefinitionError(
                            f"{source}: classified value '{cleaned}' for '{canonical_id}' conflicts with synonym of '{synonym_owner}'."
                        )
                    continue
                previous = classification_lookup.get(key)
                if previous is not None and previous != canonical_id:
                    raise VocabularyDefinitionError(
                        f"{source}: classified value '{cleaned}' is ambiguous between '{previous}' and '{canonical_id}'."
                    )
                classification_lookup[key] = canonical_id

        self.terms_by_vocab[vocab_name] = terms
        self.valid_ids_by_vocab[vocab_name] = valid_ids
        self.synonyms_by_vocab[vocab_name] = synonym_lookup
        self.classifications_by_vocab[vocab_name] = classification_lookup

    def _load_all(self) -> None:
        if self.vocab_registry is not None:
            vocab_items: list[tuple[str, Path]] = []
            for vocab_name, vocab_spec in self.vocab_registry.items():
                if not isinstance(vocab_spec, dict):
                    raise VocabularyDefinitionError(f"Vocabulary registry entry '{vocab_name}' must be a mapping.")
                self.registry_spec_by_vocab[vocab_name] = dict(vocab_spec)
                inline_allowed = vocab_spec.get("allowed_values")
                if vocab_spec.get("source") == "inline":
                    if not isinstance(inline_allowed, list):
                        raise VocabularyDefinitionError(
                            f"Inline vocabulary '{vocab_name}' needs an allowed_values list."
                        )
                    values = [str(item).strip() for item in inline_allowed if str(item).strip()]
                    raw_terms = [
                        {"id": value, "label": value, "description": f"Allowed value: {value}."}
                        for value in values
                    ]
                    self._register_terms(vocab_name, raw_terms, source=f"inline vocabulary '{vocab_name}'")
                    continue

                raw_file = vocab_spec.get("file") or vocab_spec.get("path")
                if not isinstance(raw_file, str) or not raw_file.strip():
                    raise VocabularyDefinitionError(f"Vocabulary registry entry '{vocab_name}' needs file/path.")
                vocab_items.append((vocab_name, self._resolve_vocab_path(raw_file)))
        else:
            if not self.vocab_dir.exists():
                raise VocabularyDefinitionError(f"Vocabulary directory '{self.vocab_dir.as_posix()}' does not exist.")
            vocab_items = [(vocab_file.stem, vocab_file) for vocab_file in sorted(self.vocab_dir.glob("*.yaml"))]

        for vocab_name, vocab_file in vocab_items:
            if not vocab_file.exists():
                raise VocabularyDefinitionError(
                    f"Vocabulary '{vocab_name}' references missing file '{vocab_file.as_posix()}'."
                )
            payload = self._load_vocab_file(vocab_file)
            raw_terms = payload.get("terms")
            if not isinstance(raw_terms, list):
                raise VocabularyDefinitionError(f"Vocabulary '{vocab_file.as_posix()}' needs a terms list.")
            self._register_terms(vocab_name, raw_terms, source=vocab_file.as_posix())

        self._validate_semantic_references()

    def _validate_semantic_references(self) -> None:
        def require(vocab_name: str, term_id: Any, *, context: str) -> None:
            if vocab_name not in self.valid_ids_by_vocab:
                return
            if not isinstance(term_id, str) or term_id not in self.valid_ids_by_vocab[vocab_name]:
                raise VocabularyDefinitionError(
                    f"{context}: unknown referenced term '{term_id}' in vocabulary '{vocab_name}'."
                )

        route_terms = self.terms_by_vocab.get("optical_routes", {})
        for route_id, term in route_terms.items():
            covers = term.metadata.get("covers")
            if not isinstance(covers, dict):
                continue
            for axis in ("imaging_modes", "contrast_methods"):
                values = covers.get(axis, [])
                if values is None:
                    continue
                if not isinstance(values, list):
                    raise VocabularyDefinitionError(
                        f"optical_routes.{route_id}.covers.{axis} must be a list."
                    )
                for value in values:
                    require(axis, value, context=f"optical_routes.{route_id}.covers.{axis}")

        capability_targets = {
            "imaging_modes": "imaging_modes",
            "contrast_methods": "contrast_methods",
            "readouts": "measurement_readouts",
            "workflows": "workflow_tags",
            "assay_operations": "assay_operations",
            "non_optical": "non_optical_capabilities",
        }
        for module_id, term in self.terms_by_vocab.get("modules", {}).items():
            tags = term.metadata.get("tags")
            provides = tags.get("provides_capability") if isinstance(tags, dict) else None
            if not isinstance(provides, dict):
                continue
            for axis, values in provides.items():
                target = capability_targets.get(axis)
                if target is None:
                    raise VocabularyDefinitionError(
                        f"modules.{module_id}.tags.provides_capability uses unknown axis '{axis}'."
                    )
                if not isinstance(values, list):
                    raise VocabularyDefinitionError(
                        f"modules.{module_id}.tags.provides_capability.{axis} must be a list."
                    )
                for value in values:
                    require(target, value, context=f"modules.{module_id}.tags.provides_capability.{axis}")

    def check(self, vocab_name: str, value: Any) -> tuple[bool, str | None]:
        if not isinstance(value, str):
            return False, None
        cleaned = self._normalize(value)
        if not cleaned:
            return False, None
        if vocab_name not in self.valid_ids_by_vocab:
            return False, None
        if cleaned in self.valid_ids_by_vocab[vocab_name]:
            return True, None
        spec = self.registry_spec_by_vocab.get(vocab_name, {})
        if spec.get("allow_synonyms_on_input") is False:
            return False, None
        canonical = self.synonyms_by_vocab[vocab_name].get(cleaned.casefold())
        return (False, canonical) if canonical is not None else (False, None)

    def resolve_canonical(self, vocab_name: str, value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = self._normalize(value)
        if not cleaned or vocab_name not in self.valid_ids_by_vocab:
            return None
        if cleaned in self.valid_ids_by_vocab[vocab_name]:
            return cleaned
        spec = self.registry_spec_by_vocab.get(vocab_name, {})
        if spec.get("allow_synonyms_on_input") is False:
            return None
        return self.synonyms_by_vocab[vocab_name].get(cleaned.casefold())


    def classify_canonical(self, vocab_name: str, value: Any) -> str | None:
        """Return a category match without authorizing automatic rewriting."""
        if not isinstance(value, str):
            return None
        resolved = self.resolve_canonical(vocab_name, value)
        if resolved is not None:
            return resolved
        cleaned = self._normalize(value)
        if not cleaned or vocab_name not in self.valid_ids_by_vocab:
            return None
        return self.classifications_by_vocab.get(vocab_name, {}).get(cleaned.casefold())


    def requires_canonical_ids(self, vocab_name: str) -> bool:
        spec = self.registry_spec_by_vocab.get(vocab_name, {})
        if spec.get("canonical_ids_only") is True:
            return True
        marker = spec.get("field_should_store")
        return isinstance(marker, str) and "canonical" in marker.casefold()

    def get_term(self, vocab_name: str, canonical_id: str) -> VocabularyTerm | None:
        return self.terms_by_vocab.get(vocab_name, {}).get(canonical_id)


REPOSITORY_POLICY_PATHS: tuple[str, ...] = (
    "schema/instrument_policy.yaml",
    "schema/QC_policy.yaml",
    "schema/maintenance_policy.yaml",
)


def build_repository_vocabulary(repo_root: Path) -> Vocabulary:
    """Build the authoritative repository vocabulary from all sources and policies."""
    repo_root = Path(repo_root).resolve()
    vocab_dir = repo_root / "vocab"
    combined_registry: dict[str, dict[str, Any]] = {
        path.stem: {"source": "file", "path": f"vocab/{path.name}"}
        for path in sorted(vocab_dir.glob("*.yaml"))
    }
    for relative_path in REPOSITORY_POLICY_PATHS:
        policy_path = repo_root / relative_path
        if not policy_path.exists():
            continue
        payload, error = _load_yaml(policy_path, reject_duplicate_keys=True)
        if error is not None or payload is None:
            raise VocabularyDefinitionError(
                f"Failed loading policy '{policy_path.as_posix()}': {error or 'unknown policy load error'}"
            )
        registry = payload.get("vocab_registry")
        if registry is None:
            continue
        if not isinstance(registry, dict):
            raise VocabularyDefinitionError(
                f"Policy '{policy_path.as_posix()}' has non-mapping vocab_registry."
            )
        combined_registry = merge_vocab_registries(combined_registry, registry)
    return Vocabulary(vocab_dir, vocab_registry=combined_registry)
