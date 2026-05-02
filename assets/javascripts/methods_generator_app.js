document.addEventListener("DOMContentLoaded", async () => {
    const configNode = document.getElementById("methods-generator-config");
    let pageConfig = {
        acknowledgements: {
            standard: "",
            xcelligence_addition: "",
        },
        output_title: "Light Microscopy Methods",
    };
    try {
        if (configNode?.textContent?.trim()) {
            pageConfig = JSON.parse(configNode.textContent);
        }
    } catch (error) {
        console.error("Failed to parse methods-generator config", error);
    }

    const acknowledgements = pageConfig?.acknowledgements || {};
    const ackStandard = String(acknowledgements.standard || "");
    const ackXcelligence = String(acknowledgements.xcelligence_addition || "");
    const outputTitle = String(pageConfig?.output_title || "Light Microscopy Methods");
    const instrumentDataUrl = String(pageConfig?.instrument_data_url || "../assets/instruments_data.json");

    const systemSelect = document.getElementById("system-select");
    const hwOptions = document.getElementById("hardware-options");
    const outputText = document.getElementById("output-text");
    const copyBtn = document.getElementById("copy-btn");
    const clearBtn = document.getElementById("clear-btn");
    const addBtn = document.getElementById("add-btn");

    const methodsMetadataWarning = document.getElementById("methods-metadata-warning");
    const methodsMetadataBlockers = document.getElementById("methods-metadata-blockers");

    let instruments = [];
    let currentInst = null;
    let accumulatedEntries = new Map();
    let usedInstruments = new Map();

    function cleanText(value) {
        return typeof value === "string" ? value.trim() : "";
    }

    function uniqueTexts(values) {
        return Array.from(new Set((Array.isArray(values) ? values : []).map(cleanText).filter(Boolean)));
    }

    function dedupeSentences(values) {
        const seen = new Set();
        return (Array.isArray(values) ? values : []).reduce((acc, value) => {
            const cleaned = cleanText(value);
            if (!cleaned) return acc;
            const key = cleaned.toLowerCase();
            if (seen.has(key)) return acc;
            seen.add(key);
            acc.push(cleaned);
            return acc;
        }, []);
    }

    function normalizeSentenceKey(value) {
        return cleanText(value)
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, " ")
            .trim();
    }

    function buildSentenceFact({ text, channel, key, specificity = 1 }) {
        const cleanedText = cleanText(text);
        const cleanedChannel = cleanText(channel) || "generic";
        const cleanedKey = normalizeSentenceKey(key || cleanedText);
        if (!cleanedText || !cleanedKey) return null;
        return {
            text: cleanedText,
            channel: cleanedChannel,
            key: cleanedKey,
            specificity: Number.isFinite(Number(specificity)) ? Number(specificity) : 1,
        };
    }

    function dedupeSentenceFacts(facts) {
        const byIdentity = new Map();
        (Array.isArray(facts) ? facts : []).forEach((fact) => {
            if (!fact || typeof fact !== "object") return;
            const normalizedFact = buildSentenceFact(fact);
            if (!normalizedFact) return;
            const identity = `${normalizedFact.channel}::${normalizedFact.key}`;
            const existing = byIdentity.get(identity);
            if (!existing || normalizedFact.specificity > existing.specificity) {
                byIdentity.set(identity, normalizedFact);
                return;
            }
            if (normalizedFact.specificity === existing.specificity && normalizedFact.text.length > existing.text.length) {
                byIdentity.set(identity, normalizedFact);
            }
        });
        return dedupeSentences(Array.from(byIdentity.values()).map((fact) => fact.text));
    }

    function humanJoin(values) {
        const items = uniqueTexts(values);
        if (!items.length) return "";
        if (items.length === 1) return items[0];
        if (items.length === 2) return `${items[0]} and ${items[1]}`;
        return `${items.slice(0, -1).join(", ")}, and ${items[items.length - 1]}`;
    }

    function showLoadError(message) {
        const finalMessage = cleanText(message) || "Failed to load instrument data.";
        currentInst = null;
        hwOptions.style.display = "none";
        addBtn.disabled = true;
        methodsMetadataWarning.style.display = "none";
        methodsMetadataBlockers.innerHTML = "";
        outputText.value = finalMessage;
    }

    function populateDropdown() {
        systemSelect.innerHTML = '<option value="">-- Choose an instrument --</option>';
        instruments.forEach(inst => {
            const opt = document.createElement("option");
            opt.value = inst.id;
            opt.textContent = inst.retired ? `${inst.display_name} (Retired)` : inst.display_name;
            systemSelect.appendChild(opt);
        });
    }

    function formatBlockerLabel(blocker) {
        return (blocker?.title || blocker?.path || "Missing field").toString().trim();
    }

    function missingMetadataNote(blockers) {
        const labels = uniqueTexts((Array.isArray(blockers) ? blockers : []).map(formatBlockerLabel));
        if (!labels.length) {
            return "Some instrument metadata is missing; ask staff to confirm the exact settings.";
        }
        return `Some instrument metadata is missing (${humanJoin(labels)}); ask staff to confirm the exact settings.`;
    }

    function getMethodsMetadataStatus(inst) {
        const metadata = inst?.methods_generation || {};
        const blockers = Array.isArray(metadata?.blockers)
            ? metadata.blockers.filter(item => item?.kind === "instrument_metadata")
            : [];

        return {
            isBlocked: Boolean(metadata?.is_blocked) && blockers.length > 0,
            blockers,
            softwareByRole: metadata?.software_by_role || {},
        };
    }

    function renderMethodsMetadataWarning(inst) {
        const status = getMethodsMetadataStatus(inst);
        methodsMetadataBlockers.innerHTML = "";

        if (!status.isBlocked) {
            methodsMetadataWarning.style.display = "none";
            return status;
        }

        status.blockers.forEach(blocker => {
            const item = document.createElement("li");
            item.textContent = formatBlockerLabel(blocker);
            methodsMetadataBlockers.appendChild(item);
        });

        methodsMetadataWarning.style.display = "block";
        return status;
    }

    function bindCheckboxes(containerId, items, prefix) {
        const container = document.getElementById(containerId);
        container.innerHTML = "";
        if (Array.isArray(container.children)) container.children = [];
        if (Array.isArray(container.options)) container.options = [];

        const normalizedItems = Array.isArray(items) ? items.filter(item => item && typeof item === 'object') : [];
        if (!normalizedItems.length) {
            return 0;
        }

        normalizedItems.forEach((item, index) => {
            const wrapper = document.createElement("div");
            wrapper.style.marginBottom = "4px";

            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.id = `${prefix}-${index}`;
            checkbox.value = item.id || `${prefix}-${index}`;
            checkbox.dataset.displayLabel = item.display_label || "";
            checkbox.dataset.methodSentence = item.method_sentence || "";
            checkbox.dataset.category = prefix;
            checkbox.dataset.role = item.role || "";

            const label = document.createElement("label");
            label.htmlFor = checkbox.id;

            const mainText = document.createElement("span");
            mainText.textContent = " " + (item.display_label || "Unnamed item");
            label.appendChild(mainText);

            const inlineDetail = cleanText(item.display_subtitle);
            if (inlineDetail) {
                const noteSpan = document.createElement("span");
                noteSpan.textContent = ` — ${inlineDetail}`;
                noteSpan.style.fontSize = "0.85em";
                noteSpan.style.color = "var(--md-default-fg-color--light)";
                label.appendChild(noteSpan);
            }

            wrapper.appendChild(checkbox);
            wrapper.appendChild(label);
            container.appendChild(wrapper);
        });
        return normalizedItems.length;
    }

    function toggleSectionVisibility(sectionId, hasItems) {
        const section = document.getElementById(sectionId);
        if (!section) return;
        section.style.display = hasItems ? "" : "none";
    }

    /**
     * Bind canonical route checkboxes (with nested readout checkboxes) from
     * authoritative_route_contract.routes into the given container.
     *
     * Route checkboxes use prefix "route-" and value = route.id.
     * Readout checkboxes use prefix "readout-{routeIndex}-" and
     * value = "{routeId}:{readoutId}", with dataset.routeId and
     * dataset.routeDisplayLabel for sentence generation.
     *
     * Returns the number of route checkboxes rendered.
     */
    function bindRoutes(dto) {
        const container = document.getElementById("route-list");
        container.innerHTML = "";
        if (Array.isArray(container.children)) container.children = [];
        if (Array.isArray(container.options)) container.options = [];

        const routeViews = routeViewsForInstrument(dto);
        let routeCheckboxCount = 0;

        routeViews.forEach((route, routeIdx) => {
            const routeId = cleanText(route.id);
            const routeLabel = cleanText(route.display_label || route.id);
            if (!routeId) return;

            // Route checkbox
            const routeWrapper = document.createElement("div");
            routeWrapper.style.marginBottom = "4px";

            const routeCheckbox = document.createElement("input");
            routeCheckbox.type = "checkbox";
            routeCheckbox.id = `route-${routeIdx}`;
            routeCheckbox.value = routeId;
            routeCheckbox.dataset.displayLabel = routeLabel;
            routeCheckbox.dataset.methodSentence = `Images were acquired using the ${routeLabel} route.`;
            routeCheckbox.dataset.category = "route";

            const routeLabelEl = document.createElement("label");
            routeLabelEl.htmlFor = routeCheckbox.id;
            const routeLabelText = document.createElement("span");
            routeLabelText.textContent = ` ${routeLabel}`;
            routeLabelEl.appendChild(routeLabelText);

            routeWrapper.appendChild(routeCheckbox);
            routeWrapper.appendChild(routeLabelEl);
            container.appendChild(routeWrapper);
            routeCheckboxCount++;

            // Nested readout checkboxes
            const routeIdentity = route.route_identity && typeof route.route_identity === "object"
                ? route.route_identity
                : {};
            const readouts = Array.isArray(routeIdentity.readouts) ? routeIdentity.readouts : [];
            readouts.forEach((readout, readoutIdx) => {
                const readoutId = cleanText(
                    (readout && typeof readout === "object" ? readout.id : readout) || ""
                );
                const readoutLabel = cleanText(
                    (readout && typeof readout === "object"
                        ? (readout.display_label || readout.id)
                        : readout) || ""
                );
                if (!readoutId) return;

                const readoutWrapper = document.createElement("div");
                readoutWrapper.style.marginBottom = "2px";
                readoutWrapper.style.marginLeft = "20px";

                const readoutCheckbox = document.createElement("input");
                readoutCheckbox.type = "checkbox";
                readoutCheckbox.id = `readout-${routeIdx}-${readoutIdx}`;
                readoutCheckbox.value = `${routeId}:${readoutId}`;
                readoutCheckbox.dataset.displayLabel = readoutLabel;
                readoutCheckbox.dataset.routeId = routeId;
                readoutCheckbox.dataset.routeDisplayLabel = routeLabel;
                readoutCheckbox.dataset.methodSentence =
                    `${readoutLabel} readout was acquired using the ${routeLabel} route.`;
                readoutCheckbox.dataset.category = "readout";

                const readoutLabelEl = document.createElement("label");
                readoutLabelEl.htmlFor = readoutCheckbox.id;
                const readoutLabelText = document.createElement("span");
                readoutLabelText.textContent = ` ${readoutLabel}`;
                readoutLabelEl.appendChild(readoutLabelText);

                readoutWrapper.appendChild(readoutCheckbox);
                readoutWrapper.appendChild(readoutLabelEl);
                container.appendChild(readoutWrapper);
            });
        });

        return routeCheckboxCount;
    }

    function routeViewsForInstrument(dto) {
        return Array.isArray(dto?.hardware?.optical_path?.authoritative_route_contract?.routes)
            ? dto.hardware.optical_path.authoritative_route_contract.routes
            : [];
    }

    function opticalPathInventory(dto) {
        return Array.isArray(dto?.hardware?.optical_path?.hardware_inventory_renderables)
            ? dto.hardware.optical_path.hardware_inventory_renderables
            : [];
    }

    function inventoryItemsForClasses(dto, classes) {
        const wanted = new Set((Array.isArray(classes) ? classes : []).map(cleanText).filter(Boolean));
        return opticalPathInventory(dto).filter(item => wanted.has(cleanText(item?.inventory_class)));
    }

    function updateHardwareVisibility(dto) {
        // Route selection is authoritative; fall back to legacy modality filter only
        // when no route checkboxes are checked.
        const checkedRouteIds = new Set(getCheckedIds("route"));
        const checkedModalityIds = checkedRouteIds.size === 0
            ? new Set(getCheckedIds("modality"))
            : new Set();
        const routeViews = routeViewsForInstrument(dto);

        // Collect hardware IDs from routes that match the checked routes/modalities.
        // When nothing is checked, include hardware from ALL routes.
        const matchingRouteHardwareIds = new Set();
        routeViews
            .filter(rv => {
                if (checkedRouteIds.size === 0 && checkedModalityIds.size === 0) return true;
                if (checkedRouteIds.has(cleanText(rv.id))) return true;
                // Legacy modality fallback: illumination_mode or id match
                return checkedModalityIds.has(cleanText(rv.illumination_mode)) ||
                    checkedModalityIds.has(cleanText(rv.id));
            })
            .forEach(rv => {
                ["sources", "filters", "splitters", "endpoints"].forEach(key => {
                    (rv.relevant_hardware?.[key] || []).forEach(item => {
                        const id = cleanText(item?.id);
                        if (id) matchingRouteHardwareIds.add(id);
                    });
                });
            });

        // Filter inventory renderables by:
        //   1. The item belongs to a matching route, OR
        //   2. (Legacy) The item's own modalities array declares a checked modality.
        // When nothing is checked, return all items unfiltered.
        function filterBySelection(items) {
            if (checkedRouteIds.size === 0 && checkedModalityIds.size === 0) return items;
            return items.filter(item => {
                const id = cleanText(item?.id);
                if (matchingRouteHardwareIds.has(id)) return true;
                return Array.isArray(item?.modalities) && item.modalities.some(m => checkedModalityIds.has(cleanText(m)));
            });
        }

        const allLightItems = inventoryItemsForClasses(dto, ["light_source"]);
        const allDetItems = inventoryItemsForClasses(dto, ["endpoint", "camera_port", "eyepiece"]);
        const allFilterItems = inventoryItemsForClasses(dto, ["optical_element"]);
        const allSplitterItems = inventoryItemsForClasses(dto, ["splitter"]);
        toggleSectionVisibility("section-light", bindCheckboxes("light-list", filterBySelection(allLightItems), "light") > 0);
        toggleSectionVisibility("section-det", bindCheckboxes("det-list", filterBySelection(allDetItems), "det") > 0);
        toggleSectionVisibility("section-filter", bindCheckboxes("filter-list", filterBySelection(allFilterItems), "filter") > 0);
        toggleSectionVisibility("section-splitter", bindCheckboxes("splitter-list", filterBySelection(allSplitterItems), "splitter") > 0);
    }

    function getCheckedSelections(prefix) {
        return Array.from(document.querySelectorAll(`input[id^="${prefix}-"]:checked`)).map(cb => ({
            id: cb.value,
            displayLabel: cleanText(cb.dataset.displayLabel),
            methodSentence: cleanText(cb.dataset.methodSentence),
            role: cleanText(cb.dataset.role),
        }));
    }

    function getCheckedIds(prefix) {
        return getCheckedSelections(prefix).map(item => item.id).sort();
    }

    function groupedLabelSentence(prefix, selections) {
        const labels = uniqueTexts(selections.map(item => item.displayLabel));
        if (!labels.length) {
            return dedupeSentences(selections.map(item => item.methodSentence)).join(" ");
        }

        if (prefix === "route") {
            return labels.length === 1
                ? `Images were acquired using the ${labels[0]} route.`
                : `Images were acquired using the ${humanJoin(labels)} routes.`;
        }
        if (prefix === "readout") {
            // Each readout has its own route-aware method_sentence; use it directly.
            return dedupeSentences(selections.map(item => item.methodSentence)).join(" ");
        }
        if (prefix === "modality") {
            return labels.length === 1
                ? `Imaging modality used was ${labels[0]}.`
                : `Imaging modalities used included ${humanJoin(labels)}.`;
        }
        if (prefix === "module") {
            const moduleSentences = dedupeSentences(selections.map(item => item.methodSentence));
            return moduleSentences.length
                ? moduleSentences.join(" ")
                : labels.length === 1
                    ? `Installed module used was ${labels[0]}.`
                    : `Installed modules used included ${humanJoin(labels)}.`;
        }
        if (prefix === "scanner") {
            return dedupeSentences(selections.map(item => item.methodSentence)).join(" ");
        }
        if (prefix === "obj") {
            return dedupeSentences(selections.map(item => item.methodSentence)).join(" ");
        }
        if (prefix === "det") {
            return dedupeSentences(selections.map(item => item.methodSentence)).join(" ");
        }
        if (prefix === "light") {
            return dedupeSentences(selections.map(item => item.methodSentence)).join(" ");
        }
        if (prefix === "magnification-changer") {
            return dedupeSentences(selections.map(item => item.methodSentence)).join(" ");
        }
        if (prefix === "filter") {
            return dedupeSentences(selections.map(item => item.methodSentence)).join(" ");
        }
        return dedupeSentences(selections.map(item => item.methodSentence)).join(" ");
    }

    function selectionChannel(prefix) {
        if (prefix === "light") return "source";
        if (prefix === "filter") return "optical_element";
        if (prefix === "det") return "endpoint";
        if (prefix === "splitter") return "splitter";
        if (prefix === "optical-modulator") return "modulator";
        if (prefix === "illumination-logic") return "illumination_logic";
        return "generic";
    }

    function sentenceFactsFromSelections(prefix, selections, specificity = 1) {
        const channel = selectionChannel(prefix);
        return (Array.isArray(selections) ? selections : [])
            .map((item) => buildSentenceFact({
                text: item?.methodSentence,
                channel,
                key: item?.displayLabel || item?.id,
                specificity,
            }))
            .filter(Boolean);
    }

    function getExportedRuntimeSelectedConfiguration(dto) {
        const candidate = dto?.runtime_selected_configuration;
        return candidate && typeof candidate === "object" ? candidate : null;
    }

    function getRuntimeSelectedConfigurationFromLocalStorage() {
        if (typeof window === "undefined" || !window.localStorage) return null;
        try {
            const raw = window.localStorage.getItem("aic.virtualMicroscope.selectedConfiguration");
            if (!raw) return null;
            const parsed = JSON.parse(raw);
            return parsed && typeof parsed === "object" ? parsed : null;
        } catch (error) {
            return null;
        }
    }

    function runtimeConfigurationMatchesInstrument(dto, runtimeConfig) {
        if (!dto || !runtimeConfig || typeof runtimeConfig !== "object") return false;
        const scopeId = cleanText(runtimeConfig.scope_id);
        const instrumentId = cleanText(runtimeConfig.instrument_id);
        const dtoId = cleanText(dto.id);
        if (scopeId && dtoId && scopeId === dtoId) return true;
        if (instrumentId && dtoId && instrumentId === dtoId) return true;
        return false;
    }

    function resolveRuntimeSelectedConfiguration(dto) {
        const exported = getExportedRuntimeSelectedConfiguration(dto);
        // Exported runtime selection is authoritative for this page. Browser
        // localStorage is legacy fallback when no exported runtime config exists.
        if (exported) {
            return { source: "exported_dto", config: exported };
        }
        const localStorageFallback = getRuntimeSelectedConfigurationFromLocalStorage();
        if (localStorageFallback && runtimeConfigurationMatchesInstrument(dto, localStorageFallback)) {
            return { source: "local_storage", config: localStorageFallback };
        }
        return { source: "", config: null };
    }

    function routeFactsSummarySentence(routeFacts) {
        if (!routeFacts || typeof routeFacts !== "object") return "";
        const factsByKey = [
            "selected_or_selectable_sources",
            "selected_or_selectable_excitation_filters",
            "selected_or_selectable_dichroics",
            "selected_or_selectable_emission_filters",
            "selected_or_selectable_splitters",
            "selected_or_selectable_endpoints",
            "selected_or_selectable_modulators",
            "selected_or_selectable_branch_selectors",
        ];
        const allRows = factsByKey.flatMap((key) => Array.isArray(routeFacts[key]) ? routeFacts[key] : []);
        if (!allRows.length) return "";

        const lineForRow = (row) => {
            if (!row || typeof row !== "object") return "";
            const label = cleanText(row.display_label || row.label || row.name || row.id || row.component_type);
            const position = cleanText(row.selected_position_key || row.position_key || row.selected_position_id || row.position_id);

            const channel = cleanText(row.channel_label || row.channel_name);
            const caveats = [];
            if (row._cube_incomplete) caveats.push("incomplete cube");
            if (row._unsupported_spectral_model) caveats.push("unsupported spectral model");

            const availablePositions = Array.isArray(row.available_positions)
                ? row.available_positions
                    .map((pos) => cleanText(pos?.display_label || pos?.label || pos?.position_key || pos?.position_id))
                    .filter(Boolean)
                : [];
            const selectableText = availablePositions.length ? `selectable positions: ${humanJoin(availablePositions)}` : "";

            const cubeBits = [
                row.excitation_filter ? `EX ${cleanText(row.excitation_filter.display_label || row.excitation_filter.label || row.excitation_filter.component_type || "filter")}` : "",
                row.dichroic ? `DI ${cleanText(row.dichroic.display_label || row.dichroic.label || row.dichroic.component_type || "dichroic")}` : "",
                row.emission_filter ? `EM ${cleanText(row.emission_filter.display_label || row.emission_filter.label || row.emission_filter.component_type || "filter")}` : "",
            ].filter(Boolean);
            const productCode = cleanText(row.product_code);

            const details = [
                channel ? `channel ${channel}` : "",
                cubeBits.length ? `cube internals (${cubeBits.join("; ")})` : "",
                productCode ? `product code ${productCode}` : "",
                selectableText,
                caveats.length ? `caveats: ${humanJoin(caveats)}` : "",
            ].filter(Boolean);

            const base = label ? `${label}${position ? ` @ ${position}` : ""}` : "";
            return [base, ...details].filter(Boolean).join(" — ");
        };

        const lines = dedupeSentences(allRows.map(lineForRow));
        return lines.length ? `Route-specific optical selections/facts: ${humanJoin(lines)}.` : "";
    }

    function findRouteFactsForRuntimeRoute(dto, routeNameOrId) {
        const routeViews = routeViewsForInstrument(dto);
        const target = cleanText(routeNameOrId);
        if (!target) return null;
        return routeViews.find((route) =>
            cleanText(route?.id) === target ||
            cleanText(route?.illumination_mode) === target ||
            cleanText(route?.display_label) === target
        ) || null;
    }

    function runtimeConfigurationSentence(dto) {
        const resolved = resolveRuntimeSelectedConfiguration(dto);
        const runtimeConfig = resolved.config;
        if (!runtimeConfig) return { text: "", sentenceFacts: [], hasRuntimeSelection: false };

        const route = cleanText(runtimeConfig.route) || "unspecified route";
        const matchedRoute = findRouteFactsForRuntimeRoute(dto, route);
        const routeFacts = matchedRoute?.route_optical_facts || null;
        const sourceLabels = uniqueTexts((Array.isArray(runtimeConfig.sources) ? runtimeConfig.sources : []).map((source) => {
            const label = cleanText(source?.display_label || source?.name || source?.id);
            const wavelength = source?.wavelength_nm;
            return label ? `${label}${Number.isFinite(Number(wavelength)) ? ` (${Number(wavelength)} nm)` : ""}` : "";
        }));
        const runtimeSourceKeys = uniqueTexts((Array.isArray(runtimeConfig.sources) ? runtimeConfig.sources : []).map((source) =>
            cleanText(source?.display_label || source?.name || source?.id)
        ));
        const routeSteps = Array.isArray(runtimeConfig.selected_route_steps) ? runtimeConfig.selected_route_steps : [];
        const opticalSteps = routeSteps.filter((step) => step?.kind === "optical_component");
        const runtimeOpticalKeys = uniqueTexts(opticalSteps.map((step) =>
            cleanText(step?.display_label || step?.position_label || step?.component_type)
        ));
        const stageSelections = uniqueTexts(opticalSteps.map((step) => {
            const label = cleanText(step?.display_label || step?.position_label || step?.component_type);
            const position = cleanText(step?.position_key) || cleanText(step?.position_id) || "";
            return label ? `${label}${position ? ` @ ${position}` : ""}` : "";
        }));
        const splitterSelections = uniqueTexts((Array.isArray(runtimeConfig.splitters) ? runtimeConfig.splitters : []).map((splitter) => {
            const label = cleanText(splitter?.display_label || splitter?.id);
            const branches = Array.isArray(splitter?.selected_branch_ids) ? splitter.selected_branch_ids.filter(Boolean) : [];
            return label ? `${label}${branches.length ? ` [${branches.join(", ")}]` : ""}` : "";
        }));
        const runtimeSplitterKeys = uniqueTexts((Array.isArray(runtimeConfig.splitters) ? runtimeConfig.splitters : []).map((splitter) =>
            cleanText(splitter?.display_label || splitter?.id)
        ));
        const detectorSelections = uniqueTexts((Array.isArray(runtimeConfig.detectors) ? runtimeConfig.detectors : []).map((detector) => {
            const label = cleanText(detector?.display_label || detector?.id);
            const hasWindow = Number.isFinite(Number(detector?.collection_min_nm)) && Number.isFinite(Number(detector?.collection_max_nm));
            return label ? `${label}${hasWindow ? ` (${Number(detector.collection_min_nm)}–${Number(detector.collection_max_nm)} nm)` : ""}` : "";
        }));
        const runtimeEndpointKeys = uniqueTexts((Array.isArray(runtimeConfig.detectors) ? runtimeConfig.detectors : []).map((detector) =>
            cleanText(detector?.display_label || detector?.id)
        ));
        const flattenedIncomplete = routeSteps.filter((step) => step?._cube_incomplete).map((step) => cleanText(step?.display_label || step?.position_label || step?.component_type)).filter(Boolean);
        const unsupportedComponents = routeSteps.filter((step) => step?._unsupported_spectral_model).map((step) => cleanText(step?.display_label || step?.position_label || step?.component_type)).filter(Boolean);
        const unsupportedReasons = routeSteps
            .map((step) => cleanText(step?.unsupported_reason || ""))
            .filter(Boolean);

        const acquisitionPlan = runtimeConfig.acquisition_plan && typeof runtimeConfig.acquisition_plan === "object"
            ? runtimeConfig.acquisition_plan
            : null;
        let acquisitionSentence = "";
        if (acquisitionPlan?.requiresSequentialAcquisition) {
            const steps = Array.isArray(acquisitionPlan.steps) ? acquisitionPlan.steps : [];
            const stepSummary = steps
                .map((step) => {
                    const stepNo = step?.step != null ? step.step : "?";
                    const fluor = cleanText(step?.fluorophoreName) || "fluorophore";
                    const stepRoute = cleanText(step?.route) || "current route";
                    return `step ${stepNo} (${fluor}, route ${stepRoute})`;
                })
                .filter(Boolean);
            acquisitionSentence = `Sequential acquisition is planned as ${humanJoin(stepSummary)}.`;
        }

        const notes = [];
        if (flattenedIncomplete.length) notes.push(`Flattened/incomplete optics were present for ${humanJoin(flattenedIncomplete)}.`);
        if (unsupportedComponents.length || unsupportedReasons.length) {
            notes.push(`Unsupported spectral model flags were present (${humanJoin([...unsupportedComponents, ...unsupportedReasons])}).`);
        }

        const summarySentence = `Exact runtime-selected configuration (${resolved.source === "exported_dto" ? "exported DTO" : "browser fallback"}) used route ${route}.`;
        const routeFactsSentence = routeFactsSummarySentence(routeFacts);
        const sourceSentence = sourceLabels.length ? `Selected sources: ${humanJoin(sourceLabels)}.` : "";
        const opticalSentence = stageSelections.length ? `Selected wheel/turret positions: ${humanJoin(stageSelections)}.` : "";
        const splitterSentence = splitterSelections.length ? `Selected splitter branches: ${humanJoin(splitterSelections)}.` : "";
        const endpointSentence = detectorSelections.length ? `Selected endpoints/detectors: ${humanJoin(detectorSelections)}.` : "";
        const noteSentences = dedupeSentences([acquisitionSentence, ...notes]);

        const sentenceFacts = dedupeSentenceFacts([
            buildSentenceFact({ text: sourceSentence, channel: "source", key: sourceLabels.join("|"), specificity: 3 }),
            buildSentenceFact({ text: opticalSentence, channel: "optical_element", key: stageSelections.join("|"), specificity: 3 }),
            buildSentenceFact({ text: splitterSentence, channel: "splitter", key: splitterSelections.join("|"), specificity: 3 }),
            buildSentenceFact({ text: endpointSentence, channel: "endpoint", key: detectorSelections.join("|"), specificity: 3 }),
            buildSentenceFact({ text: summarySentence, channel: "runtime_selection", key: route, specificity: 3 }),
            buildSentenceFact({ text: routeFactsSentence, channel: "route_summary", key: route, specificity: 3 }),
            ...noteSentences.map((text, idx) => buildSentenceFact({ text, channel: "runtime_note", key: `${route}-${idx}`, specificity: 3 })),
        ].filter(Boolean));

        return {
            text: sentenceFacts.join(" "),
            sentenceFacts: [
                ...runtimeSourceKeys.map((label) => buildSentenceFact({ text: sourceSentence, channel: "source", key: label, specificity: 3 })),
                ...runtimeOpticalKeys.map((label) => buildSentenceFact({ text: opticalSentence, channel: "optical_element", key: label, specificity: 3 })),
                ...runtimeSplitterKeys.map((label) => buildSentenceFact({ text: splitterSentence, channel: "splitter", key: label, specificity: 3 })),
                ...runtimeEndpointKeys.map((label) => buildSentenceFact({ text: endpointSentence, channel: "endpoint", key: label, specificity: 3 })),
                buildSentenceFact({ text: summarySentence, channel: "runtime_selection", key: route, specificity: 3 }),
                buildSentenceFact({ text: routeFactsSentence, channel: "route_summary", key: route, specificity: 3 }),
                ...noteSentences.map((text, idx) => buildSentenceFact({ text, channel: "runtime_note", key: `${route}-${idx}`, specificity: 3 })),
            ].filter(Boolean),
            hasRuntimeSelection: true,
        };
    }

    function instrumentTriggersXcelligence(nameOrId) {
        const normalized = cleanText(nameOrId).toLowerCase();
        return ["xcelligence", "rtca esight"].some(token => normalized.includes(token));
    }

    function updateOutputText() {
        if (accumulatedEntries.size === 0) {
            outputText.value = 'Please select an instrument and click "Add to Methods".';
            return;
        }

        const blocks = Array.from(accumulatedEntries.values()).map(entry => entry.text).filter(Boolean);
        let finalOutput = `${outputTitle}:\n\n${blocks.join("\n\n")}`;

        const acknowledgementParts = [ackStandard];
        const usedXcell = Array.from(usedInstruments.entries()).some(([instrumentId, displayName]) => {
            return instrumentTriggersXcelligence(instrumentId) || instrumentTriggersXcelligence(displayName);
        });
        if (usedXcell) acknowledgementParts.push(ackXcelligence);

        const filteredAcknowledgements = acknowledgementParts.map(cleanText).filter(Boolean);
        if (filteredAcknowledgements.length) {
            finalOutput += `\n\nAcknowledgements:\n\n${filteredAcknowledgements.join(" ")}`;
        }

        outputText.value = finalOutput;
    }

    async function loadInstruments() {
        try {
            const instrumentsResponse = await fetch(instrumentDataUrl, {
                headers: { Accept: "application/json" },
            });
            if (!instrumentsResponse.ok) {
                throw new Error(`HTTP ${instrumentsResponse.status}`);
            }
            const instrumentsPayload = await instrumentsResponse.json();
            instruments = Array.isArray(instrumentsPayload)
                ? instrumentsPayload
                : (instrumentsPayload?.instruments || []);
            if (!Array.isArray(instruments) || instruments.length === 0) {
                throw new Error("The instruments export did not contain any instruments.");
            }
            populateDropdown();
            addBtn.disabled = false;
            systemSelect.disabled = false;
            updateOutputText();
        } catch (error) {
            console.error("Failed to load methods-generator instrument data", error);
            showLoadError(`Failed to load instrument data for the Methods Generator from ${instrumentDataUrl}: ${error.message}. Please rebuild the dashboard and verify the configured JSON export exists and contains valid JSON.`);
        }
    }

    systemSelect.addEventListener("change", (e) => {
        const instId = e.target.value;
        currentInst = instruments.find(i => i.id === instId);

        if (!currentInst) {
            hwOptions.style.display = "none";
            methodsMetadataWarning.style.display = "none";
            methodsMetadataBlockers.innerHTML = "";
            return;
        }

        hwOptions.style.display = "block";
        renderMethodsMetadataWarning(currentInst);

        const dto = currentInst;

        const routeCount = bindRoutes(dto);
        toggleSectionVisibility("section-route", routeCount > 0);
        const modalityCount = bindCheckboxes("modality-list", dto.modalities || [], "modality");
        toggleSectionVisibility("section-modality", modalityCount > 0);
        toggleSectionVisibility("section-module", bindCheckboxes("module-list", dto.modules || [], "module") > 0);
        toggleSectionVisibility("section-scanner", bindCheckboxes("scanner-list", dto.hardware?.scanner?.present ? [dto.hardware.scanner] : [], "scanner") > 0);
        toggleSectionVisibility("section-obj", bindCheckboxes("obj-list", dto.hardware?.objectives || [], "obj") > 0);
        toggleSectionVisibility("section-magnification-changer", bindCheckboxes("magnification-changer-list", dto.hardware?.magnification_changers || [], "magnification-changer") > 0);
        toggleSectionVisibility("section-optical-modulator", bindCheckboxes("optical-modulator-list", dto.hardware?.optical_modulators || [], "optical-modulator") > 0);
        toggleSectionVisibility("section-illumination-logic", bindCheckboxes("illumination-logic-list", dto.hardware?.illumination_logic || [], "illumination-logic") > 0);
        updateHardwareVisibility(dto);
    });

    // Container-level change listener for modality checkboxes. Registered once at
    // initialization so it survives instrument switches; reads currentInst at call time.
    document.getElementById("modality-list").addEventListener("change", () => {
        if (currentInst) updateHardwareVisibility(currentInst);
    });

    // Container-level change listener for route/readout checkboxes. Route selection
    // is authoritative; modality filter only activates when no route is checked.
    document.getElementById("route-list").addEventListener("change", () => {
        if (currentInst) updateHardwareVisibility(currentInst);
    });

    addBtn.addEventListener("click", () => {
        if (!currentInst) return;

        const dto = currentInst;
        const methodsMetadataStatus = getMethodsMetadataStatus(currentInst);
        if (methodsMetadataStatus.isBlocked) {
            renderMethodsMetadataWarning(currentInst);
        }

        const groupedSelections = {
            route: groupedLabelSentence("route", getCheckedSelections("route")),
            readout: groupedLabelSentence("readout", getCheckedSelections("readout")),
            modality: groupedLabelSentence("modality", getCheckedSelections("modality")),
            module: groupedLabelSentence("module", getCheckedSelections("module")),
            scanner: groupedLabelSentence("scanner", getCheckedSelections("scanner")),
            objective: groupedLabelSentence("obj", getCheckedSelections("obj")),
            magnificationChanger: groupedLabelSentence("magnification-changer", getCheckedSelections("magnification-changer")),
        };

        const specialistSelections = dedupeSentences([
            ...getCheckedSelections("optical-modulator").map(item => item.methodSentence),
            ...getCheckedSelections("illumination-logic").map(item => item.methodSentence),
        ]);

        const paragraphHardware = dedupeSentences([
            dto.methods?.base_sentence,
            groupedSelections.route,
            groupedSelections.readout,
            groupedSelections.modality,
            groupedSelections.module,
            groupedSelections.scanner,
            groupedSelections.objective,
            groupedSelections.magnificationChanger,
            dto.methods?.environment_sentence,
            ...(dto.methods?.stage_sentences || []),
            dto.methods?.autofocus_sentence,
            dto.methods?.triggering_sentence,
        ]).join(" ");

        const runtimeDetails = runtimeConfigurationSentence(dto);

        const genericOpticalFacts = [
            ...sentenceFactsFromSelections("light", getCheckedSelections("light"), runtimeDetails.hasRuntimeSelection ? 1 : 2),
            ...sentenceFactsFromSelections("det", getCheckedSelections("det"), runtimeDetails.hasRuntimeSelection ? 1 : 2),
            ...sentenceFactsFromSelections("filter", getCheckedSelections("filter"), runtimeDetails.hasRuntimeSelection ? 1 : 2),
            ...sentenceFactsFromSelections("splitter", getCheckedSelections("splitter"), runtimeDetails.hasRuntimeSelection ? 1 : 2),
        ];
        const combinedOpticalSentences = dedupeSentenceFacts([
            ...genericOpticalFacts,
            ...(runtimeDetails.sentenceFacts || []),
            ...specialistSelections.map((text, idx) => buildSentenceFact({ text, channel: "specialist", key: `specialist-${idx}`, specificity: 2 })),
            buildSentenceFact({
                text: dto.methods?.quarep_light_path_recommendation_needed ? dto.methods?.quarep_light_path_recommendation : "",
                channel: "route_summary",
                key: "quarep-recommendation",
                specificity: 0,
            }),
        ]);

        const paragraphLightPath = combinedOpticalSentences.join(" ");

        const paragraphAcquisition = dedupeSentences([
            ...(dto.methods?.processing_sentences || []),
            dto.methods?.specimen_preparation_recommendation,
            dto.methods?.acquisition_settings_recommendation,
            dto.methods?.nyquist_recommendation,
        ]).join(" ");

        const paragraphDeposition = cleanText(dto.methods?.data_deposition_recommendation);
        const paragraphMissingMetadata = methodsMetadataStatus.isBlocked
            ? missingMetadataNote(methodsMetadataStatus.blockers)
            : "";

        const textParts = [
            paragraphHardware,
            paragraphLightPath,
            paragraphAcquisition,
            paragraphDeposition,
            paragraphMissingMetadata,
        ].map(cleanText).filter(Boolean);

        accumulatedEntries.set(dto.id, {
            instrumentId: dto.id,
            text: textParts.join("\n\n"),
        });
        usedInstruments.set(dto.id, dto.display_name || dto.id);
        updateOutputText();
    });

    clearBtn.addEventListener("click", () => {
        accumulatedEntries = new Map();
        usedInstruments = new Map();
        updateOutputText();
    });

    copyBtn.addEventListener("click", () => {
        if (accumulatedEntries.size === 0) return;
        navigator.clipboard.writeText(outputText.value);
        const feedback = document.getElementById("copy-feedback");
        feedback.style.display = "inline";
        setTimeout(() => feedback.style.display = "none", 2000);
    });

    addBtn.disabled = true;
    systemSelect.disabled = true;
    await loadInstruments();
});
