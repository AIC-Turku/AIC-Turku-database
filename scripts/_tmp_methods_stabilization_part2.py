from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(path: str, old: str, new: str, count: int = 1) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if text.count(old) < count:
        raise RuntimeError(f"{path}: replacement anchor not found: {old[:100]!r}")
    target.write_text(text.replace(old, new, count), encoding="utf-8")


# Robustly detect whether a retained nested position is still rendered. Attribute
# selectors are awkward here because position ids may contain punctuation.
replace(
    "assets/javascripts/methods_generator_app.js",
    '''        const visiblePositionIds = new Set(getCheckedSelections("filterposition").map(item => item.id));
        const droppedPositions = Array.from(retainedPositions).filter(id => !document.querySelector(
            `input[id^="filterposition-"][value="${typeof CSS !== "undefined" && CSS.escape ? CSS.escape(id) : id}"]`));
''',
    '''        const renderedPositionIds = new Set(
            Array.from(document.querySelectorAll('input[id^="filterposition-"]')).map(input => input.value)
        );
        const droppedPositions = Array.from(retainedPositions).filter(id => !renderedPositionIds.has(id));
''',
)

# Method changes filter both route rows and their readout rows. Hidden readouts are
# cleared so they cannot leak into prose after the user switches methods.
replace(
    "assets/javascripts/methods_generator_app.js",
    '''        routeInputs.forEach((route) => {
            const wrapper = route.parentElement;
            const compatible = allowed.has(route.value);
            if (wrapper) wrapper.style.display = compatible ? "" : "none";
            route.disabled = !compatible;
            if (!compatible) route.checked = false;
        });
        toggleSectionVisibility("section-route", routeIds.length > 0);
''',
    '''        routeInputs.forEach((route) => {
            const wrapper = route.parentElement;
            const compatible = allowed.has(route.value);
            if (wrapper) wrapper.style.display = compatible ? "" : "none";
            route.disabled = !compatible;
            if (!compatible) route.checked = false;
        });
        document.querySelectorAll('input[id^="readout-"]').forEach((readout) => {
            const compatible = allowed.has(readout.dataset.routeId);
            if (readout.parentElement) readout.parentElement.style.display = compatible ? "" : "none";
            readout.disabled = !compatible;
            if (!compatible) readout.checked = false;
        });
        toggleSectionVisibility("section-route", routeIds.length > 0);
''',
)

# Switching the route radio must clear readouts from the previous route because the
# browser does not emit a change event for the radio it automatically unchecks.
replace(
    "assets/javascripts/methods_generator_app.js",
    '''        if (target?.dataset.category === "readout" && target.checked) {
            document.querySelectorAll('input[id^="route-"]').forEach(route => {
                if (route.value === target.dataset.routeId) route.checked = true;
            });
        } else if (target?.dataset.category === "route" && !target.checked) {
''',
    '''        if (target?.dataset.category === "route" && target.checked) {
            document.querySelectorAll('input[id^="readout-"]').forEach(readout => {
                if (readout.dataset.routeId !== target.value) readout.checked = false;
            });
        } else if (target?.dataset.category === "readout" && target.checked) {
            document.querySelectorAll('input[id^="route-"]').forEach(route => {
                if (route.value === target.dataset.routeId) route.checked = true;
            });
        } else if (target?.dataset.category === "route" && !target.checked) {
''',
)

# Natural component identity clauses: make the draft read like Methods prose, not a
# spreadsheet dump. Product codes remain included when known but are not blockers.
replace(
    "scripts/dashboard/instrument_view.py",
    '''    parts: list[str] = []
    for label, value in (
        ("Manufacturer", manufacturer),
        ("Model", model),
        ("Product code", product_code),
    ):
        cleaned = _identity_value(value)
        if not cleaned or cleaned in sentence:
            continue
        parts.append(f"{label}: {cleaned}")
    for part in extras or []:
        cleaned = clean_text(part)
        if cleaned:
            parts.append(cleaned)
    return "; ".join(parts)
''',
    '''    parts: list[str] = []
    identity = " ".join(
        value for value in (_identity_value(manufacturer), _identity_value(model))
        if value and value not in sentence
    ).strip()
    if identity:
        parts.append(identity)
    product = _identity_value(product_code)
    if product and product not in sentence:
        parts.append(product)
    for part in extras or []:
        cleaned = clean_text(part)
        if cleaned:
            parts.append(cleaned)
    return ", ".join(parts)
''',
)

# Avoid "a ASI ... piezo kit piezo stage" and similar stage grammar.
replace(
    "scripts/dashboard/instrument_view.py",
    '''        stage_name = " ".join(part for part in [manufacturer, model] if part).strip()
        method_sentence = f"Z-stacks were acquired using a {stage_name} piezo stage." if stage_name else "Z-stacks were acquired using a piezo stage."
''',
    '''        stage_name = " ".join(part for part in [manufacturer, model] if part).strip()
        if stage_name:
            descriptor = stage_name if "piezo" in stage_name.lower() else f"{stage_name} piezo stage"
            method_sentence = f"Z-stacks were acquired using {_indefinite_article(descriptor)} {descriptor}."
        else:
            method_sentence = "Z-stacks were acquired using a piezo stage."
''',
)

# Multiple acquisition-role software rows should all be available to the user, and
# non-numeric version strings should not be forced into a fake "v..." form.
replace(
    "assets/javascripts/methods_generator_app.js",
    '''        const acquisitionSoftware = (Array.isArray(dto?.software) ? dto.software : []).find((row) => {
            if (!row || typeof row !== "object") return false;
            const name = cleanText(row.name);
            return cleanText(row.role).toLowerCase() === "acquisition"
                && name
                && !placeholderValues.has(name.toLowerCase());
        });
        if (acquisitionSoftware) {
            const name = cleanText(acquisitionSoftware.name);
            const rawVersion = cleanText(acquisitionSoftware.version);
            const version = rawVersion && !placeholderValues.has(rawVersion.toLowerCase())
                ? rawVersion
                : "";
            const softwareLabel = version ? `${name} (v${version})` : name;
            const sentence = `Instrument control and image acquisition were performed using ${softwareLabel}.`;
            options.push({
                id: "action-acquisition-software",
                display_label: sentence,
                method_sentence: sentence,
                review_prompts: version
                    ? []
                    : [`[PLEASE SPECIFY: acquisition software version for ${name}]`],
            });
        } else if (!Array.isArray(dto?.software)) {
''',
    '''        const acquisitionSoftware = (Array.isArray(dto?.software) ? dto.software : []).filter((row) => {
            if (!row || typeof row !== "object") return false;
            const name = cleanText(row.name);
            return cleanText(row.role).toLowerCase() === "acquisition"
                && name
                && !placeholderValues.has(name.toLowerCase());
        });
        acquisitionSoftware.forEach((software, softwareIndex) => {
            const name = cleanText(software.name);
            const rawVersion = cleanText(software.version);
            const version = rawVersion && !placeholderValues.has(rawVersion.toLowerCase())
                ? rawVersion
                : "";
            const numericVersion = /^\\d+(?:[.\\-]\\d+)*(?:\\s|$)/.test(version);
            const softwareLabel = version
                ? `${name} (${numericVersion ? `v${version}` : `version ${version}`})`
                : name;
            const sentence = `Instrument control and image acquisition were performed using ${softwareLabel}.`;
            options.push({
                id: `action-acquisition-software-${softwareIndex}`,
                display_label: sentence,
                method_sentence: sentence,
                review_prompts: version
                    ? []
                    : [`[PLEASE SPECIFY: acquisition software version for ${name}]`],
            });
        });
        if (!acquisitionSoftware.length && !Array.isArray(dto?.software)) {
''',
)

print("Methods Generator follow-up patch applied.")
