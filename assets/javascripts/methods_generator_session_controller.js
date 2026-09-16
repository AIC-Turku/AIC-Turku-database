/**
 * Acquisition-session reliability layer for the Methods Generator.
 *
 * The core generator remains responsible for rendering one acquisition from the
 * authoritative instrument DTO. This controller owns cross-acquisition state:
 * preserving only compatible selections, replacing corrected entries, resetting
 * the form, and applying publication-safety checks to the core-generated entry.
 */
document.addEventListener("DOMContentLoaded", () => {
    const systemSelect = document.getElementById("system-select");
    const methodList = document.getElementById("method-list");
    const outputText = document.getElementById("output-text");
    const sessionLabel = document.getElementById("session-label");
    const runtimeConfirm = document.getElementById("runtime-confirm");
    const status = document.getElementById("methods-selection-status");
    const originalAdd = document.getElementById("add-btn");
    const originalClear = document.getElementById("clear-btn");
    const configNode = document.getElementById("methods-generator-config");
    if (!systemSelect || !methodList || !outputText || !originalAdd || !originalClear) return;

    let config = {};
    try { config = JSON.parse(configNode?.textContent || "{}"); } catch (_) { config = {}; }
    const outputTitle = String(config.output_title || "Light Microscopy Methods");
    const dataUrl = String(config.instrument_data_url || "../assets/instruments_data.json");
    const instrumentData = fetch(dataUrl)
        .then(response => response.ok ? response.json() : Promise.reject(new Error("instrument data unavailable")))
        .then(payload => new Map((Array.isArray(payload?.instruments) ? payload.instruments : [])
            .map(item => [String(item?.id || ""), item])))
        .catch(() => new Map());

    // Keep the core controls and their established listeners, but put session
    // semantics on user-facing clones. The controller can therefore ask the core
    // to render one acquisition without duplicating its sentence-generation code.
    originalAdd.id = "add-btn-core";
    originalAdd.style.display = "none";
    const addButton = originalAdd.cloneNode(true);
    addButton.id = "add-btn";
    addButton.style.display = "";
    originalAdd.parentNode.insertBefore(addButton, originalAdd);

    originalClear.id = "clear-btn-core";
    originalClear.style.display = "none";
    const clearButton = originalClear.cloneNode(true);
    clearButton.id = "clear-btn";
    clearButton.style.display = "";
    originalClear.parentNode.insertBefore(clearButton, originalClear);

    const mirrorDisabled = () => { addButton.disabled = originalAdd.disabled; };
    new MutationObserver(mirrorDisabled).observe(originalAdd, { attributes: true, attributeFilter: ["disabled"] });
    mirrorDisabled();

    const entries = new Map();
    let activeMethodId = "";

    function clean(value) { return typeof value === "string" ? value.trim() : ""; }
    function checked(prefix) {
        return Array.from(document.querySelectorAll(`input[id^="${prefix}-"]:checked`));
    }
    function values(prefix) { return checked(prefix).map(input => input.value); }
    function labelFor(input) {
        return clean(document.querySelector(`label[for="${CSS.escape(input.id)}"]`)?.textContent);
    }
    function unique(items) { return Array.from(new Set(items.map(clean).filter(Boolean))); }
    function reviewLine(text) { return `- ${text.replace(/\.$/, "")}`; }

    function snapshot(prefixes) {
        const result = new Map();
        prefixes.forEach(prefix => result.set(prefix, checked(prefix).map(input => input.value)));
        return result;
    }
    function restore(state) {
        state.forEach((selectedValues, prefix) => {
            selectedValues.forEach(value => {
                const input = Array.from(document.querySelectorAll(`input[id^="${prefix}-"]`))
                    .find(candidate => candidate.value === value && !candidate.disabled);
                if (input) input.checked = true;
            });
        });
    }
    function clearPrefixes(prefixes) {
        prefixes.forEach(prefix => document.querySelectorAll(`input[id^="${prefix}-"]:checked`)
            .forEach(input => { input.checked = false; }));
    }

    methodList.addEventListener("change", event => {
        const target = event.target;
        if (!(target instanceof HTMLInputElement) || target.dataset.category !== "method") return;
        const previousRoute = values("route")[0] || "";
        const routeState = snapshot(["light", "det", "filter", "filterposition", "splitter"]);
        let allowedRoutes = [];
        try { allowedRoutes = JSON.parse(target.dataset.routeIds || "[]"); } catch (_) { allowedRoutes = []; }
        const sameRoute = Boolean(previousRoute && allowedRoutes.includes(previousRoute));
        const previousMethodId = activeMethodId;
        activeMethodId = target.value;
        const changingMethod = Boolean(previousMethodId && previousMethodId !== target.value);

        setTimeout(() => {
            if (changingMethod) {
                clearPrefixes(["readout", "module", "scanner", "obj", "magnification-changer", "optical-modulator", "illumination-logic"]);
            }
            if (sameRoute) {
                restore(routeState);
                checked("light").forEach(light => {
                    const role = clean(light.dataset.role).toLowerCase();
                    const method = clean(target.value).toLowerCase();
                    if (role === "depletion" && !["sted", "resolft"].includes(method)) light.checked = false;
                    if (["activation", "switching"].includes(role) && method !== "smlm") light.checked = false;
                });
                if (changingMethod && status) {
                    status.textContent = "The physical light path is unchanged, so compatible source/filter/detector selections were kept. Objective and method-specific hardware were cleared for confirmation.";
                    status.style.display = "";
                }
            } else if (changingMethod && previousRoute && status) {
                status.textContent = "Light-path selections were cleared because the new imaging method uses a different physical path. Objective and method-specific hardware were also cleared for confirmation.";
                status.style.display = "";
            }
        }, 0);
    }, true);

    systemSelect.addEventListener("change", () => {
        setTimeout(() => {
            activeMethodId = "";
            const methodInputs = document.querySelectorAll('input[id^="method-"]');
            const routeInputs = document.querySelectorAll('input[id^="route-"]');
            if (methodInputs.length === 0 && routeInputs.length === 1) {
                routeInputs[0].checked = true;
                routeInputs[0].dispatchEvent(new Event("change", { bubbles: true }));
            }
            mirrorDisabled();
        }, 0);
    }, true);

    function extractSingleEntry(coreOutput) {
        const header = `${outputTitle}:`;
        if (!coreOutput.startsWith(header)) return null;
        let body = coreOutput.slice(header.length).trim();
        let acknowledgements = [];
        const marker = "\n\nAcknowledgements:";
        const markerIndex = body.indexOf(marker);
        if (markerIndex >= 0) {
            acknowledgements = body.slice(markerIndex + marker.length).trim().split(/\n\s*\n/).map(clean).filter(Boolean);
            body = body.slice(0, markerIndex).trim();
        }
        return body ? { body, acknowledgements } : null;
    }

    function instrumentReferenceFromBaseSentence(dto) {
        const base = clean(dto?.methods?.base_sentence);
        const prefix = "Images were acquired using ";
        if (!base.startsWith(prefix)) return "";
        return base.slice(prefix.length).replace(/\.$/, "").split(/, controlled by /i)[0].trim();
    }

    function splitReview(body) {
        const marker = "Review before publication:";
        const index = body.indexOf(marker);
        if (index < 0) return { prose: body.trim(), prompts: [] };
        return {
            prose: body.slice(0, index).trim(),
            prompts: body.slice(index + marker.length).trim().split("\n").map(clean).filter(Boolean),
        };
    }

    function unresolvedDetectorSelection() {
        return checked("det").some(input => {
            const label = labelFor(input);
            if (/\b(?:unknown|placeholder)\b/i.test(label)) return true;
            const parts = label.split(/\s+[—-]\s+/).map(clean).filter(Boolean);
            return parts.length >= 2 && parts[0].toLowerCase() === parts[1].toLowerCase();
        });
    }

    function sanitizeEntry(body, dto) {
        let { prose, prompts } = splitReview(body);
        const methodInputs = checked("method");
        const methodIds = new Set(methodInputs.map(input => clean(input.value).toLowerCase()));
        const routeInputs = checked("route");
        const lights = checked("light");
        const detectors = checked("det");
        const modules = checked("module");
        const objectives = checked("obj");

        const reference = instrumentReferenceFromBaseSentence(dto);
        if (reference) {
            prose = prose.replace(/\bwas performed using the .*? microscope\./,
                match => match.replace(/using the .*? microscope\./, `using ${reference}.`));
        }
        if (!methodIds.size && routeInputs.length === 1 && clean(routeInputs[0].dataset.routeType).toLowerCase() === "multiphoton") {
            prose = prose.replace(/^Images were acquired using .*?\./,
                `Two-photon (multiphoton) excitation imaging was performed using ${reference || "the microscope"}.`);
        }

        prose = prose.replace(/\s+other microscope\b/gi, " microscope")
            .replace(/\s+pos(?:ition)?\s+\d+\b/gi, "")
            .replace(/\s+\(position\s+[A-Z0-9_ -]+\)/g, "");
        prompts = prompts.map(line => line
            .replace(/\s+\([^)]*?\sroute\)/gi, "")
            .replace(/\s+pos(?:ition)?\s+\d+\b/gi, ""));

        if (unresolvedDetectorSelection()) {
            prose = prose.replace(/(?:^|\s)Images were recorded using [^.]+\./g, "").replace(/\s{2,}/g, " ").trim();
            prompts.push(reviewLine("[PLEASE SPECIFY: the detector/camera used for this acquisition (manufacturer and model); the facility record does not identify it]"));
        }

        prompts = prompts.filter(line => !/^\- \[PLEASE VERIFY: .* not recorded for this instrument;/i.test(line)
            && !/^\- \[PLEASE VERIFY: the instrument export reported /i.test(line));

        const moduleActsAsDetector = modules.some(input => /detector|camera|airyscan/i.test(labelFor(input)));
        if (!objectives.length) {
            prompts.push(reviewLine("[PLEASE SPECIFY: the objective used for this acquisition (magnification, numerical aperture and immersion medium)]"));
        }
        if (!lights.length) {
            prompts.push(reviewLine("[PLEASE SPECIFY: the illumination/excitation source used for this acquisition]"));
        }
        if (!detectors.length && !moduleActsAsDetector) {
            prompts.push(reviewLine("[PLEASE SPECIFY: the detector or observation path used for this acquisition]"));
        }

        const depletion = lights.some(input => clean(input.dataset.role).toLowerCase() === "depletion"
            || /depletion/i.test(labelFor(input)));
        if (methodIds.has("sted") && !depletion) {
            prompts.push(reviewLine("[PLEASE VERIFY: STED imaging was selected but no depletion source is reported; confirm the depletion beam used]"));
        }
        if (!methodIds.has("sted") && !methodIds.has("resolft") && depletion) {
            prompts.push(reviewLine("[PLEASE VERIFY: a depletion source is selected for an acquisition that is not identified as STED/RESOLFT; confirm the imaging method and source roles]"));
        }

        const nonChannelRoles = new Set(["depletion", "activation", "switching"]);
        const channelSources = lights.filter(input => !nonChannelRoles.has(clean(input.dataset.role).toLowerCase()));
        if (lights.length > 1 && channelSources.length <= 1 && detectors.length <= 1) {
            prompts = prompts.filter(line => !/whether the channels were acquired sequentially or simultaneously/i.test(line));
        }

        const detectorLabels = detectors.map(labelFor).map(label => clean(label.split(" — ")[0]));
        const detectorCounts = new Map();
        detectorLabels.forEach(label => detectorCounts.set(label, (detectorCounts.get(label) || 0) + 1));
        detectorCounts.forEach((count, label) => {
            if (count > 1 && label) {
                const pattern = new RegExp(`Images were recorded using ${label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\.`, "g");
                prose = prose.replace(pattern, `Images were recorded using ${count} × ${label}.`);
            }
        });

        checked("filter").forEach(filter => {
            const filterPositions = checked("filterposition").filter(position => clean(position.dataset.componentId) === clean(filter.value));
            if (filterPositions.length) return;
            const label = clean(filter.dataset.publicationLabel || labelFor(filter).split(" — ")[0]);
            if (!label) return;
            const pattern = new RegExp(`(?:^|\\s)The light path included ${label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\.`, "g");
            prose = prose.replace(pattern, "").replace(/\s{2,}/g, " ").trim();
        });

        const finalPrompts = unique(prompts);
        return [prose, finalPrompts.length ? `Review before publication:\n${finalPrompts.join("\n")}` : ""]
            .filter(Boolean).join("\n\n");
    }

    function scopeKey() {
        return JSON.stringify([
            systemSelect.value,
            clean(sessionLabel?.value),
            values("method"),
            values("route"),
        ]);
    }

    function render() {
        if (!entries.size) return;
        const bodies = Array.from(entries.values()).map(entry => entry.body);
        const acknowledgements = unique(Array.from(entries.values()).flatMap(entry => entry.acknowledgements));
        const sections = [`${outputTitle}:`, ...bodies];
        if (acknowledgements.length) sections.push(`Acknowledgements:\n${acknowledgements.join("\n\n")}`);
        outputText.value = sections.join("\n\n");
    }

    addButton.addEventListener("click", async () => {
        if (originalAdd.disabled) return;
        originalClear.click();
        originalAdd.click();
        const single = extractSingleEntry(outputText.value);
        if (!single) return;
        const dto = (await instrumentData).get(systemSelect.value);
        single.body = sanitizeEntry(single.body, dto);
        single.instrumentId = systemSelect.value;
        entries.set(scopeKey(), single);
        render();
    });

    clearButton.addEventListener("click", () => {
        entries.clear();
        originalClear.click();
        activeMethodId = "";
        if (sessionLabel) sessionLabel.value = "";
        if (runtimeConfirm) runtimeConfirm.checked = false;
        if (systemSelect.value) systemSelect.dispatchEvent(new Event("change"));
    });
});
