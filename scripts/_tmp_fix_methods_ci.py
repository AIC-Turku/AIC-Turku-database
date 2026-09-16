from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(path: str, old: str, new: str, count: int = 1) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if text.count(old) < count:
        raise RuntimeError(f"{path}: replacement anchor not found: {old[:120]!r}")
    target.write_text(text.replace(old, new, count), encoding="utf-8")


# 1) Objective display: keep explicit immersion metadata even if the user-facing
# slot/name happens to contain the same word (e.g. "Oil Objective Slot A"). Only
# suppress duplicated magnification/NA.
replace(
    "scripts/dashboard/instrument_view.py",
    '''    immersion_label = immersion.upper() if immersion else ""\n    if immersion_label and immersion_label.lower() in identity_label.lower():\n        immersion_label = ""\n    parts = [identity_label, mag_na, immersion_label]\n''',
    '''    immersion_label = immersion.upper() if immersion else ""\n    parts = [identity_label, mag_na, immersion_label]\n''',
)

# 2) Incomplete filter-cube wording: legacy/synthetic DTOs may not carry an
# explicit component_type. Preserve the established cube wording unless the type
# explicitly identifies another optical component such as an analyzer/polarizer.
replace(
    "assets/javascripts/methods_generator_app.js",
    '''            const componentType = cleanText(position?.component_type).toLowerCase();\n            const incompletePrompt = componentType === "filter_cube"\n                ? `[PLEASE VERIFY: the recorded transmission bands for ${positionLabel} are incomplete; confirm its excitation filter, dichroic and emission filter]`\n                : `[PLEASE VERIFY: the recorded optical details for ${positionLabel} are incomplete; confirm the exact setting used]`;\n''',
    '''            const componentType = cleanText(position?.component_type).toLowerCase();\n            const cubeLike = !componentType || componentType === "filter_cube";\n            const incompletePrompt = cubeLike\n                ? `[PLEASE VERIFY: the recorded transmission bands for ${positionLabel} are incomplete; confirm its excitation filter, dichroic and emission filter]`\n                : `[PLEASE VERIFY: the recorded optical details for ${positionLabel} are incomplete; confirm the exact setting used]`;\n''',
)

# 3) Legacy modality compatibility. Keep it only for records that really need the
# fallback: active old DTOs with neither capabilities nor explicit route methods,
# or retired route-less records. Explicit route/method contracts remain authoritative.
replace(
    "assets/javascripts/methods_generator_app.js",
    '''    function shouldUseLegacyModalities(dto) {\n        const modalities = Array.isArray(dto?.modalities) ? dto.modalities : [];\n        return modalities.length > 0 && routeViewsForInstrument(dto).length === 0;\n    }\n''',
    '''    function shouldUseLegacyModalities(dto) {\n        const modalities = Array.isArray(dto?.modalities) ? dto.modalities : [];\n        if (!modalities.length) return false;\n        const routeViews = routeViewsForInstrument(dto);\n        const hasRoutes = routeViews.length > 0;\n        if (dto?.retired) return !hasRoutes;\n        const caps = dto?.capabilities && typeof dto.capabilities === "object" ? dto.capabilities : {};\n        const hasCapabilities = Object.values(caps).some(value => Array.isArray(value) && value.length > 0);\n        const hasExplicitRouteMethods = routeViews.some(route => {\n            const identity = route?.route_identity && typeof route.route_identity === "object"\n                ? route.route_identity : {};\n            return (Array.isArray(identity.imaging_modes) && identity.imaging_modes.length > 0)\n                || (Array.isArray(identity.contrast_methods) && identity.contrast_methods.length > 0);\n        });\n        return !hasCapabilities && !hasExplicitRouteMethods;\n    }\n''',
)

# 4) Revert the broad parser-level position-label preference. It changed Virtual
# Microscope stage labels. Position identity improvement belongs only in the
# Methods-specific downstream view.
replace(
    "scripts/lightpath/route_graph.py",
    '''    position_label = (\n        _clean_string(position.get("display_label"))\n        or _clean_string(position.get("label"))\n        or _clean_string(position.get("name"))\n        or _clean_string(position.get("model"))\n        or _clean_string(component_payload.get("model"))\n        or _clean_string(position.get("product_code"))\n        or _clean_string(component_payload.get("display_label"))\n        or _clean_string(component_payload.get("label"))\n        or position_key\n        or (str(fallback_slot) if fallback_slot is not None else None)\n    )\n''',
    '''    position_label = (\n        _clean_string(position.get("display_label"))\n        or _clean_string(position.get("label"))\n        or _clean_string(position.get("name"))\n        or _clean_string(component_payload.get("display_label"))\n        or _clean_string(component_payload.get("label"))\n        or position_key\n        or (str(fallback_slot) if fallback_slot is not None else None)\n    )\n''',
)

# Methods-only position identity: prefer a recorded human name/model before the
# parser fallback label, without altering the canonical VM/runtime projection.
replace(
    "scripts/dashboard/optical_path_view.py",
    '''                label = clean_text(position.get("position_label") or position.get("label") or position.get("name"))\n''',
    '''                label = clean_text(\n                    position.get("name")\n                    or position.get("model")\n                    or position.get("position_label")\n                    or position.get("label")\n                    or position.get("product_code")\n                )\n''',
)

# 5) The old regression explicitly required an internal "(Compatibility)" marker.
# The product requirement is now the opposite: route-less legacy records may still
# report their selected modality, but migration vocabulary must not leak into prose.
path = ROOT / "tests/test_methods_generator_template.py"
text = path.read_text(encoding="utf-8")
old = '''        # Modality text must appear with compatibility label, not as primary sentence\n        self.assertIn("(Compatibility)", result["output"])\n        # The raw modality sentence style "imaging modalities used included X" may appear\n        # but ONLY under the (Compatibility) marker — the primary paragraph must not\n        # start with a modality sentence.\n        lines = result["output"].split("\\n\\n")\n        primary = lines[0] if lines else ""\n        self.assertNotIn("Imaging modality", primary,\n                         "Primary paragraph must not contain modality sentence; it belongs in (Compatibility) section")\n'''
new = '''        # Route-less legacy records may still report the selected modality, but\n        # implementation/migration vocabulary must never enter manuscript prose.\n        self.assertNotIn("(Compatibility)", result["output"])\n        self.assertIn("Imaging modality used was Confocal.", result["output"])\n'''
if old not in text:
    raise RuntimeError("legacy compatibility test assertion anchor not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")

print("Methods CI compatibility repairs applied")
