from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def replace(path: str, old: str, new: str, *, count: int = 1) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    found = text.count(old)
    if found < count:
        raise RuntimeError(f"{path}: expected at least {count} occurrence(s), found {found}: {old[:100]!r}")
    target.write_text(text.replace(old, new, count), encoding="utf-8")


def regex(path: str, pattern: str, replacement: str, *, count: int = 1, flags: int = 0) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    updated, n = re.subn(pattern, replacement, text, count=count, flags=flags)
    if n != count:
        raise RuntimeError(f"{path}: expected {count} regex replacement(s), got {n}: {pattern[:100]!r}")
    target.write_text(updated, encoding="utf-8")


# -----------------------------------------------------------------------------
# Route contract: a user-facing imaging method is explicitly associated with the
# physical light path that supports it. route_type remains the path family.
# -----------------------------------------------------------------------------
replace(
    "scripts/lightpath/parse_canonical.py",
    '''            "readouts": [\n                r.strip()\n                for r in (route.get("readouts") or [])\n                if isinstance(r, str) and r.strip()\n            ],\n            "illumination_sequence": illumination_sequence,\n''',
    '''            "readouts": [\n                r.strip()\n                for r in (route.get("readouts") or [])\n                if isinstance(r, str) and r.strip()\n            ],\n            "imaging_modes": [\n                value.strip()\n                for value in (route.get("imaging_modes") or [])\n                if isinstance(value, str) and value.strip()\n            ],\n            "contrast_methods": [\n                value.strip()\n                for value in (route.get("contrast_methods") or [])\n                if isinstance(value, str) and value.strip()\n            ],\n            "illumination_sequence": illumination_sequence,\n''',
)

replace(
    "scripts/lightpath/route_graph.py",
    '''            "route_type_label": _resolve_route_label(route_type) if route_type else "",\n            "readouts": list(route.get("readouts") or []),\n        },\n''',
    '''            "route_type_label": _resolve_route_label(route_type) if route_type else "",\n            "readouts": list(route.get("readouts") or []),\n            "imaging_modes": list(route.get("imaging_modes") or []),\n            "contrast_methods": list(route.get("contrast_methods") or []),\n        },\n''',
)

# Selectable wheel/turret positions are alternatives by default; preserve the
# authored selection mode when present.
replace(
    "scripts/lightpath/selected_execution.py",
    '''                "component_type": (\n                    _clean_string(component.get("component_type")).lower()\n                    or None\n                ),\n                "spectral_ops": component.get("spectral_ops"),\n''',
    '''                "component_type": (\n                    _clean_string(component.get("component_type")).lower()\n                    or None\n                ),\n                "selection_mode": (\n                    _clean_string(element.get("selection_mode")).lower()\n                    or "exclusive"\n                ),\n                "spectral_ops": component.get("spectral_ops"),\n''',
)

# Prefer a position's own model/catalogue identity to its parent holder label.
replace(
    "scripts/lightpath/route_graph.py",
    '''    position_label = (\n        _clean_string(position.get("display_label"))\n        or _clean_string(position.get("label"))\n        or _clean_string(position.get("name"))\n        or _clean_string(component_payload.get("display_label"))\n        or _clean_string(component_payload.get("label"))\n        or position_key\n        or (str(fallback_slot) if fallback_slot is not None else None)\n    )\n''',
    '''    position_label = (\n        _clean_string(position.get("display_label"))\n        or _clean_string(position.get("label"))\n        or _clean_string(position.get("name"))\n        or _clean_string(position.get("model"))\n        or _clean_string(component_payload.get("model"))\n        or _clean_string(position.get("product_code"))\n        or _clean_string(component_payload.get("display_label"))\n        or _clean_string(component_payload.get("label"))\n        or position_key\n        or (str(fallback_slot) if fallback_slot is not None else None)\n    )\n''',
)

# -----------------------------------------------------------------------------
# Publication-safe optical-path rendering.
# -----------------------------------------------------------------------------
replace(
    "scripts/dashboard/optical_path_view.py",
    '_PLACEHOLDER_IDENTITY_VALUES = {"unknown", "unknown manufacturer", "n/a", "na", "none", "-", "--", "?"}\n',
    '_PLACEHOLDER_IDENTITY_VALUES = {"unknown", "unknown manufacturer", "placeholder", "n/a", "na", "none", "-", "--", "?"}\n',
)
replace(
    "scripts/dashboard/optical_path_view.py",
    '_SPLITTER_SENTENCE = "The emission light was divided by {label}."\n',
    '_SPLITTER_SENTENCE = "Light was directed through {label}."\n',
)
replace(
    "scripts/dashboard/optical_path_view.py",
    '''def _identity_value(value: Any) -> str:\n    """Return a manufacturer/model string, or "" when it only marks the value unknown."""\n    cleaned = clean_text(value)\n    return "" if cleaned.lower() in _PLACEHOLDER_IDENTITY_VALUES else cleaned\n\n\ndef _number_text(value: Any) -> str:\n    """Render a recorded number without a trailing ``.0``; "" when not numeric."""\n    if isinstance(value, bool) or value in (None, ""):\n        return ""\n    if isinstance(value, (int, float)):\n        return str(int(value)) if float(value).is_integer() else str(value)\n    return clean_text(value)\n''',
    '''def _identity_value(value: Any) -> str:\n    """Return an identity string, or "" when the value only marks it unresolved."""\n    cleaned = clean_text(value)\n    lowered = cleaned.lower()\n    if lowered in _PLACEHOLDER_IDENTITY_VALUES:\n        return ""\n    if lowered.startswith("unknown ") or lowered.startswith("placeholder"):\n        return ""\n    return cleaned\n\n\ndef _number_text(value: Any) -> str:\n    """Render a recorded number without a trailing ``.0``; "" when not numeric."""\n    if isinstance(value, bool) or value in (None, ""):\n        return ""\n    if isinstance(value, (int, float)):\n        return str(int(value)) if float(value).is_integer() else str(value)\n    cleaned = clean_text(value)\n    try:\n        numeric = float(cleaned)\n    except (TypeError, ValueError):\n        return ""\n    return str(int(numeric)) if numeric.is_integer() else str(numeric)\n''',
)
replace(
    "scripts/dashboard/optical_path_view.py",
    '    return trimmed or model\n',
    '    return trimmed\n',
)
replace(
    "scripts/dashboard/optical_path_view.py",
    '''                row = {\n                    "id": key,\n                    "display_label": label,\n                    "product_code": clean_text(position.get("product_code")),\n                    "component_type": clean_text(position.get("component_type")),\n                    "incomplete": bool(position.get("_cube_incomplete") or position.get("_unsupported_spectral_model")),\n                    "route_ids": [route_id] if route_id else [],\n                    "route_labels": [route_label] if route_label else [],\n                }\n''',
    '''                row = {\n                    "id": key,\n                    "display_label": label,\n                    "product_code": clean_text(position.get("product_code")),\n                    "component_type": clean_text(position.get("component_type")),\n                    "selection_mode": clean_text(position.get("selection_mode")).lower() or "exclusive",\n                    "is_empty": clean_text(label).lower() in {"empty", "none", "blank"},\n                    "incomplete": bool(position.get("_cube_incomplete") or position.get("_unsupported_spectral_model")),\n                    "route_ids": [route_id] if route_id else [],\n                    "route_labels": [route_label] if route_label else [],\n                }\n''',
)
replace(
    "scripts/dashboard/optical_path_view.py",
    '''        enriched_route_identity["readouts"] = [\n            {\n                "id": r,\n                "display_label": _readout_vocab_label(r, vocabulary),\n            }\n            for r in (route_identity.get("readouts") or [])\n            if isinstance(r, str) and r.strip()\n        ]\n''',
    '''        enriched_route_identity["readouts"] = [\n            {\n                "id": r,\n                "display_label": _readout_vocab_label(r, vocabulary),\n            }\n            for r in (route_identity.get("readouts") or [])\n            if isinstance(r, str) and r.strip()\n        ]\n        enriched_route_identity["imaging_modes"] = [\n            {"id": value, "display_label": _route_type_vocab_label(value, vocabulary)}\n            for value in (route_identity.get("imaging_modes") or [])\n            if isinstance(value, str) and value.strip()\n        ]\n        enriched_route_identity["contrast_methods"] = [\n            {"id": value, "display_label": _route_type_vocab_label(value, vocabulary)}\n            for value in (route_identity.get("contrast_methods") or [])\n            if isinstance(value, str) and value.strip()\n        ]\n''',
)
replace(
    "scripts/dashboard/optical_path_view.py",
    '''            "route_type_label": clean_text(enriched_route_identity.get("route_type_label")),\n            "readouts": enriched_route_identity["readouts"],\n''',
    '''            "route_type_label": clean_text(enriched_route_identity.get("route_type_label")),\n            "imaging_modes": enriched_route_identity["imaging_modes"],\n            "contrast_methods": enriched_route_identity["contrast_methods"],\n            "readouts": enriched_route_identity["readouts"],\n''',
)

# Tunable sources need the wavelength actually used, not just their installed range.
replace(
    "scripts/dashboard/optical_path_view.py",
    '''        if not template:\n            template = _SOURCE_ROLE_UNRECORDED_SENTENCE\n            prompts = [_SOURCE_ROLE_UNRECORDED_PROMPT.format(label=label)]\n''',
    '''        if not template:\n            template = _SOURCE_ROLE_UNRECORDED_SENTENCE\n            prompts = [_SOURCE_ROLE_UNRECORDED_PROMPT.format(label=label)]\n        tunable_min = _number_text(source_meta.get("tunable_min_nm"))\n        tunable_max = _number_text(source_meta.get("tunable_max_nm"))\n        if tunable_min and tunable_max:\n            prompts.append(\n                f"[PLEASE SPECIFY: wavelength used from the recorded {tunable_min}-{tunable_max} nm tunable range of {label}]"\n            )\n''',
)

# -----------------------------------------------------------------------------
# General Methods prose safety and readability.
# -----------------------------------------------------------------------------
replace(
    "scripts/dashboard/instrument_view.py",
    '_PLACEHOLDER_IDENTITY_VALUES = {"unknown", "unknown manufacturer", "n/a", "na", "none", "-", "--", "?"}\n',
    '_PLACEHOLDER_IDENTITY_VALUES = {"unknown", "unknown manufacturer", "placeholder", "n/a", "na", "none", "-", "--", "?"}\n',
)
replace(
    "scripts/dashboard/instrument_view.py",
    '''def _component_reference(manufacturer: Any, model: Any, fallback: str) -> str:\n    manufacturer_text = clean_text(manufacturer)\n    model_text = clean_text(model)\n''',
    '''def _component_reference(manufacturer: Any, model: Any, fallback: str) -> str:\n    manufacturer_text = _identity_value(manufacturer)\n    model_text = _identity_value(model)\n''',
)
replace(
    "scripts/dashboard/instrument_view.py",
    '''def _identity_value(value: Any) -> str:\n    """Return an identity string, or "" when it only marks the value unknown."""\n    cleaned = clean_text(value)\n    return "" if cleaned.lower() in _PLACEHOLDER_IDENTITY_VALUES else cleaned\n''',
    '''def _identity_value(value: Any) -> str:\n    """Return an identity string, or "" when it only marks the value unresolved."""\n    cleaned = clean_text(value)\n    lowered = cleaned.lower()\n    if lowered in _PLACEHOLDER_IDENTITY_VALUES:\n        return ""\n    if lowered.startswith("unknown ") or lowered.startswith("placeholder"):\n        return ""\n    return cleaned\n''',
)
# Product/catalogue numbers are useful when present but should not dominate UX as
# publication blockers when manufacturer/model already identify the component.
replace(
    "scripts/dashboard/instrument_view.py",
    '''        for label, value in (\n            ("manufacturer", manufacturer),\n            ("model", model),\n            ("product code", product_code),\n        )\n''',
    '''        for label, value in (\n            ("manufacturer", manufacturer),\n            ("model", model),\n        )\n''',
)
replace(
    "scripts/dashboard/instrument_view.py",
    '''    identity_label = instance_name or model\n    parts = [identity_label, f"{mag}x/{na}" if mag and na else f"{mag}x" if mag else "", immersion.upper() if immersion else ""]\n    return " ".join(part for part in parts if part).strip() or identity_label or "Objective"\n''',
    '''    identity_label = instance_name or model\n    mag_na = f"{mag}x/{na}" if mag and na else f"{mag}x" if mag else ""\n    if mag_na and mag_na.lower() in identity_label.lower():\n        mag_na = ""\n    immersion_label = immersion.upper() if immersion else ""\n    if immersion_label and immersion_label.lower() in identity_label.lower():\n        immersion_label = ""\n    parts = [identity_label, mag_na, immersion_label]\n    return " ".join(part for part in parts if part).strip() or identity_label or "Objective"\n''',
)
replace(
    "scripts/dashboard/instrument_view.py",
    '''    detail_bits = [f"line rate {line_rate} Hz" if line_rate else "", f"pinhole {pinhole} µm" if pinhole else ""]\n    detail_text = ", ".join(bit for bit in detail_bits if bit)\n    scanner_fallback = scanner_type if scanner_type.lower().endswith("scanner") else f"{scanner_type} scanner"\n''',
    '''    detail_bits = [\n        f"light-sheet type {light_sheet_type.replace('_', ' ')}" if light_sheet_type else "",\n        f"line rate {line_rate} Hz" if line_rate else "",\n        f"pinhole {pinhole} µm" if pinhole else "",\n    ]\n    detail_text = ", ".join(bit for bit in detail_bits if bit)\n    scanner_fallback = scanner_type if "scanner" in scanner_type.lower() else f"{scanner_type} scanner"\n''',
)
replace(
    "scripts/dashboard/instrument_view.py",
    '''        module_name = clean_text(module.get("display_name")) or _vocab_display(vocabulary, "modules", module_id) or module_id\n        manufacturer = clean_text(module.get("manufacturer"))\n''',
    '''        module_name = clean_text(module.get("display_name")) or _vocab_display(vocabulary, "modules", module_id) or module_id\n        manufacturer = clean_text(module.get("manufacturer"))\n''',
)
replace(
    "scripts/dashboard/instrument_view.py",
    '''                "method_sentence": _append_quarep_specs(f"The {module_name} module was used." if module_name else "", manufacturer, model, product_code),\n                "review_prompts": _quarep_review_prompts(f"{module_name} module", manufacturer, model, product_code),\n''',
    '''                "method_sentence": _append_quarep_specs(\n                    f"The {module_name if module_name.lower().endswith('module') else module_name + ' module'} was used."\n                    if module_name else "",\n                    manufacturer, model, product_code,\n                ),\n                "review_prompts": _quarep_review_prompts(\n                    module_name if module_name.lower().endswith("module") else f"{module_name} module",\n                    manufacturer, model, product_code,\n                ),\n''',
)
# A routing component is not evidence that filters/dichroics are documented.
replace(
    "scripts/dashboard/instrument_view.py",
    '''                if clean_text(step.get("kind")) not in {"optical_component", "routing_component"}:\n                    continue\n''',
    '''                if clean_text(step.get("kind")) != "optical_component":\n                    continue\n''',
)

# -----------------------------------------------------------------------------
# Method-first Methods Generator UX.
# -----------------------------------------------------------------------------
replace(
    "scripts/templates/methods_generator.md.j2",
    '''    <div id="section-route" class="methods-option-section">\n      <strong>Optical routes and readouts</strong>\n      <div id="route-list" style="margin-bottom: 15px; margin-top: 5px; margin-left: 10px;"></div>\n    </div>\n''',
    '''    <div id="section-method" class="methods-option-section">\n      <strong>Imaging method</strong>\n      <p>Choose what you actually did. The generator will then show the compatible recorded light path and only the route-specific optical components.</p>\n      <div id="method-list" style="margin-bottom: 15px; margin-top: 5px; margin-left: 10px;"></div>\n    </div>\n    <div id="section-route" class="methods-option-section">\n      <strong>Light path and readouts</strong>\n      <div id="route-list" style="margin-bottom: 15px; margin-top: 5px; margin-left: 10px;"></div>\n    </div>\n    <p id="methods-selection-status" role="status" style="display:none;"></p>\n''',
)

# bindCheckboxes can render route-owned exclusive choices as radios.
replace(
    "assets/javascripts/methods_generator_app.js",
    '''    function bindCheckboxes(containerId, items, prefix, selectedIds = new Set()) {\n''',
    '''    function bindCheckboxes(containerId, items, prefix, selectedIds = new Set(), selectedPositionIds = new Set()) {\n''',
)
replace(
    "assets/javascripts/methods_generator_app.js",
    '''            checkbox.type = "checkbox";\n            checkbox.id = `${prefix}-${index}`;\n''',
    '''            checkbox.type = item.selection_group ? "radio" : "checkbox";\n            if (item.selection_group) checkbox.name = `${prefix}-${item.selection_group}`;\n            checkbox.id = `${prefix}-${index}`;\n''',
    count=1,
)
replace(
    "assets/javascripts/methods_generator_app.js",
    '''            bindSelectablePositions(container, item, prefix, index);\n''',
    '''            bindSelectablePositions(container, item, prefix, index, selectedPositionIds);\n''',
    count=1,
)
replace(
    "assets/javascripts/methods_generator_app.js",
    '''    function bindSelectablePositions(container, item, prefix, itemIndex) {\n''',
    '''    function bindSelectablePositions(container, item, prefix, itemIndex, selectedPositionIds = new Set()) {\n''',
)
replace(
    "assets/javascripts/methods_generator_app.js",
    '''            const checkbox = document.createElement("input");\n            checkbox.type = "checkbox";\n            checkbox.id = `${prefix}position-${itemIndex}-${positionIndex}`;\n            checkbox.value = `${componentId}::${positionId}`;\n''',
    '''            const checkbox = document.createElement("input");\n            const selectionMode = cleanText(position?.selection_mode).toLowerCase() || "exclusive";\n            checkbox.type = selectionMode === "multiple" ? "checkbox" : "radio";\n            if (checkbox.type === "radio") checkbox.name = `${prefix}position-${componentId}`;\n            checkbox.id = `${prefix}position-${itemIndex}-${positionIndex}`;\n            checkbox.value = `${componentId}::${positionId}`;\n            checkbox.checked = selectedPositionIds.has(checkbox.value);\n''',
)
replace(
    "assets/javascripts/methods_generator_app.js",
    '''            const productCode = cleanText(position?.product_code);\n            const identity = productCode ? `${positionLabel} (catalogue no. ${productCode})` : positionLabel;\n            checkbox.dataset.publicationTemplate = "The light path included {label}.";\n            checkbox.dataset.publicationLabel = componentLabel\n                ? `${identity} in the ${componentLabel}`\n                : identity;\n            checkbox.dataset.reviewPrompts = JSON.stringify(position?.incomplete ? [\n                `[PLEASE VERIFY: the recorded transmission bands for ${positionLabel} are incomplete; confirm its excitation filter, dichroic and emission filter]`,\n            ] : []);\n''',
    '''            const productCode = cleanText(position?.product_code);\n            const isEmpty = Boolean(position?.is_empty);\n            const identity = isEmpty\n                ? "Empty (no filter)"\n                : productCode ? `${positionLabel} (catalogue no. ${productCode})` : positionLabel;\n            checkbox.dataset.publicationTemplate = isEmpty\n                ? "No filter was installed in {label}."\n                : "The light path included {label}.";\n            checkbox.dataset.publicationLabel = isEmpty\n                ? componentLabel\n                : componentLabel ? `${identity} in the ${componentLabel}` : identity;\n            const componentType = cleanText(position?.component_type).toLowerCase();\n            const incompletePrompt = componentType === "filter_cube"\n                ? `[PLEASE VERIFY: the recorded transmission bands for ${positionLabel} are incomplete; confirm its excitation filter, dichroic and emission filter]`\n                : `[PLEASE VERIFY: the recorded optical details for ${positionLabel} are incomplete; confirm the exact setting used]`;\n            checkbox.dataset.reviewPrompts = JSON.stringify(position?.incomplete ? [incompletePrompt] : []);\n''',
)

# One acquisition uses one route; radios remove an unnecessary invalid state.
replace(
    "assets/javascripts/methods_generator_app.js",
    '''            routeCheckbox.type = "checkbox";\n            routeCheckbox.id = `route-${routeIdx}`;\n''',
    '''            routeCheckbox.type = "radio";\n            routeCheckbox.name = "methods-optical-route";\n            routeCheckbox.id = `route-${routeIdx}`;\n''',
)

# Add method projection/binding immediately before routeViewsForInstrument().
replace(
    "assets/javascripts/methods_generator_app.js",
    '''    function routeViewsForInstrument(dto) {\n''',
    '''    function methodOptionsForInstrument(dto) {\n        const byMethod = new Map();\n        routeViewsForInstrument(dto).forEach((route) => {\n            const routeId = cleanText(route?.id);\n            const identity = route?.route_identity && typeof route.route_identity === "object"\n                ? route.route_identity : {};\n            const explicit = [\n                ...(Array.isArray(identity.imaging_modes) ? identity.imaging_modes : []),\n                ...(Array.isArray(identity.contrast_methods) ? identity.contrast_methods : []),\n            ];\n            const candidates = explicit.length ? explicit : [{\n                id: cleanText(route?.route_type),\n                display_label: cleanText(route?.route_type_label || route?.display_label),\n            }];\n            candidates.forEach((entry) => {\n                const methodId = cleanText(entry?.id || entry);\n                const displayLabel = cleanText(entry?.display_label || entry?.id || entry);\n                if (!methodId || !displayLabel || !routeId) return;\n                if (!byMethod.has(methodId)) {\n                    byMethod.set(methodId, {\n                        id: methodId, display_label: displayLabel, route_ids: [],\n                        method_sentence: `${displayLabel} imaging was performed.`,\n                    });\n                }\n                const option = byMethod.get(methodId);\n                if (!option.route_ids.includes(routeId)) option.route_ids.push(routeId);\n            });\n        });\n        return Array.from(byMethod.values());\n    }\n\n    function bindMethods(dto) {\n        const container = document.getElementById("method-list");\n        container.innerHTML = "";\n        const options = methodOptionsForInstrument(dto);\n        options.forEach((option, index) => {\n            const wrapper = document.createElement("div");\n            const input = document.createElement("input");\n            input.type = "radio";\n            input.name = "methods-imaging-method";\n            input.id = `method-${index}`;\n            input.value = option.id;\n            input.dataset.category = "method";\n            input.dataset.displayLabel = option.display_label;\n            input.dataset.methodSentence = option.method_sentence;\n            input.dataset.routeIds = JSON.stringify(option.route_ids);\n            const label = document.createElement("label");\n            label.htmlFor = input.id;\n            label.textContent = ` ${option.display_label}`;\n            wrapper.appendChild(input);\n            wrapper.appendChild(label);\n            container.appendChild(wrapper);\n        });\n        return options.length;\n    }\n\n    function routeViewsForInstrument(dto) {\n''',
)

# Legacy modality checkboxes are only a fallback for records with no explicit routes.
replace(
    "assets/javascripts/methods_generator_app.js",
    '''    function shouldUseLegacyModalities(dto) {\n        const modalities = Array.isArray(dto?.modalities) ? dto.modalities : [];\n        const caps = dto?.capabilities && typeof dto.capabilities === "object" ? dto.capabilities : {};\n        const hasCapabilities = Object.values(caps).some(v => Array.isArray(v) && v.length > 0);\n        return modalities.length > 0 && (!!dto?.retired || !hasCapabilities);\n    }\n''',
    '''    function shouldUseLegacyModalities(dto) {\n        const modalities = Array.isArray(dto?.modalities) ? dto.modalities : [];\n        return modalities.length > 0 && routeViewsForInstrument(dto).length === 0;\n    }\n''',
)

# Preserve nested filter-position selections through route-driven re-rendering and
# apply detector exclusivity from the selected route's branch contract.
replace(
    "assets/javascripts/methods_generator_app.js",
    '''    function updateHardwareVisibility(dto, preserveSelections = true) {\n        const retained = Object.fromEntries(["light", "det", "filter", "splitter"].map(prefix =>\n            [prefix, new Set(preserveSelections ? getCheckedIds(prefix) : [])]\n        ));\n''',
    '''    function updateHardwareVisibility(dto, preserveSelections = true) {\n        const retained = Object.fromEntries(["light", "det", "filter", "splitter"].map(prefix =>\n            [prefix, new Set(preserveSelections ? getCheckedIds(prefix) : [])]\n        ));\n        const retainedPositions = new Set(preserveSelections ? getCheckedIds("filterposition") : []);\n''',
)
replace(
    "assets/javascripts/methods_generator_app.js",
    '''        const allLightItems = inventoryItemsForClasses(dto, ["light_source"]);\n        const allDetItems = inventoryItemsForClasses(dto, ["endpoint", "camera_port", "eyepiece"]);\n        const allFilterItems = inventoryItemsForClasses(dto, ["optical_element"]);\n        const allSplitterItems = inventoryItemsForClasses(dto, ["splitter"]);\n        toggleSectionVisibility("section-light", bindCheckboxes("light-list", filterBySelection(allLightItems), "light", retained.light) > 0);\n        toggleSectionVisibility("section-det", bindCheckboxes("det-list", filterBySelection(allDetItems), "det", retained.det) > 0);\n        toggleSectionVisibility("section-filter", bindCheckboxes("filter-list", filterBySelection(allFilterItems), "filter", retained.filter) > 0);\n        toggleSectionVisibility("section-splitter", bindCheckboxes("splitter-list", filterBySelection(allSplitterItems), "splitter", retained.splitter) > 0);\n''',
    '''        function decorateExclusiveEndpoints(items) {\n            if (checkedRouteIds.size !== 1) return items;\n            const routeId = Array.from(checkedRouteIds)[0];\n            const route = routeViews.find(item => cleanText(item?.id) === routeId);\n            const groups = new Map();\n            (Array.isArray(route?.branch_summary?.branches) ? route.branch_summary.branches : []).forEach((branch) => {\n                if (cleanText(branch?.selection_mode).toLowerCase() !== "exclusive") return;\n                const group = cleanText(branch?.block_id) || "exclusive-branch";\n                (branch?.endpoint_inventory_ids || []).forEach(id => groups.set(cleanText(id), group));\n            });\n            return items.map(item => groups.has(cleanText(item?.id))\n                ? {...item, selection_group: groups.get(cleanText(item?.id))}\n                : item);\n        }\n\n        const allLightItems = inventoryItemsForClasses(dto, ["light_source"]);\n        const allDetItems = inventoryItemsForClasses(dto, ["endpoint", "camera_port", "eyepiece"]);\n        const allFilterItems = inventoryItemsForClasses(dto, ["optical_element"]);\n        const allSplitterItems = inventoryItemsForClasses(dto, ["splitter"]);\n        toggleSectionVisibility("section-light", bindCheckboxes("light-list", filterBySelection(allLightItems), "light", retained.light) > 0);\n        toggleSectionVisibility("section-det", bindCheckboxes("det-list", decorateExclusiveEndpoints(filterBySelection(allDetItems)), "det", retained.det) > 0);\n        toggleSectionVisibility("section-filter", bindCheckboxes("filter-list", filterBySelection(allFilterItems), "filter", retained.filter, retainedPositions) > 0);\n        toggleSectionVisibility("section-splitter", bindCheckboxes("splitter-list", filterBySelection(allSplitterItems), "splitter", retained.splitter) > 0);\n\n        const visiblePositionIds = new Set(getCheckedSelections("filterposition").map(item => item.id));\n        const droppedPositions = Array.from(retainedPositions).filter(id => !document.querySelector(\n            `input[id^="filterposition-"][value="${typeof CSS !== "undefined" && CSS.escape ? CSS.escape(id) : id}"]`));\n        const selectionStatus = document.getElementById("methods-selection-status");\n        if (selectionStatus) {\n            selectionStatus.textContent = droppedPositions.length\n                ? `${droppedPositions.length} previously selected filter position${droppedPositions.length === 1 ? " was" : "s were"} cleared because it is not available on this light path.`\n                : "";\n            selectionStatus.style.display = droppedPositions.length ? "" : "none";\n        }\n''',
)

# Instrument load: routes first, then methods; route-specific hardware stays hidden
# until the user chooses a method/light path.
replace(
    "assets/javascripts/methods_generator_app.js",
    '''        const routeCount = bindRoutes(dto);\n        toggleSectionVisibility("section-route", routeCount > 0);\n        const showLegacyModalities = shouldUseLegacyModalities(dto);\n''',
    '''        const routeCount = bindRoutes(dto);\n        const methodCount = bindMethods(dto);\n        toggleSectionVisibility("section-method", methodCount > 0);\n        toggleSectionVisibility("section-route", methodCount === 0 && routeCount > 0);\n        const showLegacyModalities = shouldUseLegacyModalities(dto);\n''',
)
replace(
    "assets/javascripts/methods_generator_app.js",
    '''        updateHardwareVisibility(dto, false);\n    });\n\n    // Container-level change listener for modality checkboxes.\n''',
    '''        updateHardwareVisibility(dto, false);\n        if (methodCount > 0) {\n            ["section-light", "section-filter", "section-splitter", "section-det"].forEach(id => {\n                const section = document.getElementById(id);\n                if (section) section.style.display = "none";\n            });\n        }\n    });\n\n    document.getElementById("method-list").addEventListener("change", (event) => {\n        if (!currentInst || event?.target?.dataset.category !== "method") return;\n        const routeIds = parseJsonArray(event.target.dataset.routeIds);\n        const allowed = new Set(routeIds);\n        const routeInputs = Array.from(document.querySelectorAll('input[id^="route-"]'));\n        routeInputs.forEach((route) => {\n            const wrapper = route.parentElement;\n            const compatible = allowed.has(route.value);\n            if (wrapper) wrapper.style.display = compatible ? "" : "none";\n            route.disabled = !compatible;\n            if (!compatible) route.checked = false;\n        });\n        toggleSectionVisibility("section-route", routeIds.length > 0);\n        if (routeIds.length === 1) {\n            const route = routeInputs.find(item => item.value === routeIds[0]);\n            if (route) route.checked = true;\n            updateHardwareVisibility(currentInst);\n        } else {\n            ["section-light", "section-filter", "section-splitter", "section-det"].forEach(id => {\n                const section = document.getElementById(id);\n                if (section) section.style.display = "none";\n            });\n        }\n    });\n\n    // Container-level change listener for modality checkboxes.\n''',
)

# Technique reporting follows the selected method first, then route/readout.
replace(
    "assets/javascripts/methods_generator_app.js",
    '''        light_sheet: reportingRecommendation(\n            "light-sheet thickness, sheet numerical aperture, and the detection/illumination objective pairing"),\n    };\n''',
    '''        light_sheet: reportingRecommendation(\n            "light-sheet thickness, sheet numerical aperture, and the detection/illumination objective pairing"),\n        tirf: reportingRecommendation(\n            "TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available"),\n        sted: reportingRecommendation(\n            "STED depletion wavelength and power at the sample, time-gating settings where used, and the phase-mask/beam-shaping configuration"),\n        sim: reportingRecommendation(\n            "SIM pattern/orientation settings and the reconstruction software/version and parameters used"),\n        smlm: reportingRecommendation(\n            "number of frames, exposure time, activation/excitation settings, localization software/version, and drift-correction method"),\n        ism: reportingRecommendation(\n            "detector/reconstruction mode and the reconstruction software/version and settings used"),\n    };\n''',
)
replace(
    "assets/javascripts/methods_generator_app.js",
    '''    function modalitySettingsPrompts(routeSelections, readoutSelections) {\n        const prompts = uniqueTexts(routeSelections.map(item => MODALITY_SETTINGS_PROMPTS[item.routeType] || ""));\n''',
    '''    function modalitySettingsPrompts(methodSelections, routeSelections, readoutSelections) {\n        const prompts = uniqueTexts([\n            ...methodSelections.map(item => MODALITY_SETTINGS_PROMPTS[cleanText(item.id).toLowerCase()] || ""),\n            ...routeSelections.map(item => MODALITY_SETTINGS_PROMPTS[item.routeType] || ""),\n        ]);\n''',
)
replace(
    "assets/javascripts/methods_generator_app.js",
    '''        const routeSelections = getCheckedSelections("route");\n        const runtime = runtimeAcquisitionFacts(dto);\n''',
    '''        const methodSelections = getCheckedSelections("method");\n        const methodLabels = uniqueTexts(methodSelections.map(item => item.displayLabel));\n        const routeSelections = getCheckedSelections("route");\n        const runtime = runtimeAcquisitionFacts(dto);\n''',
)
replace(
    "assets/javascripts/methods_generator_app.js",
    '''        const identitySentence = cleanText(methods.base_sentence);\n        // The route joins the microscope sentence rather than restating "Images were\n        // acquired using ..." a second time. A sentence that already carries an\n        // appositive ("..., an inverted microscope") needs the comma to keep reading.\n        const routeClause = routeLabels.length\n            ? `${identitySentence.includes(",") ? ", " : " "}with the ${humanJoin(routeLabels)} ${routeLabels.length === 1 ? "route" : "routes"}`\n            : "";\n        const openingSentence = routeClause && identitySentence.endsWith(".")\n            ? `${identitySentence.slice(0, -1)}${routeClause}.`\n            : identitySentence;\n\n        const readoutSelections = getCheckedSelections("readout");\n        const readoutSentences = dedupeSentences(readoutSelections.map(item => item.methodSentence));\n        const techniquePrompts = modalitySettingsPrompts(routeSelections, readoutSelections);\n''',
    '''        const identitySentence = cleanText(methods.base_sentence);\n        const routeClause = routeLabels.length\n            ? `${identitySentence.includes(",") ? ", " : " "}with the ${humanJoin(routeLabels)} ${routeLabels.length === 1 ? "route" : "routes"}`\n            : "";\n        const fallbackOpening = routeClause && identitySentence.endsWith(".")\n            ? `${identitySentence.slice(0, -1)}${routeClause}.`\n            : identitySentence;\n        const instrumentName = cleanText(dto.display_name) || cleanText(dto.id) || "microscope";\n        const openingSentence = methodLabels.length === 1\n            ? `${methodLabels[0]} imaging was performed using the ${instrumentName}.`\n            : fallbackOpening;\n\n        const readoutSelections = getCheckedSelections("readout");\n        const readoutSentences = dedupeSentences(readoutSelections.map(item => item.methodSentence));\n        const techniquePrompts = modalitySettingsPrompts(methodSelections, routeSelections, readoutSelections);\n''',
)
replace(
    "assets/javascripts/methods_generator_app.js",
    '''        const paragraphCompatModality = compatModalityText ? `(Compatibility) ${compatModalityText}` : "";\n''',
    '''        const paragraphCompatModality = compatModalityText;\n''',
)
replace(
    "assets/javascripts/methods_generator_app.js",
    '''        const selections = ["route", "readout", "modality", "module", "scanner", "obj", "light", "det", "filter", "filterposition", "splitter", "magnification-changer", "optical-modulator", "illumination-logic", "confirmed"];\n''',
    '''        const selections = ["method", "route", "readout", "modality", "module", "scanner", "obj", "light", "det", "filter", "filterposition", "splitter", "magnification-changer", "optical-modulator", "illumination-logic", "confirmed"];\n''',
)

# -----------------------------------------------------------------------------
# High-confidence authored method-to-route associations and data cleanup.
# -----------------------------------------------------------------------------
replace(
    "instruments/Abberior STED.yaml",
    '''- id: confocal_point\n  illumination_sequence:\n''',
    '''- id: confocal_point\n  imaging_modes:\n  - confocal_point\n  - sted\n  - resolft\n  illumination_sequence:\n''',
)
replace(
    "instruments/Deltavision OMX.yaml",
    '''- id: widefield_fluorescence\n  illumination_sequence:\n''',
    '''- id: widefield_fluorescence\n  imaging_modes:\n  - widefield_fluorescence\n  - tirf\n  - sim\n  - smlm\n  illumination_sequence:\n''',
)
replace(
    "instruments/ONI Nanoimager.yaml",
    '''- id: widefield_fluorescence\n  illumination_sequence:\n''',
    '''- id: widefield_fluorescence\n  imaging_modes:\n  - tirf\n  - smlm\n  illumination_sequence:\n''',
)
replace(
    "instruments/Zeiss TIRF.yaml",
    '''- id: widefield_fluorescence\n  illumination_sequence:\n''',
    '''- id: widefield_fluorescence\n  imaging_modes:\n  - widefield_fluorescence\n  - tirf\n  illumination_sequence:\n''',
)
# Widefield cube/LED path is not the STELLARIS spectral detector path.
replace(
    "instruments/Leica STELLARIS 8 FALCON FLIM.yaml",
    '''  route_type: widefield_fluorescence\n  readouts:\n  - spectral_imaging\n- id: transmitted_light\n''',
    '''  route_type: widefield_fluorescence\n  readouts: []\n- id: transmitted_light\n''',
)
# Retired SP5: retain legacy strings as notes where necessary but provide numeric
# ranges for the two Chameleon lasers whose notes explicitly give them.
replace(
    "instruments/retired/Leica TCS SP5 Multiphoton.yaml",
    '''      wavelength_nm: tunable\n      power: ''\n      role: excitation\n      path: multiphoton\n      notes: 'tunable 690-1040 nm'\n''',
    '''      tunable_min_nm: 690\n      tunable_max_nm: 1040\n      power: ''\n      role: excitation\n      path: multiphoton\n      notes: 'tunable 690-1040 nm'\n''',
    count=2,
)

print("Methods Generator stabilization patch applied.")
