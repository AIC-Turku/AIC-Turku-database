"""Optical-path dashboard view DTOs.

This module owns the optical-path view projection derived from canonical
light-path DTOs.

It must not import scripts.dashboard_builder.
It also should not import scripts.dashboard.instrument_view, because
instrument_view imports this module.
"""

from __future__ import annotations

import copy
import json
import re
from typing import Any

from scripts.build_context import clean_text
from scripts.display_labels import (
    resolve_component_type_label,
    resolve_element_type_label,
    resolve_endpoint_type_label,
    resolve_inventory_class_label,
    resolve_light_source_kind_label,
    resolve_stage_role_label,
)
from scripts.validate import Vocabulary


_MAX_READOUT_ACRONYM_LENGTH = 5
"""Readout IDs with ≤ this many non-space characters are rendered as UPPERCASE acronyms."""


def _readout_vocab_label(readout_id: str, vocabulary: Vocabulary | None) -> str:
    """Return a display label for a measurement readout vocabulary term.

    Uses the vocabulary when available; falls back to a human-readable
    derivation of the ID so the UI never shows a raw machine identifier.
    """
    if not readout_id:
        return ""
    if vocabulary:
        term = vocabulary.terms_by_vocab.get("measurement_readouts", {}).get(readout_id)
        if term is not None:
            label = getattr(term, "label", None)
            if label:
                return label
    # Fallback: short uppercase acronyms (≤ _MAX_READOUT_ACRONYM_LENGTH non-space chars) else title-case
    slug = readout_id.replace("_", " ")
    return slug.upper() if len(slug.replace(" ", "")) <= _MAX_READOUT_ACRONYM_LENGTH else slug.title()


def _route_type_vocab_label(route_type_id: str, vocabulary: Vocabulary | None) -> str:
    """Return a human-readable label for an optical route type / illumination mode.

    Resolves against ``imaging_modes`` and ``contrast_methods`` vocab (both
    share IDs with optical route types) so the template never shows a raw
    snake_case identifier for the route type field.
    """
    if not route_type_id:
        return ""
    if vocabulary:
        for vocab_name in ("imaging_modes", "contrast_methods", "optical_routes"):
            term = vocabulary.terms_by_vocab.get(vocab_name, {}).get(route_type_id)
            if term is not None:
                label = getattr(term, "label", None) or getattr(term, "display_label", None)
                if label:
                    return label
    # Fallback: title-case the slug
    return route_type_id.replace("_", " ").title()


def _method_publication_phrase(method_id: str, vocabulary: Vocabulary | None) -> str:
    """Return the noun phrase a Methods sentence uses for a method.

    A vocabulary `label` is a picker label: "Confocal point scanning" reads as a
    column heading, and the generic "<label> imaging" frame turns it into
    "Confocal point scanning imaging". `publication_phrase` is the authored
    sentence form, and is also where an acronym gets expanded on first use.
    """
    if not method_id or not vocabulary:
        return ""
    for vocab_name in ("imaging_modes", "contrast_methods"):
        term = vocabulary.terms_by_vocab.get(vocab_name, {}).get(method_id)
        if term is not None and isinstance(getattr(term, "metadata", None), dict):
            phrase = term.metadata.get("publication_phrase")
            if isinstance(phrase, str) and phrase.strip():
                return phrase.strip()
    return ""


def _method_required_source_role(method_id: str, vocabulary: Vocabulary | None) -> str:
    """The source role a technique cannot be performed without, as authored.

    `vocab/imaging_modes.yaml` records that STED and RESOLFT both need a beam
    whose role is `depletion`. The Methods page needs that in both directions - a
    technique reported without its beam, and a beam reported without a technique
    that uses it - and a table of it in browser JavaScript is a second copy of the
    vocabulary. It had also drifted from it: the table required a depletion source
    for STED and not for RESOLFT, which use the same beam.
    """
    if not method_id or not vocabulary:
        return ""
    for vocab_name in ("imaging_modes", "contrast_methods"):
        term = vocabulary.terms_by_vocab.get(vocab_name, {}).get(method_id)
        if term is None:
            continue
        role = term.tag_value("requires_source_role")
        if isinstance(role, str) and role.strip():
            return role.strip()
    return ""


def _role_forms_imaging_channel(role_id: str, vocabulary: Vocabulary | None) -> bool:
    """Whether a source in this role produces an image channel.

    A depletion, activation or alignment beam does not, so an acquisition using
    one is not asked in what order its channels were acquired. Roles say this
    about themselves in `vocab/light_source_roles.yaml`; a role that says nothing
    forms a channel, which is what every illumination role does.
    """
    if not role_id or not vocabulary:
        return True
    term = vocabulary.terms_by_vocab.get("light_source_roles", {}).get(role_id)
    if term is None:
        return True
    return term.tag_value("forms_imaging_channel", True) is not False


def _human_list(items: list[str]) -> str:
    cleaned = [clean_text(item) for item in items if clean_text(item)]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])}, and {cleaned[-1]}"


def _spec_lines(*pairs: tuple[str, Any]) -> list[str]:
    lines: list[str] = []
    for label, raw_value in pairs:
        if raw_value in (None, "", [], {}):
            continue
        lines.append(f"**{label}:** {raw_value}")
    return lines


def _format_position_value(pos: dict[str, Any], vocabulary: Any = None) -> str:
    """Format a single optical path element position into a compact display string."""
    name = clean_text(pos.get("name") or pos.get("display_label") or pos.get("label"))
    if not name:
        raw_component_type = clean_text(pos.get("component_type"))
        if raw_component_type and vocabulary:
            name = resolve_component_type_label(raw_component_type, vocabulary)
        elif raw_component_type:
            name = raw_component_type.replace("_", " ").title()
    product_code = clean_text(pos.get("product_code"))
    if not name and product_code:
        name = product_code
        product_code = ""
    if not name:
        return ""
    bands = pos.get("bands")
    notes = clean_text(pos.get("notes"))
    parts: list[str] = [name]
    if product_code:
        parts.append(f"({product_code})")
    if isinstance(bands, list) and bands:
        band_strs = []
        for band in bands:
            if isinstance(band, dict):
                center = band.get("center_nm")
                width = band.get("width_nm")
                if center is not None and width is not None:
                    band_strs.append(f"{center}/{width} nm")
                elif center is not None:
                    band_strs.append(f"{center} nm")
        if band_strs:
            parts.append(f"— emission {', '.join(band_strs)}")
    if notes:
        parts.append(f"— {notes}")
    return " ".join(parts)


def _optical_element_position_pairs(element: dict[str, Any], vocabulary: Any = None) -> list[tuple[str, str]]:
    """Return (label, value) pairs for each named position of an optical path element."""
    positions = element.get("positions")
    pairs: list[tuple[str, str]] = []
    if isinstance(positions, dict):
        for key in sorted(positions):
            pos = positions[key]
            if not isinstance(pos, dict):
                continue
            value = _format_position_value(pos, vocabulary)
            if value:
                label = key.replace("_", " ").title()
                pairs.append((label, value))
    elif isinstance(positions, list):
        for i, pos in enumerate(positions):
            if not isinstance(pos, dict):
                continue
            value = _format_position_value(pos, vocabulary)
            if value:
                pairs.append((f"Pos {i + 1}", value))
    return pairs


# A recorded manufacturer/model that only restates that the value is unknown is not
# an identity. Publication prose must not present it as one; the QUAREP clause
# reports it as missing instead.
_PLACEHOLDER_IDENTITY_VALUES = {"unknown", "unknown manufacturer", "placeholder", "n/a", "na", "none", "-", "--", "?"}

# Publication sentence per recorded light-source role. A source whose role is not
# recorded must not be described as an excitation source: the neutral sentence is
# paired with an explicit review request instead of an inferred role.
_SOURCE_ROLE_SENTENCES = {
    "excitation": "Excitation was provided by {label}.",
    # The recorded role says the beam depletes; it does not say by which mechanism,
    # and the mechanism belongs to the method rather than to the hardware. The same
    # 775 nm beam depletes by stimulated emission under STED and drives reversible
    # photoswitching under RESOLFT, and the Abberior record declares both. Naming
    # stimulated emission here made every RESOLFT draft from that record wrong, so
    # the sentence states the role and the opening sentence names the technique.
    "depletion": "Depletion was provided by {label}.",
    "transmitted_illumination": "Transmitted-light illumination was provided by {label}.",
    "reflected_illumination": "Reflected-light illumination was provided by {label}.",
    "activation": "Photoactivation was performed using {label}.",
    "alignment": "Alignment illumination was provided by {label}.",
}
_SOURCE_ROLE_UNRECORDED_SENTENCE = "Illumination was provided by {label}."

_ENDPOINT_SENTENCE = "Images were recorded using {label}."
_EYEPIECE_SENTENCE = "Samples were observed through {label}."
_SPLITTER_SENTENCE = "Light was directed through {label}."
_OPTICAL_ELEMENT_SENTENCE = "The light path included {label}."
_SOURCE_ROLE_UNRECORDED_PROMPT = (
    "[PLEASE SPECIFY: the role of {label} in this acquisition, for example excitation, "
    "transmitted illumination, or depletion; it is not recorded for this source]"
)


# A component whose identity is unresolved must not be named in publication prose.
# The Methods draft asks for the identity instead, per class, so the request names
# the thing the author has to look up rather than the field the record is missing.
_UNRESOLVED_IDENTITY_PROMPTS = {
    "endpoint": (
        "[PLEASE SPECIFY: the detector or camera used for this acquisition "
        "(manufacturer and model); the facility record does not identify it]"
    ),
    "camera_port": (
        "[PLEASE SPECIFY: the camera used for this acquisition (manufacturer and "
        "model); the facility record does not identify it]"
    ),
    "light_source": (
        "[PLEASE SPECIFY: the illumination source used for this acquisition "
        "(manufacturer and model); the facility record does not identify it]"
    ),
    "optical_element": (
        "[PLEASE SPECIFY: the optical element used for this acquisition "
        "(manufacturer and model/catalogue number); the facility record does not "
        "identify it]"
    ),
    "splitter": (
        "[PLEASE SPECIFY: the beam splitter used for this acquisition "
        "(manufacturer and model); the facility record does not identify it]"
    ),
}
_UNRESOLVED_IDENTITY_FALLBACK_PROMPT = (
    "[PLEASE SPECIFY: the identity of one selected component (manufacturer and "
    "model); the facility record does not identify it]"
)
# Classes where the manufacturer alone is not an identity. "Zeiss" names a vendor,
# not the photomultiplier a reader would have to look up, so it is refused here
# rather than printed as though it were the detector.
_MODEL_REQUIRED_CLASSES = {"endpoint", "camera_port"}


def _identity_value(value: Any) -> str:
    """Return an identity string, or "" when the value only marks it unresolved."""
    cleaned = clean_text(value)
    lowered = cleaned.lower()
    if lowered in _PLACEHOLDER_IDENTITY_VALUES:
        return ""
    if lowered.startswith("unknown ") or lowered.startswith("placeholder"):
        return ""
    return cleaned


def _authored_label_value(value: Any) -> str:
    """Return an authored display label, or "" when it only restates "unknown".

    ``display_label`` is the last fallback for a publication label. When the record
    authored it as ``Unknown Camera`` that fallback publishes the placeholder the
    identity check just removed, so the same test is applied to it.
    """
    return _identity_value(value)


def _unresolved_identity_prompt(inventory_class: str) -> str:
    return _UNRESOLVED_IDENTITY_PROMPTS.get(
        clean_text(inventory_class), _UNRESOLVED_IDENTITY_FALLBACK_PROMPT
    )


def _number_text(value: Any) -> str:
    """Render a recorded number without a trailing ``.0``; "" when not numeric."""
    if isinstance(value, bool) or value in (None, ""):
        return ""
    if isinstance(value, (int, float)):
        return str(int(value)) if float(value).is_integer() else str(value)
    cleaned = clean_text(value)
    try:
        numeric = float(cleaned)
    except (TypeError, ValueError):
        return ""
    return str(int(numeric)) if numeric.is_integer() else str(numeric)


def _kind_phrase(kind_label: str) -> str:
    """Lower-case a vocabulary kind label for mid-sentence use, keeping acronyms."""
    if not kind_label:
        return ""
    return " ".join(
        word if word.isupper() else word.lower()
        for word in kind_label.split()
    )


def _strip_leading_wavelength(model: str, wavelength: str) -> str:
    """Drop a wavelength the label already states, keeping the rest of the model.

    ``405 nm (Diode)`` becomes ``Diode`` so the rendered label reads
    ``405 nm laser (Diode)`` instead of repeating the line twice.
    """
    if not model or not wavelength:
        return model
    trimmed = re.sub(rf"^\s*{re.escape(wavelength)}\s*nm\b", "", model, flags=re.IGNORECASE).strip()
    trimmed = trimmed.strip(" -–—")
    if trimmed.startswith("(") and trimmed.endswith(")"):
        trimmed = trimmed[1:-1].strip()
    return trimmed


def _publication_inventory_label(item: dict[str, Any], vocabulary: Vocabulary | None) -> str:
    """Build a manuscript-safe label for an inventory card.

    The canonical ``display_label`` concatenates the raw vocabulary ``kind`` id
    (``halogen_lamp``, ``white_light_laser``) because the light-path layer has no
    vocabulary. This view resolves the term and drops placeholder identities, so
    publication prose never carries an internal id or the word "Unknown".
    """
    inventory_class = clean_text(item.get("inventory_class"))
    manufacturer = _identity_value(item.get("manufacturer"))
    model = _identity_value(item.get("model"))
    authored = clean_text(item.get("display_label"))

    if inventory_class == "light_source":
        source_meta = item.get("source_metadata") if isinstance(item.get("source_metadata"), dict) else {}
        wavelength = _number_text(source_meta.get("wavelength_nm"))
        kind_phrase = _kind_phrase(resolve_light_source_kind_label(clean_text(source_meta.get("kind")), vocabulary))
        core = " ".join(part for part in (f"{wavelength} nm" if wavelength else "", kind_phrase) if part).strip()
        identity = " ".join(
            part for part in (manufacturer, _strip_leading_wavelength(model, wavelength)) if part
        ).strip()
        if core and identity:
            return f"{core} ({identity})"
        # A wavelength and kind ("488 nm laser") identify a line well enough to
        # publish even with no vendor recorded. Only when neither is recorded does
        # the label fall back, and then never onto a placeholder.
        return core or identity or _authored_label_value(authored)

    identity = " ".join(part for part in (manufacturer, model) if part).strip()
    fallback = _authored_label_value(authored)
    if clean_text(inventory_class) in _MODEL_REQUIRED_CLASSES and not model:
        identity = ""
        # An authored label that only restates the vendor is the same non-identity
        # the model check just rejected.
        if fallback.lower() == manufacturer.lower():
            fallback = ""
    return identity or fallback


def _inventory_method_facts(
    item: dict[str, Any],
    label: str,
) -> tuple[str, str, list[str]]:
    """Publication sentence and review requests for a selected inventory card.

    Every sentence describes only what selecting the card asserts: that this
    component was in the path the user used. Nothing about its function is
    inferred - a light source is described by its recorded ``role`` or not at all.

    Review requests are returned separately from the sentence so the instrument
    page can render the prose alone while the Methods draft collects the requests
    into its review block.

    Returns ``(sentence_template, sentence, review_prompts)``. The template keeps
    ``{label}`` unfilled so the Methods draft can merge several components that
    share it into one sentence instead of repeating the frame per checkbox.
    """
    inventory_class = clean_text(item.get("inventory_class"))
    if not label:
        # The component stays selectable - the user did use it - but it cannot be
        # named, so the draft asks who it is instead of publishing a placeholder or
        # dropping the fact silently.
        return "", "", [_unresolved_identity_prompt(inventory_class)]

    template = ""
    prompts: list[str] = []
    if inventory_class == "light_source":
        source_meta = item.get("source_metadata") if isinstance(item.get("source_metadata"), dict) else {}
        role = clean_text(source_meta.get("role") or item.get("role")).lower()
        template = _SOURCE_ROLE_SENTENCES.get(role, "")
        if not template:
            template = _SOURCE_ROLE_UNRECORDED_SENTENCE
            prompts = [_SOURCE_ROLE_UNRECORDED_PROMPT.format(label=label)]
        tunable_min = _number_text(source_meta.get("tunable_min_nm"))
        tunable_max = _number_text(source_meta.get("tunable_max_nm"))
        if tunable_min and tunable_max:
            prompts.append(
                f"[PLEASE SPECIFY: wavelength used from the recorded {tunable_min}-{tunable_max} nm tunable range of {label}]"
            )
    elif inventory_class in {"endpoint", "camera_port", "eyepiece"}:
        endpoint_meta = item.get("endpoint_metadata") if isinstance(item.get("endpoint_metadata"), dict) else {}
        endpoint_type = clean_text(endpoint_meta.get("endpoint_type") or endpoint_meta.get("kind"))
        template = (
            _EYEPIECE_SENTENCE
            if inventory_class == "eyepiece" or endpoint_type == "eyepiece"
            else _ENDPOINT_SENTENCE
        )
    elif inventory_class == "splitter":
        template = _SPLITTER_SENTENCE
    elif inventory_class == "optical_element":
        template = _OPTICAL_ELEMENT_SENTENCE

    if not template:
        return "", "", []
    return template, template.format(label=label), prompts


_EMPTY_POSITION_WORDS = {"empty", "none", "blank", "open", "free"}

# How a filter position is described in prose. The recorded ``component_type`` is a
# schema term; these are the words a Methods section uses for the same thing.
_POSITION_TYPE_NOUNS = {
    "bandpass": "bandpass filter",
    "multiband_bandpass": "multi-bandpass filter",
    "longpass": "longpass filter",
    "shortpass": "shortpass filter",
    "dichroic": "dichroic mirror",
    "multiband_dichroic": "multi-band dichroic mirror",
    "filter_cube": "filter cube",
    "neutral_density": "neutral-density filter",
    "analyzer": "analyser",
    "polarizer": "polariser",
    "beamsplitter": "beam splitter",
}
# Where the position sits in the path, when the recorded stage role says so. Used
# to write "excitation filter" rather than the bare type noun.
_POSITION_STAGE_ADJECTIVES = {
    "excitation": "excitation",
    "emission": "emission",
    "dichroic": "",
    "cube": "",
}


def _looks_like_internal_id(value: str) -> str:
    """True when a label is a slot identifier rather than a name a reader knows.

    ``EMP_BF`` and ``Pos_1`` identify a position in the record; printing them in a
    Methods section tells a reader nothing and exposes the repository's own keys.
    """
    cleaned = clean_text(value)
    if not cleaned or " " in cleaned:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9]+(?:[_\-][A-Za-z0-9]+)+", cleaned))


# Words that already say what kind of optic a component is. When the recorded name
# carries one, restating the type noun produces "Quad-band Dichroic multi-band
# dichroic mirror".
# A name carrying one of these already says what kind of optic it is, so the whole
# type noun is dropped: "Quad-band Dichroic", not "Quad-band Dichroic multi-band
# dichroic mirror".
_OPTIC_HEAD_WORDS = {
    "filter", "filters", "cube", "cubes", "dichroic", "dichroics", "mirror",
    "emitter", "splitter", "beamsplitter", "analyser", "analyzer", "polariser",
    "polarizer",
}
# These only qualify the optic, so a name carrying one drops that word from the type
# noun and keeps the head: "GFP Emission bandpass filter", not "GFP Emission
# emission bandpass filter".
_OPTIC_QUALIFIER_WORDS = {
    "emission", "excitation", "bandpass", "longpass", "shortpass", "multiband",
    "multi-band", "neutral-density", "nd",
}
# First letters whose spoken acronym starts with a vowel sound, so "an LED" but
# "a UV lamp".
_ACRONYM_VOWEL_LETTERS = set("AEFHILMNORSX")
_DIGIT_ARTICLES = {"8": "an"}


def _indefinite_article(text: str) -> str:
    """Return "a" or "an" for a generated label, by how the label is read aloud."""
    cleaned = clean_text(text)
    if not cleaned:
        return "a"
    first_word = cleaned.split()[0]
    first = first_word[0]
    if first.isdigit():
        if first_word[:2] in {"11", "18"}:
            return "an"
        return _DIGIT_ARTICLES.get(first, "a")
    # An acronym is spelled out, so the article follows the letter name, not the word.
    if first_word.isupper() and len(first_word) > 1:
        return "an" if first in _ACRONYM_VOWEL_LETTERS else "a"
    return "an" if first.lower() in set("aeiou") else "a"


def _publication_position_phrase(row: dict[str, Any]) -> str:
    """Name a filter position the way a Methods section names it.

    A catalogue number identifies the part but not what it does, and the position
    name alone ("387/11", "GFP") is a facility shorthand. This states the optic,
    what it passes when that is recorded, and the catalogue number - nothing that
    is not in the record.
    """
    name = clean_text(row.get("display_label")) if row.get("has_identity") else ""
    # "NIR dichroic position" names a slot; the trailing word is an authoring
    # artefact, not part of the component's name.
    name = re.sub(r"\s+(position|slot)$", "", name, flags=re.IGNORECASE).strip()
    spec = clean_text(row.get("spec_phrase"))
    noun = clean_text(row.get("type_noun"))
    code = clean_text(row.get("product_code"))
    manufacturer = clean_text(row.get("manufacturer"))

    # "Quad-band Dichroic multi-band dichroic mirror" repeats itself. The type noun
    # is dropped when the recorded name already carries its head word.
    if noun and name:
        name_words = {word.strip("()/,").lower() for word in name.split()}
        if name_words & _OPTIC_HEAD_WORDS:
            noun = ""
        elif name_words & _OPTIC_QUALIFIER_WORDS:
            noun = " ".join(word for word in noun.split() if word.lower() not in name_words)

    if name and spec and name.lower() in spec.lower():
        core = " ".join(part for part in (spec, noun) if part)
        parenthetical = ""
    else:
        core = " ".join(part for part in (name, noun) if part) or spec
        parenthetical = spec if spec and spec != core else ""

    if not core:
        return ""
    details = [detail for detail in (parenthetical, manufacturer, f"cat. no. {code}" if code else "") if detail]
    phrase = f"{core} ({'; '.join(details)})" if details else core
    return f"{_indefinite_article(phrase)} {phrase}"


def _band_text(band: Any) -> str:
    """Render one recorded transmission band as ``525/25`` or ``525``."""
    if not isinstance(band, dict):
        return ""
    center = _number_text(band.get("center_nm"))
    width = _number_text(band.get("width_nm"))
    if not center:
        return ""
    return f"{center}/{width}" if width else center


def _bands_text(bands: Any) -> str:
    rendered = [text for text in (_band_text(band) for band in (bands or [])) if text]
    return ", ".join(rendered)


def _position_spec_phrase(position: dict[str, Any]) -> str:
    """Summarise a filter position's recorded transmission in publication wording.

    A catalogue number identifies a part; it does not tell a reader what the filter
    passes. The spectral model the repository already derives for the virtual
    microscope carries that, so it is summarised here rather than left out of the
    Methods draft. Nothing is inferred: a position whose bands are not recorded
    produces no phrase, and the existing incompleteness prompt asks for them.
    """
    spectral_ops = position.get("spectral_ops") if isinstance(position.get("spectral_ops"), dict) else {}
    operations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for phase in ("illumination", "detection"):
        for operation in spectral_ops.get(phase) or []:
            if not isinstance(operation, dict):
                continue
            key = json.dumps(operation, sort_keys=True, default=str)
            if key in seen:
                continue
            seen.add(key)
            operations.append(operation)

    component_type = clean_text(position.get("component_type")).lower()

    if component_type == "filter_cube":
        # A cube is three parts; naming them separately is what makes the draft
        # usable, because a reader checks excitation against emission.
        parts: list[str] = []
        for sub_role, prefix, suffix in (
            ("excitation_filter", "excitation", ""),
            ("dichroic", "", "dichroic"),
            ("emission_filter", "emission", ""),
        ):
            for operation in operations:
                if clean_text(operation.get("sub_role")) != sub_role:
                    continue
                text = _operation_band_text(operation)
                if not text:
                    continue
                parts.append(" ".join(part for part in (prefix, text, suffix) if part))
                break
        return ", ".join(parts)

    for operation in operations:
        text = _operation_band_text(operation)
        if text:
            return text
    return ""


def _operation_band_text(operation: dict[str, Any]) -> str:
    """Render one spectral operation as a transmission phrase, or "" when unrecorded."""
    op = clean_text(operation.get("op")).lower()
    if op in {"bandpass", "multiband_bandpass"}:
        bands = operation.get("bands")
        if bands:
            rendered = _bands_text(bands)
            return f"{rendered} nm" if rendered else ""
        center = _number_text(operation.get("center_nm"))
        width = _number_text(operation.get("width_nm"))
        if center and width:
            return f"{center}/{width} nm"
        return f"{center} nm" if center else ""
    if op in {"longpass"}:
        cut_on = _number_text(operation.get("cut_on_nm"))
        return f"{cut_on} nm longpass" if cut_on else ""
    if op in {"shortpass"}:
        cut_off = _number_text(operation.get("cut_off_nm") or operation.get("cut_on_nm"))
        return f"{cut_off} nm shortpass" if cut_off else ""
    if op in {"dichroic_reflect", "dichroic_transmit"}:
        bands = operation.get("bands")
        if bands:
            rendered = _bands_text(bands)
            return f"{rendered} nm" if rendered else ""
        cut_on = _number_text(operation.get("cut_on_nm"))
        return f"{cut_on} nm" if cut_on else ""
    return ""


def _position_type_noun(position: dict[str, Any], stage_role: str) -> str:
    """Name the kind of optic a position is, in Methods wording."""
    component_type = clean_text(position.get("component_type")).lower()
    noun = _POSITION_TYPE_NOUNS.get(component_type, "")
    if not noun:
        return ""
    adjective = _POSITION_STAGE_ADJECTIVES.get(clean_text(stage_role).lower(), "")
    # "excitation dichroic mirror" would be wrong; the stage role only qualifies
    # filters, never the dichroic or the cube that carries all three parts.
    if adjective and component_type in {"bandpass", "multiband_bandpass", "longpass", "shortpass"}:
        return f"{adjective} {noun}"
    return noun



def _operation_pass_windows(operation: dict[str, Any]) -> list[list[float | None]]:
    """The wavelength ranges one recorded spectral operation lets through.

    Only the operations whose pass band is fully recorded produce a window. A
    longpass or shortpass edge bounds one side only, and the unbounded side is
    `null` rather than a guessed limit or a float infinity - these windows are
    serialised into the instrument catalogue, and `Infinity` is not JSON a
    browser will parse.
    """
    op = clean_text(operation.get("op")).lower()
    windows: list[list[float | None]] = []

    def band_window(band: Any) -> None:
        if not isinstance(band, dict):
            return
        center = _float_or_none(band.get("center_nm"))
        width = _float_or_none(band.get("width_nm"))
        if center is None:
            return
        half = (width / 2) if width else 0.0
        windows.append([center - half, center + half])

    if op in {"bandpass", "multiband_bandpass"}:
        bands = operation.get("bands")
        if isinstance(bands, list) and bands:
            for band in bands:
                band_window(band)
        else:
            band_window(operation)
    elif op == "longpass":
        cut_on = _float_or_none(operation.get("cut_on_nm"))
        if cut_on is not None:
            windows.append([cut_on, None])
    elif op == "shortpass":
        cut_off = _float_or_none(operation.get("cut_off_nm") or operation.get("cut_on_nm"))
        if cut_off is not None:
            windows.append([None, cut_off])
    return windows


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _position_excitation_windows(position: dict[str, Any]) -> list[list[float | None]]:
    """What a position lets reach the sample, as recorded pass windows.

    A source whose recorded emission cannot pass these windows cannot have
    excited anything through this position. That is the one statement these
    numbers support, and the Methods page uses it to ask rather than to decide:
    an EVOS light cube carries its own LED, so pairing the 470 nm GFP cube's LED
    with the Cy5 cube is a configuration the instrument cannot produce, and the
    draft used to report both without comment.
    """
    spectral_ops = position.get("spectral_ops") if isinstance(position.get("spectral_ops"), dict) else {}
    windows: list[list[float | None]] = []
    for operation in spectral_ops.get("illumination") or []:
        if not isinstance(operation, dict):
            continue
        # A dichroic steers rather than defines the excitation band, and reading
        # its edge as a pass window would reject legitimate pairings.
        if clean_text(operation.get("sub_role")) == "dichroic":
            continue
        windows.extend(_operation_pass_windows(operation))
    return windows


# Positions that exist to select a fluorescence band. A route that declares no
# imaging mode implements only contrast methods - transmitted brightfield, phase
# contrast, DIC - and none of those select an emission band.
#
# Public: scripts/ledger_gaps.py asks the same question about a whole holder
# (every recorded position selects a fluorescence band) rather than one position
# on one route, and imports these rather than keeping its own copy - which had
# already happened once and could silently disagree with this one.
FLUORESCENCE_PASSBAND_TYPES = {
    "bandpass", "multiband_bandpass", "longpass", "shortpass", "notch",
}
FLUORESCENCE_STAGE_ROLES = {"excitation", "emission", "cube"}


def route_declares_imaging(route: dict[str, Any]) -> bool:
    """True when a canonical route declares at least one imaging mode.

    A route whose `imaging_modes` is empty is not an unfinished record: the
    vocabulary authors `covers.imaging_modes: []` for the transmitted-light and
    reflected-light families, and the instrument records follow it. Such a route
    carries only contrast methods.
    """
    modes = route.get("imaging_modes")
    return isinstance(modes, list) and bool([mode for mode in modes if clean_text(mode)])


def position_serves_route(position: dict[str, Any], stage_role: str, route_declares_imaging_modes: bool) -> bool:
    """Whether a recorded position can be the one a given route was set to.

    The BC43 records its internal emission filter wheel on the transmitted path as
    well as the fluorescence ones, and the wheel holds four fluorescence bandpass
    filters and no open position. Offering those on a brightfield acquisition let a
    draft state "the light path included a mCherry emission bandpass filter
    (600/50 nm)" in a transmitted-light paragraph, and asking which of them was
    used had no answer a brightfield author could give.

    Nothing here decides what the wheel really holds. It refuses to present a
    fluorescence band as a brightfield choice; `scripts/ledger_gaps.py` asks the
    facility whether the path is recorded correctly and whether the wheel has an
    open position that is not written down.
    """
    if route_declares_imaging_modes:
        return True
    component_type = clean_text(position.get("component_type")).lower()
    if component_type not in FLUORESCENCE_PASSBAND_TYPES:
        return True
    return clean_text(stage_role).lower() not in FLUORESCENCE_STAGE_ROLES


def _selectable_positions_by_component(light_paths: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Collect the positions each multi-position optical element can be set to.

    Without these the Methods page can only offer the holder - "the light path
    included Filter Turret" - which tells a reader nothing about the filter that
    was used, the most important light-path fact in a fluorescence Methods
    section. The positions are recorded per route in `selected_execution`; this
    indexes them by component so the page can offer them as choices.
    """
    positions_by_component: dict[str, list[dict[str, Any]]] = {}
    for route in light_paths:
        route_id = clean_text(route.get("id"))
        route_label = clean_text(route.get("name") or route.get("display_label") or route_id)
        route_images = route_declares_imaging(route)
        selected_execution = route.get("selected_execution") if isinstance(route.get("selected_execution"), dict) else {}
        steps = selected_execution.get("selected_route_steps")
        for step in steps if isinstance(steps, list) else []:
            if not isinstance(step, dict):
                continue
            inventory_id = clean_text(step.get("hardware_inventory_id"))
            available = step.get("available_positions")
            if not inventory_id or not isinstance(available, list):
                continue
            holder_label = clean_text(step.get("display_label"))
            holder_stage_role = clean_text(step.get("stage_role"))
            known = positions_by_component.setdefault(inventory_id, [])
            by_key = {row["id"]: row for row in known}
            by_identity = {
                (row["display_label"], row["product_code"], row["component_type"].lower()): row
                for row in known
            }
            for position in available:
                if not isinstance(position, dict):
                    continue
                if not position_serves_route(position, holder_stage_role, route_images):
                    continue
                key = clean_text(position.get("position_key") or position.get("position_id"))
                # The holder's own name identifies the container, never the filter
                # inside it. A candidate equal to it is refused outright so no
                # upstream default can produce "the Filter Turret in the Filter
                # Turret"; the position key is a last-resort distinguishable label.
                identity_label = next(
                    (
                        candidate
                        for candidate in (
                            clean_text(position.get(field))
                            for field in ("name", "model", "position_label", "label", "product_code")
                        )
                        if candidate and candidate != holder_label
                    ),
                    "",
                )
                label = identity_label or key
                if not key or not label:
                    continue
                # A holder shared by two routes may offer different positions on
                # each. Keeping the route each position came from is what lets the
                # page refuse "route A plus a position that only exists on route B".
                existing = by_key.get(key)
                if existing is not None:
                    if route_id and route_id not in existing["route_ids"]:
                        existing["route_ids"].append(route_id)
                        existing["route_labels"].append(route_label)
                    continue
                # Two slots of one holder that record the same identity are the
                # same choice to a user and publish the same sentence, so offering
                # both only asks a question with no answer. Naming them apart would
                # mean inventing a distinction the record does not make.
                twin = (label, clean_text(position.get("product_code")), clean_text(position.get("component_type")).lower())
                duplicate = by_identity.get(twin)
                if duplicate is not None:
                    if route_id and route_id not in duplicate["route_ids"]:
                        duplicate["route_ids"].append(route_id)
                    if route_label and route_label not in duplicate["route_labels"]:
                        duplicate["route_labels"].append(route_label)
                    continue
                row = {
                    "id": key,
                    "display_label": label,
                    # False when `display_label` is only the position key or a
                    # generic emptiness word, so the browser never presents an
                    # internal slot id - or "(position Empty)" - as an identity.
                    "has_identity": bool(identity_label)
                    and identity_label.lower() not in _EMPTY_POSITION_WORDS
                    and not _looks_like_internal_id(identity_label),
                    "product_code": clean_text(position.get("product_code")),
                    "manufacturer": _identity_value(position.get("manufacturer")),
                    "component_type": clean_text(position.get("component_type")),
                    # What the filter passes, in publication wording, and what kind
                    # of optic it is. Both come from the recorded spectral model;
                    # neither is inferred when the record does not carry it.
                    "spec_phrase": _position_spec_phrase(position),
                    # The recorded pass windows on the illumination side, so the
                    # page can ask about a source that cannot reach the sample
                    # through this position instead of reporting both as fact.
                    "excitation_windows": _position_excitation_windows(position),
                    "type_noun": _position_type_noun(position, holder_stage_role),
                    "stage_role": holder_stage_role,
                    "selection_mode": clean_text(position.get("selection_mode")).lower() or "exclusive",
                    "is_empty": (
                        clean_text(position.get("component_type")).lower() == "empty"
                        or clean_text(label).lower() in _EMPTY_POSITION_WORDS
                    ),
                    "incomplete": bool(position.get("_cube_incomplete") or position.get("_unsupported_spectral_model")),
                    "route_ids": [route_id] if route_id else [],
                    "route_labels": [route_label] if route_label else [],
                }
                row["publication_phrase"] = _publication_position_phrase(row)
                by_key[key] = row
                by_identity[twin] = row
                known.append(row)
    return positions_by_component


def hardware_renderables_from_inventory(
    inventory_renderables: list[dict[str, Any]],
    hardware_ids: set[str],
    *inventory_classes: str,
) -> list[dict[str, Any]]:
    allowed = set(inventory_classes)
    rows: list[dict[str, Any]] = []
    for item in inventory_renderables:
        if clean_text(item.get("id")) not in hardware_ids:
            continue
        if allowed and clean_text(item.get("inventory_class")) not in allowed:
            continue
        rows.append(copy.deepcopy(item))
    return rows


def _inventory_display_number(
    inventory_id: str,
    inventory_lookup: dict[str, dict[str, Any]],
    hardware_index_map: dict[str, Any],
) -> int | None:
    item = inventory_lookup.get(inventory_id) or {}
    display_number = item.get("display_number")
    if isinstance(display_number, int):
        return display_number
    by_inventory_id = hardware_index_map.get("by_inventory_id") if isinstance(hardware_index_map.get("by_inventory_id"), dict) else {}
    value = by_inventory_id.get(inventory_id)
    return value if isinstance(value, int) else None


def _normalized_hardware_index_map(hardware_inventory: list[dict[str, Any]], raw_index_map: dict[str, Any]) -> dict[str, Any]:
    by_inventory_id = copy.deepcopy(raw_index_map.get("by_inventory_id") or {}) if isinstance(raw_index_map, dict) else {}
    by_ref = copy.deepcopy(raw_index_map.get("by_ref") or {}) if isinstance(raw_index_map, dict) else {}
    by_hardware_id = copy.deepcopy(raw_index_map.get("by_hardware_id") or {}) if isinstance(raw_index_map, dict) else {}

    for item in hardware_inventory:
        if not isinstance(item, dict):
            continue
        inventory_id = clean_text(item.get("id"))
        hardware_id = clean_text(item.get("hardware_id"))
        display_number = item.get("display_number")
        if inventory_id and isinstance(display_number, int):
            by_inventory_id.setdefault(inventory_id, display_number)
        if inventory_id:
            by_ref.setdefault(inventory_id, inventory_id)
        if hardware_id and isinstance(display_number, int):
            by_hardware_id.setdefault(hardware_id, display_number)

    return {
        "by_inventory_id": by_inventory_id,
        "by_ref": by_ref,
        "by_hardware_id": by_hardware_id,
    }


def _normalized_hardware_inventory(
    hardware_inventory: list[dict[str, Any]],
    hardware_index_map: dict[str, Any],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in hardware_inventory:
        if not isinstance(item, dict):
            continue
        inventory_id = clean_text(item.get("id"))
        hardware_id = clean_text(item.get("hardware_id"))
        normalized.append({
            **copy.deepcopy(item),
            "display_number": item.get("display_number") or _inventory_display_number(inventory_id, {inventory_id: item}, hardware_index_map),
            "inventory_identity": copy.deepcopy(item.get("inventory_identity") or {
                "inventory_id": inventory_id,
                "hardware_id": hardware_id,
                "component_type": clean_text(item.get("component_type")),
            }),
        })
    return normalized


def _route_endpoint_summary(
    usage: dict[str, Any],
    inventory_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    endpoint_ids = [clean_text(item) for item in (usage.get("endpoint_inventory_ids") or []) if clean_text(item)]
    endpoint_items = [copy.deepcopy(inventory_lookup[item_id]) for item_id in endpoint_ids if item_id in inventory_lookup]
    return {
        "count": len(endpoint_items),
        "inventory_ids": endpoint_ids,
        "labels": [clean_text(item.get("display_label") or item.get("id")) for item in endpoint_items if clean_text(item.get("display_label") or item.get("id"))],
        "items": endpoint_items,
    }


def _route_branch_summary(route: dict[str, Any], usage: dict[str, Any]) -> dict[str, Any]:
    branch_blocks = [copy.deepcopy(item) for item in (usage.get("branch_blocks") or route.get("branch_blocks") or []) if isinstance(item, dict)]
    branches: list[dict[str, Any]] = []
    selection_modes: list[str] = []
    for block in branch_blocks:
        selection_mode = clean_text(block.get("selection_mode"))
        if selection_mode and selection_mode not in selection_modes:
            selection_modes.append(selection_mode)
        for branch in block.get("branches") or []:
            if not isinstance(branch, dict):
                continue
            branches.append({
                "block_id": clean_text(block.get("id")),
                "selection_mode": selection_mode,
                "branch_id": clean_text(branch.get("branch_id") or branch.get("id")),
                "label": clean_text(branch.get("label") or branch.get("branch_id") or branch.get("id")),
                "mode": clean_text(branch.get("mode")),
                "hardware_inventory_ids": [clean_text(item) for item in (branch.get("hardware_inventory_ids") or []) if clean_text(item)],
                "endpoint_inventory_ids": [clean_text(item) for item in (branch.get("endpoint_inventory_ids") or []) if clean_text(item)],
            })
    return {
        "has_branches": bool(branch_blocks),
        "count": len(branches),
        "selection_modes": selection_modes,
        "branch_blocks": branch_blocks,
        "branches": branches,
    }


def _build_route_optical_facts(selected_execution: dict[str, Any]) -> dict[str, Any]:
    fact_keys = [
        "selected_or_selectable_sources",
        "selected_or_selectable_excitation_filters",
        "selected_or_selectable_dichroics",
        "selected_or_selectable_emission_filters",
        "selected_or_selectable_splitters",
        "selected_or_selectable_endpoints",
        "selected_or_selectable_modulators",
        "selected_or_selectable_branch_selectors",
    ]
    selected_route_steps = (
        selected_execution.get("selected_route_steps")
        if isinstance(selected_execution.get("selected_route_steps"), list)
        else []
    )

    facts: dict[str, list[Any]] = {key: [] for key in fact_keys}
    seen_serializations: dict[str, set[str]] = {key: set() for key in fact_keys}

    for step in selected_route_steps:
        if not isinstance(step, dict):
            continue
        for fact_key in fact_keys:
            raw_value = step.get(fact_key)
            if raw_value is None:
                continue
            candidate_rows = raw_value if isinstance(raw_value, list) else [raw_value]
            for candidate in candidate_rows:
                if candidate is None:
                    continue
                serialized = json.dumps(candidate, sort_keys=True, default=str)
                if serialized in seen_serializations[fact_key]:
                    continue
                seen_serializations[fact_key].add(serialized)
                facts[fact_key].append(copy.deepcopy(candidate))

    return {
        "contract_version": "route_optical_facts.v1",
        "selected_route_step_count": len(selected_route_steps),
        **facts,
    }


def build_optical_path_view_dto(lightpath_dto: dict[str, Any], raw_hardware: dict[str, Any] | None = None, vocabulary: Vocabulary | None = None) -> dict[str, Any]:
    """
    Build the downstream optical-path DTO.

    Authoritative downstream contract:
    - hardware_inventory / hardware_index_map
    - light_paths (one canonical graph-backed route record per route)
    - authoritative_route_contract (compact route-planning contract for UIs/LLMs)

    Derived-only compatibility helpers:
    - sections / renderables / splitters / methods_route_views
    - runtime_splitters and other adapter/card-style projections
    """
    optical_elements = [item for item in (lightpath_dto.get("optical_path_elements") or []) if isinstance(item, dict)] if isinstance(lightpath_dto, dict) else []
    endpoints_raw = [item for item in (lightpath_dto.get("normalized_endpoints") or lightpath_dto.get("endpoints") or []) if isinstance(item, dict)] if isinstance(lightpath_dto, dict) else []
    light_paths = [item for item in (lightpath_dto.get("light_paths") or []) if isinstance(item, dict)] if isinstance(lightpath_dto, dict) else []
    raw_hardware_inventory = [item for item in (lightpath_dto.get("hardware_inventory") or []) if isinstance(item, dict)] if isinstance(lightpath_dto, dict) else []
    hardware_index_map = _normalized_hardware_index_map(
        raw_hardware_inventory,
        copy.deepcopy(lightpath_dto.get("hardware_index_map") or {}) if isinstance(lightpath_dto, dict) else {},
    )
    hardware_inventory = _normalized_hardware_inventory(raw_hardware_inventory, hardware_index_map)
    route_hardware_usage = [item for item in (lightpath_dto.get("route_hardware_usage") or []) if isinstance(item, dict)] if isinstance(lightpath_dto, dict) else []
    projection_root = (
        ((lightpath_dto.get("projections") or {}).get("virtual_microscope") or {})
        if isinstance(lightpath_dto, dict)
        else {}
    )
    legacy_splitters = [item for item in (projection_root.get("splitters") or lightpath_dto.get("splitters") or []) if isinstance(item, dict)] if isinstance(lightpath_dto, dict) else []

    derived_optical_element_cards: list[dict[str, Any]] = []
    derived_splitter_cards: list[dict[str, Any]] = []
    derived_endpoint_cards: list[dict[str, Any]] = []
    derived_sections: list[dict[str, Any]] = []

    element_items: list[dict[str, Any]] = []
    for element in optical_elements:
        raw_stage_role = clean_text(element.get("stage_role") or element.get("element_type") or element.get("type"))
        stage_role = resolve_stage_role_label(raw_stage_role, vocabulary) if vocabulary else raw_stage_role.replace("_", " ").title()
        if clean_text(element.get("stage_role")).lower() == "splitter":
            derived_splitter_cards.append({
                "id": clean_text(element.get("id")),
                "display_label": clean_text(element.get("name") or element.get("display_label") or element.get("id")),
                "display_subtitle": stage_role or "Splitter",
                "spec_lines": _spec_lines(("Selection mode", clean_text(element.get("selection_mode"))), ("Supported branch modes", ", ".join(element.get("supported_branch_modes") or [])), ("Supported branch count", clean_text(element.get("supported_branch_count")))),
                "method_sentence": f"Downstream routing may traverse {clean_text(element.get('name') or element.get('id'))}; explicit branch truth is declared on route-owned branch blocks.",
            })
        else:
            position_pairs = _optical_element_position_pairs(element, vocabulary)
            raw_element_type = clean_text(element.get("element_type") or element.get("type"))
            if vocabulary:
                element_type_label = resolve_element_type_label(raw_element_type, vocabulary)
            elif raw_element_type:
                element_type_label = raw_element_type.replace("_", " ").title()
            else:
                element_type_label = ""
            element_items.append({
                "id": clean_text(element.get("id")),
                "display_label": clean_text(element.get("name") or element.get("display_label") or element.get("id")),
                "display_subtitle": stage_role or "Optical path element",
                "spec_lines": _spec_lines(
                    ("Element type", element_type_label),
                    ("Details", clean_text(element.get("notes"))),
                    *position_pairs,
                ),
                "method_sentence": f"The optical path includes {clean_text(element.get('name') or element.get('id'))}.",
            })
    if element_items:
        derived_optical_element_cards.extend(element_items)
        derived_sections.append({"id": "optical_path_elements", "display_label": "Optical Path Elements", "items": element_items})
    route_splitters = [item for item in legacy_splitters if isinstance(item, dict)]
    if route_splitters:
        derived_splitter_cards = [
            {
                "id": clean_text(splitter.get("id") or splitter.get("name")),
                "display_label": clean_text(splitter.get("display_label") or splitter.get("name")),
                "display_subtitle": "Route-owned branch block",
                "spec_lines": _spec_lines(("Selection mode", clean_text(splitter.get("selection_mode"))), ("Branches", " • ".join(clean_text(branch.get("label") or branch.get("id")) for branch in splitter.get("branches", []) if isinstance(branch, dict)))),
                "method_sentence": f"Explicit route traversal branches through {clean_text(splitter.get('name') or splitter.get('display_label'))}.",
            }
            for splitter in route_splitters
        ]
    if derived_splitter_cards:
        derived_sections.append({"id": "splitters", "display_label": "Splitters / Selectors", "items": derived_splitter_cards})

    for idx, terminal in enumerate(endpoints_raw):
        raw_endpoint_type = clean_text(terminal.get("endpoint_type") or terminal.get("type") or terminal.get("kind"))
        endpoint_type = resolve_endpoint_type_label(raw_endpoint_type, vocabulary) if vocabulary else raw_endpoint_type.replace("_", " ").title()
        display_label = clean_text(terminal.get("display_label") or terminal.get("name") or terminal.get("id")) or f"Endpoint {idx + 1}"
        derived_endpoint_cards.append({
            "id": clean_text(terminal.get("id")) or f"endpoint_{idx}",
            "display_label": display_label,
            "display_subtitle": endpoint_type or "Endpoint",
            "spec_lines": _spec_lines(("Endpoint type", endpoint_type), ("Details", clean_text(terminal.get("details") or terminal.get("notes")))),
            "method_sentence": f"Detected or observed light can terminate at {display_label}.",
        })
    derived_sections.append({"id": "terminals", "display_label": "Detection Endpoints", "items": derived_endpoint_cards or [{"id": "no_explicit_terminals", "display_label": "No normalized detection endpoints available", "display_subtitle": "Structured topology incomplete", "spec_lines": ["**Action needed:** add endpoint-capable inventory rows (for example hardware.detectors[], hardware.eyepieces[], or hardware.endpoints[]) and terminate routes with explicit endpoint_id values."], "method_sentence": ""}]})

    derived_inventory_cards: list[dict[str, Any]] = []
    inventory_lookup = {item.get("id"): item for item in hardware_inventory if item.get("id")}
    selectable_positions = _selectable_positions_by_component(light_paths)
    for item in hardware_inventory:
        inventory_class = clean_text(item.get("inventory_class"))
        role = clean_text(((item.get("source_metadata") or {}) if isinstance(item.get("source_metadata"), dict) else {}).get("role"))
        publication_label = _publication_inventory_label(item, vocabulary)
        sentence_template, method_sentence, review_prompts = _inventory_method_facts(item, publication_label)
        derived_inventory_cards.append({
            **copy.deepcopy(item),
            "id": clean_text(item.get("id")),
            "display_number": item.get("display_number"),
            "display_label": publication_label or clean_text(item.get("display_label") or item.get("id")),
            "publication_label": publication_label,
            # Runtime plans and the virtual microscope carry the canonical label.
            # Keep it so cross-checks match on what those records actually contain.
            "canonical_display_label": clean_text(item.get("display_label") or item.get("id")),
            "display_subtitle": resolve_inventory_class_label(inventory_class, vocabulary) if vocabulary else inventory_class.replace("_", " ").title(),
            "spec_lines": _spec_lines(
                ("Number", f"`{item.get('display_number')}`" if item.get("display_number") else None),
                ("Manufacturer", clean_text(item.get("manufacturer"))),
                ("Model", clean_text(item.get("model"))),
                ("Product code", f"`{clean_text(item.get('product_code'))}`" if clean_text(item.get("product_code")) else None),
                ("Used in routes", ", ".join(item.get("route_usage_summary") or [])),
            ),
            "role": role,
            # Whether a source in this role produces an image channel, as its role
            # records. The channel-order question is about channels, and a depletion
            # beam is not one.
            "forms_imaging_channel": _role_forms_imaging_channel(role, vocabulary),
            "method_sentence": method_sentence,
            "publication_template": sentence_template,
            "review_prompts": review_prompts,
            "selectable_positions": copy.deepcopy(selectable_positions.get(clean_text(item.get("id")), [])),
        })
    if derived_inventory_cards:
        derived_sections.insert(0, {"id": "hardware_inventory", "display_label": "Hardware Inventory", "items": derived_inventory_cards})

    route_usage_map = {clean_text(item.get("route_id")): item for item in route_hardware_usage if clean_text(item.get("route_id"))}
    runtime_splitters = copy.deepcopy(projection_root.get("splitters", lightpath_dto.get("splitters", []))) if isinstance(lightpath_dto, dict) else []

    canonical_light_paths: list[dict[str, Any]] = []
    derived_route_summary_cards: list[dict[str, Any]] = []
    derived_methods_route_views = []
    derived_branch_summary_cards: list[dict[str, Any]] = []

    for route in light_paths:
        route_id = clean_text(route.get("id"))
        usage = copy.deepcopy(route_usage_map.get(route_id, {}))
        hardware_ids = [clean_text(item) for item in (usage.get("hardware_inventory_ids") or route.get("hardware_inventory_ids") or []) if clean_text(item)]
        endpoint_summary = _route_endpoint_summary(usage, inventory_lookup)
        branch_summary = _route_branch_summary(route, usage)
        route_hardware_items = [
            copy.deepcopy(inventory_lookup[item_id])
            for item_id in hardware_ids
            if item_id in inventory_lookup
        ]
        graph_nodes = []
        for node in route.get("graph_nodes") or []:
            if not isinstance(node, dict):
                continue
            inventory_id = clean_text(node.get("hardware_inventory_id"))
            inventory_item = inventory_lookup.get(inventory_id) or {}
            graph_nodes.append({
                **copy.deepcopy(node),
                "display_number": node.get("inventory_display_number") or node.get("display_number") or _inventory_display_number(inventory_id, inventory_lookup, hardware_index_map),
                "inventory_display_number": node.get("inventory_display_number") or node.get("display_number") or _inventory_display_number(inventory_id, inventory_lookup, hardware_index_map),
                "inventory_item": copy.deepcopy(inventory_item) if inventory_item else None,
                "inventory_label": clean_text(inventory_item.get("display_label") or node.get("label")),
                "inventory_class": clean_text(inventory_item.get("inventory_class")),
                "inventory_identity": copy.deepcopy(node.get("inventory_identity") or inventory_item.get("inventory_identity") or {}),
                "route_usage": {
                    "route_id": route_id,
                    "phase": clean_text(node.get("phase")),
                },
                "graph_occurrence": copy.deepcopy(node.get("graph_occurrence") or {
                    "node_id": clean_text(node.get("id")),
                    "route_id": route_id,
                    "phase": clean_text(node.get("phase")),
                    "column": node.get("column"),
                    "lane": node.get("lane"),
                }),
            })
        graph_edges = [copy.deepcopy(edge) for edge in (route.get("graph_edges") or []) if isinstance(edge, dict)]
        graph_node_lookup = {clean_text(item.get("id")): item for item in graph_nodes if clean_text(item.get("id"))}
        graph_edges = [
            {
                **edge,
                "source_display_number": (graph_node_lookup.get(clean_text(edge.get("source"))) or {}).get("display_number"),
                "target_display_number": (graph_node_lookup.get(clean_text(edge.get("target"))) or {}).get("display_number"),
            }
            for edge in graph_edges
        ]

        canonical_route = {
            "id": route_id,
            "name": clean_text(route.get("name") or route.get("id")),
            "route_identity": copy.deepcopy(route.get("route_identity") or {}),
            "graph_nodes": graph_nodes,
            "graph_edges": graph_edges,
            "route_hardware_usage": usage,
            "route_local_hardware_usage": {
                "inventory_ids": hardware_ids,
                "items": route_hardware_items,
            },
            "endpoint_summary": endpoint_summary,
            "branch_summary": branch_summary,
            "illumination_traversal": copy.deepcopy(route.get("illumination_traversal") or []),
            "detection_traversal": copy.deepcopy(route.get("detection_traversal") or []),
            "route_steps": copy.deepcopy(route.get("route_steps") or []),
            "selected_execution": copy.deepcopy(route.get("selected_execution") or {}),
            "route_warnings": copy.deepcopy(route.get("route_warnings") or []),
            "illumination_sequence": copy.deepcopy(route.get("illumination_sequence") or []),
            "detection_sequence": copy.deepcopy(route.get("detection_sequence") or []),
        }

        route_hw_id_set = set(hardware_ids)
        route_light_sentences = [
            clean_text(item.get("method_sentence"))
            for item in hardware_renderables_from_inventory(derived_inventory_cards, route_hw_id_set, "light_source")
            if clean_text(item.get("method_sentence"))
        ]
        route_filter_sentences = [
            clean_text(item.get("method_sentence"))
            for item in hardware_renderables_from_inventory(derived_inventory_cards, route_hw_id_set, "optical_element")
            if clean_text(item.get("method_sentence"))
        ]
        route_splitter_sentences = [
            clean_text(item.get("method_sentence"))
            for item in hardware_renderables_from_inventory(derived_inventory_cards, route_hw_id_set, "splitter")
            if clean_text(item.get("method_sentence"))
        ]
        route_detector_sentences = [
            clean_text(item.get("method_sentence"))
            for item in hardware_renderables_from_inventory(derived_inventory_cards, route_hw_id_set, "endpoint", "camera_port", "eyepiece")
            if clean_text(item.get("method_sentence"))
        ]
        route_method_paragraph = " ".join(
            route_light_sentences + route_filter_sentences + route_splitter_sentences + route_detector_sentences
        )
        canonical_route["route_method_paragraph"] = route_method_paragraph

        canonical_light_paths.append(canonical_route)

        hardware_labels = [clean_text(item.get("display_label") or item.get("id")) for item in route_hardware_items if clean_text(item.get("display_label") or item.get("id"))]
        derived_route_summary_cards.append({
            "id": route_id,
            "display_label": canonical_route["name"],
            "display_subtitle": "Route-owned DTO graph",
            "spec_lines": _spec_lines(
                ("Graph nodes", len(graph_nodes)),
                ("Graph edges", len(graph_edges)),
                ("Hardware used", _human_list(hardware_labels[:6]) if hardware_labels else None),
                ("Endpoints", _human_list(endpoint_summary.get("labels") or [])),
                ("Branching", f"{branch_summary['count']} branch path(s) across {len(branch_summary['branch_blocks'])} block(s)" if branch_summary.get("has_branches") else "No explicit branch blocks"),
            ),
            "method_sentence": f"The {canonical_route['name']} route is rendered directly from DTO graph nodes and edges.",
        })
        derived_methods_route_views.append({
            "id": route_id,
            "display_label": canonical_route["name"],
            "route_method_paragraph": route_method_paragraph,
            "light_sources": [item for item in hardware_renderables_from_inventory(derived_inventory_cards, set(hardware_ids), "light_source")],
            "filters": [item for item in hardware_renderables_from_inventory(derived_inventory_cards, set(hardware_ids), "optical_element")],
            "splitters": [item for item in hardware_renderables_from_inventory(derived_inventory_cards, set(hardware_ids), "splitter")],
            "detectors": [item for item in hardware_renderables_from_inventory(derived_inventory_cards, set(hardware_ids), "endpoint", "camera_port", "eyepiece")],
            "endpoints": copy.deepcopy(endpoint_summary.get("items") or []),
            "route_hardware_usage": copy.deepcopy(usage),
            "graph_nodes": copy.deepcopy(graph_nodes),
            "graph_edges": copy.deepcopy(graph_edges),
            "branch_summary": copy.deepcopy(branch_summary),
        })
        if branch_summary.get("has_branches"):
            derived_branch_summary_cards.append({
                "id": route_id,
                "display_label": canonical_route["name"],
                "display_subtitle": "Route-owned branch summary",
                "spec_lines": _spec_lines(
                    ("Selection modes", ", ".join(branch_summary.get("selection_modes") or [])),
                    ("Branches", " • ".join(branch.get("label") or branch.get("branch_id") for branch in branch_summary.get("branches") or [] if clean_text(branch.get("label") or branch.get("branch_id")))),
                    ("Endpoints", _human_list(endpoint_summary.get("labels") or [])),
                ),
                "method_sentence": f"Explicit route traversal branches are declared directly on the {canonical_route['name']} route.",
            })

    if derived_route_summary_cards:
        derived_sections.append({"id": "light_paths", "display_label": "Light Paths", "items": derived_route_summary_cards})
    if derived_branch_summary_cards:
        derived_splitter_cards = derived_branch_summary_cards
    derived_renderables = [*derived_inventory_cards, *derived_route_summary_cards, *derived_optical_element_cards, *derived_splitter_cards, *derived_endpoint_cards]

    authoritative_route_contract_routes: list[dict[str, Any]] = []
    compact_hardware_inventory = [
        {
            "id": clean_text(item.get("id")),
            "display_label": clean_text(item.get("display_label") or item.get("id")),
            "display_number": item.get("display_number"),
            "inventory_class": clean_text(item.get("inventory_class")),
            "route_usage_summary": list(item.get("route_usage_summary") or []),
            "modalities": list(item.get("modalities") or []),
            "manufacturer": clean_text(item.get("manufacturer")),
            "model": clean_text(item.get("model")),
            "endpoint_type": clean_text(item.get("endpoint_type")),
        }
        for item in hardware_inventory
        if isinstance(item, dict)
    ]
    compact_normalized_endpoints = [
        {
            "id": clean_text(endpoint.get("id")),
            "display_label": clean_text(endpoint.get("display_label") or endpoint.get("channel_name") or endpoint.get("name") or endpoint.get("id")),
            "endpoint_type": clean_text(endpoint.get("endpoint_type") or endpoint.get("kind") or endpoint.get("type")),
            "source_section": clean_text(endpoint.get("source_section")),
            "modalities": list(endpoint.get("modalities") or []),
        }
        for endpoint in endpoints_raw
        if isinstance(endpoint, dict)
    ]

    for route_renderable in canonical_light_paths:
        route_id = clean_text(route_renderable.get("id"))
        route_usage = route_renderable.get("route_hardware_usage") if isinstance(route_renderable.get("route_hardware_usage"), dict) else {}
        route_inventory_ids = [
            clean_text(item)
            for item in (
                route_usage.get("hardware_inventory_ids")
                or ((route_renderable.get("route_local_hardware_usage") or {}).get("inventory_ids") if isinstance(route_renderable.get("route_local_hardware_usage"), dict) else [])
                or []
            )
            if clean_text(item)
        ]
        route_inventory_items = [
            copy.deepcopy(inventory_lookup[item_id])
            for item_id in route_inventory_ids
            if item_id in inventory_lookup
        ]

        def summarize_inventory_items(*classes: str) -> list[dict[str, Any]]:
            class_set = {clean_text(value) for value in classes if clean_text(value)}
            return [
                {
                    "id": clean_text(item.get("id")),
                    "display_label": clean_text(item.get("display_label") or item.get("id")),
                    "display_number": item.get("display_number"),
                    "inventory_class": clean_text(item.get("inventory_class")),
                    "route_usage_summary": list(item.get("route_usage_summary") or []),
                    "modalities": list(item.get("modalities") or []),
                    "endpoint_type": clean_text(item.get("endpoint_type")),
                    "manufacturer": clean_text(item.get("manufacturer")),
                    "model": clean_text(item.get("model")),
                }
                for item in route_inventory_items
                if clean_text(item.get("inventory_class")) in class_set
            ]

        route_identity = route_renderable.get("route_identity") if isinstance(route_renderable.get("route_identity"), dict) else {}
        route_label = clean_text(route_renderable.get("name") or route_renderable.get("id"))
        route_type = clean_text(route_identity.get("route_type") or route_id)
        illumination_mode = clean_text(route_renderable.get("illumination_mode") or route_type or route_id)
        selected_execution = copy.deepcopy(route_renderable.get("selected_execution") or {})

        # Enrich route_identity with vocabulary-resolved readout display labels so
        # downstream templates and LLM exports receive {id, display_label} dicts
        # instead of raw strings. Also populate route_type_label so the template
        # never falls back to a raw snake_case illumination_mode ID.
        enriched_route_identity = copy.deepcopy(route_identity)
        enriched_route_identity["readouts"] = [
            {
                "id": r,
                "display_label": _readout_vocab_label(r, vocabulary),
            }
            for r in (route_identity.get("readouts") or [])
            if isinstance(r, str) and r.strip()
        ]
        enriched_route_identity["imaging_modes"] = [
            {
                "id": value,
                "display_label": _route_type_vocab_label(value, vocabulary),
                "publication_phrase": _method_publication_phrase(value, vocabulary),
                "requires_source_role": _method_required_source_role(value, vocabulary),
            }
            for value in (route_identity.get("imaging_modes") or [])
            if isinstance(value, str) and value.strip()
        ]
        enriched_route_identity["contrast_methods"] = [
            {
                "id": value,
                "display_label": _route_type_vocab_label(value, vocabulary),
                "publication_phrase": _method_publication_phrase(value, vocabulary),
                "requires_source_role": _method_required_source_role(value, vocabulary),
            }
            for value in (route_identity.get("contrast_methods") or [])
            if isinstance(value, str) and value.strip()
        ]
        if not enriched_route_identity.get("route_type_label"):
            route_type_for_label = (
                enriched_route_identity.get("route_type")
                or route_type
            )
            if route_type_for_label:
                enriched_route_identity["route_type_label"] = _route_type_vocab_label(
                    route_type_for_label, vocabulary
                )

        authoritative_route_contract_routes.append({
            "id": route_id,
            "display_label": route_label,
            "illumination_mode": illumination_mode,
            "route_identity": enriched_route_identity,
            "route_type": route_type,
            "route_type_label": clean_text(enriched_route_identity.get("route_type_label")),
            "imaging_modes": enriched_route_identity["imaging_modes"],
            "contrast_methods": enriched_route_identity["contrast_methods"],
            "readouts": enriched_route_identity["readouts"],
            "route_hardware_usage": {
                "hardware_inventory_ids": route_inventory_ids,
                "endpoint_inventory_ids": list(route_usage.get("endpoint_inventory_ids") or []),
                "illumination_hardware_inventory_ids": list(route_usage.get("illumination_hardware_inventory_ids") or []),
                "detection_hardware_inventory_ids": list(route_usage.get("detection_hardware_inventory_ids") or []),
            },
            "relevant_hardware": {
                "sources": summarize_inventory_items("light_source"),
                "filters": summarize_inventory_items("optical_element"),
                "splitters": summarize_inventory_items("splitter"),
                "endpoints": summarize_inventory_items("endpoint", "camera_port", "eyepiece"),
            },
            "endpoint_summary": copy.deepcopy(route_renderable.get("endpoint_summary") or {}),
            "branch_summary": copy.deepcopy(route_renderable.get("branch_summary") or {}),
            "topology": {
                "graph_nodes": [
                    {
                        "id": clean_text(node.get("id")),
                        "label": clean_text(node.get("label") or node.get("inventory_label") or node.get("id")),
                        "component_kind": clean_text(node.get("component_kind") or node.get("stage_role") or node.get("endpoint_type")),
                        "phase": clean_text(node.get("phase")),
                        "hardware_inventory_id": clean_text(node.get("hardware_inventory_id")),
                        "display_number": node.get("inventory_display_number") or node.get("display_number"),
                        "column": node.get("column"),
                        "lane": node.get("lane"),
                        "endpoint_type": clean_text(node.get("endpoint_type")),
                    }
                    for node in (route_renderable.get("graph_nodes") or [])
                    if isinstance(node, dict)
                ],
                "graph_edges": [
                    {
                        "source": clean_text(edge.get("source")),
                        "target": clean_text(edge.get("target")),
                        "label": clean_text(edge.get("label") or edge.get("branch_id")),
                    }
                    for edge in (route_renderable.get("graph_edges") or [])
                    if isinstance(edge, dict)
                ],
            },
            "selected_execution": selected_execution,
            "route_optical_facts": _build_route_optical_facts(selected_execution),
            "method_sentence": (
                f"The {route_label} illumination mode / route was used."
                if route_label
                else ""
            ),
            "route_method_paragraph": clean_text(route_renderable.get("route_method_paragraph") or ""),
        })

    view_diagnostics: list[dict[str, str]] = []
    if not hardware_inventory:
        view_diagnostics.append({"severity": "warning", "code": "missing_hardware_inventory", "message": "missing in DTO: hardware_inventory"})
    if not canonical_light_paths:
        view_diagnostics.append({"severity": "warning", "code": "missing_light_paths", "message": "missing in DTO: light_paths"})

    return {
        **copy.deepcopy(lightpath_dto),
        "runtime_splitters": runtime_splitters,
        "hardware_inventory": copy.deepcopy(hardware_inventory),
        "hardware_index_map": copy.deepcopy(hardware_index_map),
        "light_paths": canonical_light_paths,
        "route_renderables": canonical_light_paths,
        "routes": canonical_light_paths,
        "filters": derived_optical_element_cards,
        "splitters": derived_splitter_cards,
        "terminal_renderables": derived_endpoint_cards,
        "hardware_inventory_renderables": derived_inventory_cards,
        "methods_route_options": [
            {
                "id": item["id"],
                "label": item["display_label"],
                "display_label": item["display_label"],
                "method_sentence": item.get("route_method_paragraph", ""),
            }
            for item in derived_methods_route_views
        ],
        "methods_route_views": derived_methods_route_views,
        "sections": derived_sections,
        "renderables": derived_renderables,
        "primary_rendering_contract": {
            "routes": "light_paths",
            "hardware_inventory": "hardware_inventory",
            "hardware_index_map": "hardware_index_map",
            "graph_fields": ["graph_nodes", "graph_edges"],
        },
        "derived_projection_contract": {
            "sections": "sections",
            "splitter_summaries": "splitters",
            "inventory_cards": "hardware_inventory_renderables",
            "route_summary_cards": "renderables/light_paths",
            "methods_route_views": "methods_route_views",
        },
        "authoritative_route_contract": {
            "contract_version": "authoritative_route_contract.v1",
            "primary_rendering_contract": {
                "routes": "light_paths",
                "hardware_inventory": "hardware_inventory",
                "route_hardware_usage": "route_hardware_usage",
                "normalized_endpoints": "normalized_endpoints",
                "graph_fields": ["graph_nodes", "graph_edges"],
            },
            "available_routes": [
                {
                    "id": clean_text(item.get("id")),
                    "display_label": clean_text(item.get("display_label") or item.get("label") or item.get("id")),
                }
                for item in derived_methods_route_views
                if isinstance(item, dict)
            ],
            "hardware_inventory": compact_hardware_inventory,
            "normalized_endpoints": compact_normalized_endpoints,
            "route_hardware_usage": copy.deepcopy(route_hardware_usage),
            "routes": authoritative_route_contract_routes,
        },
        "view_diagnostics": view_diagnostics,
    }


def build_optical_path_dto(lightpath_dto: dict[str, Any], raw_hardware: dict[str, Any] | None = None, vocabulary: Vocabulary | None = None) -> dict[str, Any]:
    """Backward-compatible alias for build_optical_path_view_dto."""
    return build_optical_path_view_dto(lightpath_dto, raw_hardware=raw_hardware, vocabulary=vocabulary)


__all__ = [
    "build_optical_path_view_dto",
    "build_optical_path_dto",
    "hardware_renderables_from_inventory",
    "FLUORESCENCE_PASSBAND_TYPES",
    "FLUORESCENCE_STAGE_ROLES",
]
