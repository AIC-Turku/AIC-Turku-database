"""Validation helpers and CLI for dashboard source ledgers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Any, Iterable

import yaml

DEFAULT_ALLOWED_RECORD_TYPES: tuple[str, ...] = ("qc_session", "maintenance_event")
ALLOWED_MAINTENANCE_STATUSES: tuple[str, ...] = ("in_service", "limited", "out_of_service")
INSTRUMENT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
YEAR_PATTERN = re.compile(r"^\d{4}$")
ISO_YEAR_PATTERN = re.compile(r"^(\d{4})-")
FILENAME_DATE_PATTERN = re.compile(r"^(\d{4})-\d{2}-\d{2}(?:_|$)")


@dataclass
class ValidationIssue:
    code: str
    path: str
    message: str


@dataclass
class VocabularyTerm:
    id: str
    label: str
    description: str
    synonyms: list[str]


class Vocabulary:
    """Loads vocab/*.yaml and validates values against canonical IDs/synonyms."""

    def __init__(self, vocab_dir: Path = Path("vocab")) -> None:
        self.vocab_dir = vocab_dir
        self.terms_by_vocab: dict[str, dict[str, VocabularyTerm]] = {}
        self.valid_ids_by_vocab: dict[str, set[str]] = {}
        self.synonyms_by_vocab: dict[str, dict[str, str]] = {}
        self._load_all()

    @staticmethod
    def _normalize(value: str) -> str:
        return value.strip()

    def _load_all(self) -> None:
        for vocab_file in sorted(self.vocab_dir.glob("*.yaml")):
            vocab_name = vocab_file.stem
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


def _iter_yaml_files(base_dir: Path) -> Iterable[Path]:
    if not base_dir.exists() or not base_dir.is_dir():
        return []
    return [p for p in sorted(base_dir.rglob("*")) if p.is_file() and p.suffix.lower() in {".yaml", ".yml"}]


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


def _is_valid_instrument_id(value: str) -> bool:
    return bool(INSTRUMENT_ID_PATTERN.fullmatch(value))


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_numeric_string(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"\d+(?:\.\d+)?", value.strip()))


def _is_positive_number(value: Any) -> bool:
    return _is_number(value) and value > 0


def _is_valid_wavelength(value: Any) -> bool:
    if _is_number(value):
        return value > 0

    if not isinstance(value, str):
        return False

    cleaned = value.strip()
    if not cleaned:
        return False

    if _is_numeric_string(cleaned):
        return float(cleaned) > 0

    return bool(re.fullmatch(r"\d+(?:\.\d+)?/\d+(?:\.\d+)?", cleaned))


def _is_descriptive_wavelength(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not _is_valid_wavelength(value)


def _get_started_year(payload: dict[str, Any], event_file: Path) -> str | None:
    started_utc = payload.get("started_utc")
    if isinstance(started_utc, str):
        started_match = ISO_YEAR_PATTERN.match(started_utc.strip())
        if started_match:
            return started_match.group(1)

    filename_match = FILENAME_DATE_PATTERN.match(event_file.stem)
    if filename_match:
        return filename_match.group(1)

    return None


def validate_instrument_ledgers(
    *,
    instruments_dir: Path = Path("instruments"),
) -> tuple[set[str], list[ValidationIssue], list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    instrument_ids: set[str] = set()
    instrument_id_to_files: dict[str, list[str]] = {}
    vocabulary = Vocabulary()

    def _record(issue: ValidationIssue, *, as_error: bool) -> None:
        if as_error:
            issues.append(issue)
        else:
            warnings.append(issue)

    def _validate_vocab_value(
        *,
        path: str,
        vocab_name: str,
        raw_value: Any,
        required: bool = False,
        allow_empty: bool = False,
    ) -> None:
        if raw_value is None:
            if required:
                _record(
                    ValidationIssue(
                        code="missing_vocab_value",
                        path=path,
                        message=f"Missing required term for '{vocab_name}'.",
                    ),
                    as_error=True,
                )
            return

        if not isinstance(raw_value, str):
            _record(
                ValidationIssue(
                    code="invalid_vocab_value",
                    path=path,
                    message=f"Invalid term for '{vocab_name}'; expected a string.",
                ),
                as_error=True,
            )
            return

        cleaned = raw_value.strip()
        if not cleaned:
            if allow_empty:
                return
            _record(
                ValidationIssue(
                    code="invalid_vocab_value",
                    path=path,
                    message=f"Invalid term for '{vocab_name}'; expected a non-empty string.",
                ),
                as_error=True,
            )
            return

        is_match, suggestion = vocabulary.check(vocab_name, cleaned)
        if is_match:
            return

        if suggestion is None:
            known = ", ".join(sorted(vocabulary.terms_by_vocab.get(vocab_name, {}).keys()))
            _record(
                ValidationIssue(
                    code="unknown_vocab_term",
                    path=path,
                    message=(
                        f"Unknown value '{cleaned}' for vocabulary '{vocab_name}'. "
                        f"Use one of: {known}."
                    ),
                ),
                as_error=True,
            )
            return

        warnings.append(
            ValidationIssue(
                code="vocab_synonym_used",
                path=path,
                message=(
                    f"Value '{cleaned}' is a synonym in '{vocab_name}'. "
                    f"Prefer canonical id '{suggestion}'."
                ),
            )
        )

    for instrument_file in _iter_yaml_files(instruments_dir):
        is_retired_instrument = "retired" in instrument_file.parts

        payload, load_error = _load_yaml(instrument_file)
        if load_error is not None:
            issues.append(
                ValidationIssue(
                    code="yaml_parse_error",
                    path=instrument_file.as_posix(),
                    message=load_error,
                )
            )
            continue

        if payload is None:
            continue

        instrument_section = payload.get("instrument")
        if not isinstance(instrument_section, dict):
            if is_retired_instrument:
                continue
            issues.append(
                ValidationIssue(
                    code="missing_instrument_section",
                    path=instrument_file.as_posix(),
                    message="Missing required top-level mapping key 'instrument'.",
                )
            )
            continue

        instrument_id = instrument_section.get("instrument_id")
        if not isinstance(instrument_id, str) or not instrument_id.strip():
            if is_retired_instrument:
                continue
            issues.append(
                ValidationIssue(
                    code="missing_instrument_id",
                    path=instrument_file.as_posix(),
                    message="Missing required instrument.instrument_id (must be a non-empty string).",
                )
            )
            continue

        instrument_id = instrument_id.strip()
        if not _is_valid_instrument_id(instrument_id):
            if is_retired_instrument:
                continue
            issues.append(
                ValidationIssue(
                    code="invalid_instrument_id",
                    path=instrument_file.as_posix(),
                    message=(
                        "Invalid instrument.instrument_id; expected URL-safe slug "
                        "(lowercase letters, numbers, and single hyphens only)."
                    ),
                )
            )
            continue

        instrument_ids.add(instrument_id)
        instrument_id_to_files.setdefault(instrument_id, []).append(instrument_file.as_posix())

        for field_name in ("display_name", "manufacturer", "model", "stand_orientation"):
            if _is_non_empty_string(instrument_section.get(field_name)):
                continue
            issues.append(
                ValidationIssue(
                    code="missing_instrument_field",
                    path=f"{instrument_file.as_posix()}:instrument.{field_name}",
                    message=f"Missing required instrument field '{field_name}' (must be a non-empty string).",
                )
            )

        modalities = payload.get("modalities")
        if isinstance(modalities, list):
            for index, modality in enumerate(modalities):
                _validate_vocab_value(
                    path=f"{instrument_file.as_posix()}:modalities[{index}]",
                    vocab_name="modalities",
                    raw_value=modality,
                )

        modules = payload.get("modules")
        if isinstance(modules, list):
            for index, module in enumerate(modules):
                module_name = module.get("name") if isinstance(module, dict) else module
                _validate_vocab_value(
                    path=f"{instrument_file.as_posix()}:modules[{index}].name",
                    vocab_name="modules",
                    raw_value=module_name,
                    allow_empty=True,
                )

        hardware = payload.get("hardware") if isinstance(payload.get("hardware"), dict) else {}
        scanner = hardware.get("scanner") if isinstance(hardware.get("scanner"), dict) else {}
        _validate_vocab_value(
            path=f"{instrument_file.as_posix()}:hardware.scanner.type",
            vocab_name="scanner_types",
            raw_value=scanner.get("type"),
            required=True,
        )

        for index, source in enumerate(hardware.get("light_sources", [])):
            if not isinstance(source, dict):
                issues.append(
                    ValidationIssue(
                        code="invalid_light_source_shape",
                        path=f"{instrument_file.as_posix()}:hardware.light_sources[{index}]",
                        message="Each light source must be a mapping/object.",
                    )
                )
                continue

            _validate_vocab_value(
                path=f"{instrument_file.as_posix()}:hardware.light_sources[{index}].kind",
                vocab_name="light_source_kinds",
                raw_value=source.get("kind"),
                required=True,
            )

            wavelength_nm = source.get("wavelength_nm")
            if _is_descriptive_wavelength(wavelength_nm):
                warnings.append(
                    ValidationIssue(
                        code="non_numeric_light_source_wavelength",
                        path=f"{instrument_file.as_posix()}:hardware.light_sources[{index}].wavelength_nm",
                        message=(
                            "wavelength_nm is descriptive and will be displayed as-is; "
                            "use numeric nm or '<center>/<width>' when available."
                        ),
                    )
                )
            elif wavelength_nm not in (None, "") and not _is_valid_wavelength(wavelength_nm):
                issues.append(
                    ValidationIssue(
                        code="invalid_light_source_wavelength",
                        path=f"{instrument_file.as_posix()}:hardware.light_sources[{index}].wavelength_nm",
                        message=(
                            "wavelength_nm must be numeric (or a numeric string) or a numeric band "
                            "formatted as '<center>/<width>'."
                        ),
                    )
                )

        detector_kinds_present: set[str] = set()
        for index, detector in enumerate(hardware.get("detectors", [])):
            if not isinstance(detector, dict):
                issues.append(
                    ValidationIssue(
                        code="invalid_detector_shape",
                        path=f"{instrument_file.as_posix()}:hardware.detectors[{index}]",
                        message="Each detector must be a mapping/object.",
                    )
                )
                continue

            detector_kind = detector.get("kind")
            _validate_vocab_value(
                path=f"{instrument_file.as_posix()}:hardware.detectors[{index}].kind",
                vocab_name="detector_kinds",
                raw_value=detector_kind,
                required=True,
            )
            if isinstance(detector_kind, str) and detector_kind.strip():
                detector_kinds_present.add(detector_kind.strip().casefold())

        seen_objective_ids: set[str] = set()
        for index, objective in enumerate(hardware.get("objectives", [])):
            if not isinstance(objective, dict):
                issues.append(
                    ValidationIssue(
                        code="invalid_objective_shape",
                        path=f"{instrument_file.as_posix()}:hardware.objectives[{index}]",
                        message="Each objective must be a mapping/object.",
                    )
                )
                continue

            obj_id = objective.get("id")
            if not _is_non_empty_string(obj_id):
                issues.append(
                    ValidationIssue(
                        code="missing_objective_id",
                        path=f"{instrument_file.as_posix()}:hardware.objectives[{index}].id",
                        message="Objective id is required.",
                    )
                )
            else:
                normalized_id = obj_id.strip()
                if normalized_id in seen_objective_ids:
                    issues.append(
                        ValidationIssue(
                            code="duplicate_objective_id",
                            path=f"{instrument_file.as_posix()}:hardware.objectives[{index}].id",
                            message=f"Duplicate objective id '{normalized_id}' within instrument.",
                        )
                    )
                else:
                    seen_objective_ids.add(normalized_id)

            na = objective.get("numerical_aperture")
            if na in (None, ""):
                warnings.append(
                    ValidationIssue(
                        code="missing_numerical_aperture",
                        path=f"{instrument_file.as_posix()}:hardware.objectives[{index}].numerical_aperture",
                        message="NA is missing; value will be displayed as-is and highlighted in audit output.",
                    )
                )
            elif _is_number(na):
                if not (0 < na <= 1.7):
                    issues.append(
                        ValidationIssue(
                            code="invalid_numerical_aperture",
                            path=f"{instrument_file.as_posix()}:hardware.objectives[{index}].numerical_aperture",
                            message="NA must be numeric and between 0 and 1.7.",
                        )
                    )
            elif _is_numeric_string(na):
                na_value = float(na.strip())
                if not (0 < na_value <= 1.7):
                    issues.append(
                        ValidationIssue(
                            code="invalid_numerical_aperture",
                            path=f"{instrument_file.as_posix()}:hardware.objectives[{index}].numerical_aperture",
                            message="NA must be numeric and between 0 and 1.7.",
                        )
                    )
            else:
                warnings.append(
                    ValidationIssue(
                        code="non_numeric_numerical_aperture",
                        path=f"{instrument_file.as_posix()}:hardware.objectives[{index}].numerical_aperture",
                        message="NA is descriptive and will be displayed as-is; provide numeric value when known.",
                    )
                )

            magnification = objective.get("magnification")
            if magnification is not None and not _is_positive_number(magnification):
                issues.append(
                    ValidationIssue(
                        code="invalid_objective_magnification",
                        path=f"{instrument_file.as_posix()}:hardware.objectives[{index}].magnification",
                        message="Objective magnification must be numeric and greater than 0.",
                    )
                )

            _validate_vocab_value(
                path=f"{instrument_file.as_posix()}:hardware.objectives[{index}].immersion",
                vocab_name="objective_immersion",
                raw_value=objective.get("immersion"),
                allow_empty=True,
            )
            _validate_vocab_value(
                path=f"{instrument_file.as_posix()}:hardware.objectives[{index}].correction",
                vocab_name="objective_corrections",
                raw_value=objective.get("correction"),
                allow_empty=True,
            )

        modality_ids = {value.strip() for value in modalities if isinstance(value, str) and value.strip()} if isinstance(modalities, list) else set()
        module_ids = {
            module.get("name").strip()
            for module in modules
            if isinstance(modules, list) and isinstance(module, dict) and _is_non_empty_string(module.get("name"))
        }

        scanner_type = scanner.get("type") if isinstance(scanner.get("type"), str) else None
        if "confocal_point" in modality_ids and scanner_type == "none":
            warnings.append(
                ValidationIssue(
                    code="modality_scanner_mismatch",
                    path=f"{instrument_file.as_posix()}:hardware.scanner.type",
                    message="'confocal_point' modality usually requires a non-'none' scanner type.",
                )
            )

        if "tirf" in modality_ids and not ({"ring_tirf", "tirf"} & {m.casefold() for m in module_ids}):
            warnings.append(
                ValidationIssue(
                    code="tirf_module_missing",
                    path=f"{instrument_file.as_posix()}:modules",
                    message="'tirf' modality should usually declare a dedicated TIRF illumination module/path.",
                )
            )

        flim_detector_kinds = {"apd", "spad", "hyd", "pmt", "gaasp_pmt"}
        if "flim" in modality_ids and "flim" not in {m.casefold() for m in module_ids} and not (detector_kinds_present & flim_detector_kinds):
            warnings.append(
                ValidationIssue(
                    code="flim_chain_incomplete",
                    path=f"{instrument_file.as_posix()}:modalities",
                    message=(
                        "'flim' modality should usually declare a FLIM module or FLIM-capable detector chain "
                        "(e.g., APD/SPAD/HyD/PMT)."
                    ),
                )
            )

    for instrument_id, source_files in sorted(instrument_id_to_files.items()):
        if len(source_files) <= 1:
            continue
        source_list = ", ".join(sorted(source_files))
        issues.append(
            ValidationIssue(
                code="duplicate_instrument_id",
                path=instrument_id,
                message=f"Duplicate instrument.instrument_id '{instrument_id}' defined in: {source_list}.",
            )
        )

    return instrument_ids, issues, warnings

def validate_event_ledgers(
    *,
    instrument_ids: set[str],
    qc_base_dir: Path = Path("qc/sessions"),
    maintenance_base_dir: Path = Path("maintenance/events"),
    allowed_record_types: Iterable[str] = DEFAULT_ALLOWED_RECORD_TYPES,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    event_output_to_sources: dict[str, list[str]] = {}
    allowed_types = {value.strip() for value in allowed_record_types if isinstance(value, str) and value.strip()}
    allowed_maintenance_statuses = set(ALLOWED_MAINTENANCE_STATUSES)

    event_sources = [
        (qc_base_dir, "qc_session"),
        (maintenance_base_dir, "maintenance_event"),
    ]

    for base_dir, expected_type in event_sources:
        for event_file in _iter_yaml_files(base_dir):
            try:
                rel_parts = event_file.relative_to(base_dir).parts
            except ValueError:
                rel_parts = ()

            payload, load_error = _load_yaml(event_file)
            if load_error is not None:
                issues.append(
                    ValidationIssue(
                        code="yaml_parse_error",
                        path=event_file.as_posix(),
                        message=load_error,
                    )
                )
                continue

            if payload is None:
                continue

            microscope = payload.get("microscope")
            if not isinstance(microscope, str) or not microscope.strip():
                issues.append(
                    ValidationIssue(
                        code="missing_microscope",
                        path=event_file.as_posix(),
                        message="Missing required 'microscope' field.",
                    )
                )
                continue

            if microscope not in instrument_ids:
                known = ", ".join(sorted(instrument_ids))
                issues.append(
                    ValidationIssue(
                        code="unknown_microscope",
                        path=event_file.as_posix(),
                        message=(
                            f"Unknown microscope '{microscope}'. "
                            f"Expected one of instrument IDs in registry: {known}."
                        ),
                    )
                )

            if len(rel_parts) < 3:
                issues.append(
                    ValidationIssue(
                        code="invalid_event_path_structure",
                        path=event_file.as_posix(),
                        message=(
                            f"Expected event path under '{base_dir.as_posix()}' to follow "
                            "'<microscope>/<YYYY>/<file>.yaml'."
                        ),
                    )
                )
            else:
                path_microscope = rel_parts[0]
                path_year = rel_parts[1]

                if microscope != path_microscope:
                    issues.append(
                        ValidationIssue(
                            code="microscope_mismatch_with_path",
                            path=event_file.as_posix(),
                            message=(
                                f"Path microscope '{path_microscope}' does not match payload "
                                f"microscope '{microscope}'."
                            ),
                        )
                    )

                if not YEAR_PATTERN.fullmatch(path_year):
                    issues.append(
                        ValidationIssue(
                            code="invalid_event_year_folder",
                            path=event_file.as_posix(),
                            message=(
                                f"Invalid year folder '{path_year}'. Expected a 4-digit year "
                                "like '2026'."
                            ),
                        )
                    )
                else:
                    event_year = _get_started_year(payload, event_file)
                    if event_year is None:
                        issues.append(
                            ValidationIssue(
                                code="missing_event_year_source",
                                path=event_file.as_posix(),
                                message=(
                                    "Could not derive event year from payload.started_utc or "
                                    "filename date prefix (YYYY-MM-DD_...)."
                                ),
                            )
                        )
                    elif path_year != event_year:
                        issues.append(
                            ValidationIssue(
                                code="year_mismatch_with_path",
                                path=event_file.as_posix(),
                                message=(
                                    f"Path year '{path_year}' does not match derived event "
                                    f"year '{event_year}' from started_utc/filename."
                                ),
                            )
                        )

            record_type = payload.get("record_type")
            if not isinstance(record_type, str) or not record_type.strip():
                issues.append(
                    ValidationIssue(
                        code="missing_record_type",
                        path=event_file.as_posix(),
                        message="Missing required 'record_type' field.",
                    )
                )
            elif record_type not in allowed_types:
                allowed = ", ".join(sorted(allowed_types))
                issues.append(
                    ValidationIssue(
                        code="invalid_record_type",
                        path=event_file.as_posix(),
                        message=f"Invalid record_type '{record_type}'. Allowed values: {allowed}.",
                    )
                )
            elif record_type != expected_type:
                issues.append(
                    ValidationIssue(
                        code="unexpected_record_type_for_location",
                        path=event_file.as_posix(),
                        message=(
                            f"record_type '{record_type}' does not match expected value "
                            f"'{expected_type}' for files under '{base_dir.as_posix()}'."
                        ),
                    )
                )

            if record_type == "maintenance_event":
                required_maintenance_fields = (
                    "started_utc",
                    "service_provider",
                    "reason_details",
                    "action",
                )
                for field_name in required_maintenance_fields:
                    if _is_non_empty_string(payload.get(field_name)):
                        continue
                    issues.append(
                        ValidationIssue(
                            code="missing_maintenance_field",
                            path=event_file.as_posix(),
                            message=(
                                f"Missing required maintenance field '{field_name}' "
                                "(must be a non-empty string)."
                            ),
                        )
                    )

                has_maintenance_id = _is_non_empty_string(payload.get("maintenance_id"))
                has_event_id = _is_non_empty_string(payload.get("event_id"))
                if has_maintenance_id == has_event_id:
                    issues.append(
                        ValidationIssue(
                            code="invalid_maintenance_id_shape",
                            path=event_file.as_posix(),
                            message=(
                                "Maintenance events must include exactly one ID field: "
                                "either 'maintenance_id' or 'event_id'."
                            ),
                        )
                    )

                for status_key in ("microscope_status_before", "microscope_status_after"):
                    raw_status = payload.get(status_key)
                    if raw_status is None:
                        continue
                    if not _is_non_empty_string(raw_status):
                        issues.append(
                            ValidationIssue(
                                code="invalid_maintenance_status",
                                path=event_file.as_posix(),
                                message=(
                                    f"Invalid {status_key}: expected one of "
                                    f"{', '.join(ALLOWED_MAINTENANCE_STATUSES)}."
                                ),
                            )
                        )
                        continue

                    if raw_status.strip() not in allowed_maintenance_statuses:
                        issues.append(
                            ValidationIssue(
                                code="invalid_maintenance_status",
                                path=event_file.as_posix(),
                                message=(
                                    f"Invalid {status_key} '{raw_status}'. "
                                    "Use normalized lowercase values from: "
                                    f"{', '.join(ALLOWED_MAINTENANCE_STATUSES)}."
                                ),
                            )
                        )

            output_rel_path = f"events/{microscope}/{event_file.stem}.md"
            event_output_to_sources.setdefault(output_rel_path, []).append(event_file.as_posix())

    for output_rel_path, source_files in sorted(event_output_to_sources.items()):
        if len(source_files) <= 1:
            continue
        source_list = ", ".join(sorted(source_files))
        issues.append(
            ValidationIssue(
                code="duplicate_event_output_path",
                path=output_rel_path,
                message=f"Duplicate generated event path '{output_rel_path}' from: {source_list}.",
            )
        )

    return issues


def print_validation_report(issues: list[ValidationIssue], *, report_name: str = "failures") -> None:
    if not issues:
        return

    print(f"\nValidation {report_name} detected:", file=sys.stderr)
    for index, issue in enumerate(issues, start=1):
        print(f"  {index}. [{issue.code}] {issue.path}", file=sys.stderr)
        print(f"     {issue.message}", file=sys.stderr)
    print(f"\nTotal validation {report_name}: {len(issues)}", file=sys.stderr)


def main() -> int:
    instrument_ids, issues, warnings = validate_instrument_ledgers()
    issues.extend(validate_event_ledgers(instrument_ids=instrument_ids))

    if warnings:
        print_validation_report(warnings, report_name="warnings")

    if issues:
        print_validation_report(issues)
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
