document.addEventListener("DOMContentLoaded", async () => {
    const configNode = document.getElementById("methods-generator-config");
    let pageConfig = {
        acknowledgements: {
            standard: "",
            additional: [],
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
    // Conditional acknowledgements are bound to recorded instrument IDs by
    // facility.yaml. The frontend never decides which instrument a credit
    // belongs to by reading its name.
    const ackAdditional = (Array.isArray(acknowledgements.additional) ? acknowledgements.additional : [])
        .map(entry => ({
            text: String(entry?.text || ""),
            instrumentIds: new Set(
                (Array.isArray(entry?.instrument_ids) ? entry.instrument_ids : []).map(value => String(value)),
            ),
        }))
        .filter(entry => entry.text && entry.instrumentIds.size);
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
    let runtimeCandidate = { source: "", config: null };
    const runtimeConfirm = document.getElementById("runtime-confirm");

    function optionalNumber(value) {
        if (typeof value !== "number" && typeof value !== "string") return null;
        if (typeof value === "string" && !value.trim()) return null;
        const numeric = Number(value);
        return Number.isFinite(numeric) ? numeric : null;
    }

    function confirmedActionOptions(dto) {
        const methods = dto.methods || {};
        return dedupeSentences([
            // The record documents the software installed now. That is an
            // acquisition-time claim, so it is offered for confirmation rather than
            // asserted automatically.
            methods.acquisition_software_sentence,
            methods.environment_sentence,
            ...(methods.stage_sentences || []),
            methods.autofocus_sentence,
            methods.triggering_sentence,
            ...(methods.processing_sentences || []),
        ]).map((text, index) => ({
            id: `action-${index}`, display_label: text, method_sentence: text,
        }));
    }

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

    function metadataFragmentsForItem(item) {
        const manufacturer = cleanText(item?.manufacturer);
        return manufacturer ? [manufacturer] : [];
    }

    function bindCheckboxes(containerId, items, prefix, selectedIds = new Set()) {
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
            checkbox.checked = selectedIds.has(checkbox.value);
            checkbox.dataset.displayLabel = item.display_label || "";
            checkbox.dataset.methodSentence = item.method_sentence || "";
            checkbox.dataset.category = prefix;
            checkbox.dataset.role = item.role || "";
            // Publication prose is assembled from these structured fields rather
            // than by rewriting the finished sentence, so components that share a
            // sentence frame can be merged without parsing prose.
            checkbox.dataset.publicationTemplate = item.publication_template || "";
            checkbox.dataset.publicationLabel = item.publication_phrase || item.publication_label || item.display_label || "";
            checkbox.dataset.reviewPrompts = JSON.stringify(Array.isArray(item.review_prompts) ? item.review_prompts : []);

            const label = document.createElement("label");
            label.htmlFor = checkbox.id;

            const mainText = document.createElement("span");
            mainText.textContent = " " + (item.display_label || "Unnamed item");
            label.appendChild(mainText);

            const metadataFragments = metadataFragmentsForItem(item);
            if (metadataFragments.length) {
                const noteSpan = document.createElement("span");
                noteSpan.textContent = ` — ${metadataFragments.join(" — ")}`;
                noteSpan.style.fontSize = "0.85em";
                noteSpan.style.color = "var(--md-default-fg-color--light)";
                label.appendChild(noteSpan);
            }

            wrapper.appendChild(checkbox);
            wrapper.appendChild(label);
            container.appendChild(wrapper);
            bindSelectablePositions(container, item, prefix, index);
        });
        return normalizedItems.length;
    }

    /**
     * Offer the positions a filter turret or wheel can be set to.
     *
     * Ticking the holder only says light passed through it, which tells a reader
     * nothing about the filter that was used - the fact a fluorescence Methods
     * section turns on. The positions are recorded per route, so they are offered
     * as nested choices and the holder is ticked automatically when one is picked.
     */
    function bindSelectablePositions(container, item, prefix, itemIndex) {
        const positions = Array.isArray(item?.selectable_positions) ? item.selectable_positions : [];
        if (!positions.length) return;
        const componentId = cleanText(item.id);
        const componentLabel = cleanText(item.publication_label || item.display_label);

        positions.forEach((position, positionIndex) => {
            const positionId = cleanText(position?.id);
            const positionLabel = cleanText(position?.display_label);
            if (!positionId || !positionLabel) return;

            const wrapper = document.createElement("div");
            wrapper.style.marginBottom = "2px";
            wrapper.style.marginLeft = "20px";

            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.id = `${prefix}position-${itemIndex}-${positionIndex}`;
            checkbox.value = `${componentId}::${positionId}`;
            checkbox.dataset.category = `${prefix}-position`;
            checkbox.dataset.componentId = componentId;
            checkbox.dataset.componentLabel = componentLabel;
            checkbox.dataset.displayLabel = positionLabel;
            checkbox.dataset.incomplete = position?.incomplete ? "1" : "";
            const productCode = cleanText(position?.product_code);
            const identity = productCode ? `${positionLabel} (catalogue no. ${productCode})` : positionLabel;
            checkbox.dataset.publicationTemplate = "The light path included {label}.";
            checkbox.dataset.publicationLabel = componentLabel
                ? `${identity} in the ${componentLabel}`
                : identity;
            checkbox.dataset.reviewPrompts = JSON.stringify(position?.incomplete ? [
                `[PLEASE VERIFY: the recorded transmission bands for ${positionLabel} are incomplete; confirm its excitation filter, dichroic and emission filter]`,
            ] : []);

            const label = document.createElement("label");
            label.htmlFor = checkbox.id;
            const labelText = document.createElement("span");
            labelText.textContent = ` ${identity}`;
            label.appendChild(labelText);

            wrapper.appendChild(checkbox);
            wrapper.appendChild(label);
            container.appendChild(wrapper);
        });
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
            const routeLabel = cleanText(route.display_label);
            // A route with no display label would be named by its internal id in
            // publication prose, so it is not offered as a choice at all.
            if (!routeId || !routeLabel) return;

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


    function shouldUseLegacyModalities(dto) {
        const modalities = Array.isArray(dto?.modalities) ? dto.modalities : [];
        const caps = dto?.capabilities && typeof dto.capabilities === "object" ? dto.capabilities : {};
        const hasCapabilities = Object.values(caps).some(v => Array.isArray(v) && v.length > 0);
        return modalities.length > 0 && (!!dto?.retired || !hasCapabilities);
    }

    function updateHardwareVisibility(dto, preserveSelections = true) {
        const retained = Object.fromEntries(["light", "det", "filter", "splitter"].map(prefix =>
            [prefix, new Set(preserveSelections ? getCheckedIds(prefix) : [])]
        ));
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
        toggleSectionVisibility("section-light", bindCheckboxes("light-list", filterBySelection(allLightItems), "light", retained.light) > 0);
        toggleSectionVisibility("section-det", bindCheckboxes("det-list", filterBySelection(allDetItems), "det", retained.det) > 0);
        toggleSectionVisibility("section-filter", bindCheckboxes("filter-list", filterBySelection(allFilterItems), "filter", retained.filter) > 0);
        toggleSectionVisibility("section-splitter", bindCheckboxes("splitter-list", filterBySelection(allSplitterItems), "splitter", retained.splitter) > 0);
    }

    function getCheckedSelections(prefix) {
        return Array.from(document.querySelectorAll(`input[id^="${prefix}-"]:checked`)).map(cb => ({
            id: cb.value,
            displayLabel: cleanText(cb.dataset.displayLabel),
            methodSentence: cleanText(cb.dataset.methodSentence),
            role: cleanText(cb.dataset.role),
            publicationTemplate: cleanText(cb.dataset.publicationTemplate),
            publicationLabel: cleanText(cb.dataset.publicationLabel),
            reviewPrompts: parseJsonArray(cb.dataset.reviewPrompts),
        }));
    }

    function parseJsonArray(value) {
        try {
            const parsed = JSON.parse(value || "[]");
            return Array.isArray(parsed) ? parsed.map(cleanText).filter(Boolean) : [];
        } catch (error) {
            return [];
        }
    }

    /**
     * Merge selections that share a sentence frame into one sentence.
     *
     * Each selection carries its own frame ("Excitation was provided by {label}.")
     * and its own label, so three lasers become one sentence instead of three
     * near-identical ones, without any sentence being parsed or rewritten.
     *
     * Selections are keyed by id, so two distinct components that happen to share a
     * display label stay two facts; when the draft cannot tell them apart it says so
     * rather than silently reporting one.
     */
    function mergeByPublicationTemplate(selections) {
        const groups = new Map();
        const seenIds = new Set();
        const prompts = [];

        (Array.isArray(selections) ? selections : []).forEach((item) => {
            const id = cleanText(item?.id);
            if (id && seenIds.has(id)) return;
            if (id) seenIds.add(id);
            prompts.push(...(item?.reviewPrompts || []));

            const template = cleanText(item?.publicationTemplate);
            const label = cleanText(item?.publicationLabel) || cleanText(item?.displayLabel);
            if (!template || !template.includes("{label}") || !label) {
                const fallback = cleanText(item?.methodSentence);
                if (fallback) groups.set(`literal::${fallback}`, { literal: fallback });
                return;
            }
            if (!groups.has(template)) groups.set(template, { template, labels: [] });
            groups.get(template).labels.push(label);
        });

        const sentences = [];
        groups.forEach((group) => {
            if (group.literal) {
                sentences.push(group.literal);
                return;
            }
            const counts = new Map();
            group.labels.forEach(label => counts.set(label, (counts.get(label) || 0) + 1));
            counts.forEach((count, label) => {
                if (count > 1) {
                    prompts.push(`[PLEASE SPECIFY: ${count} separate components recorded as “${label}” were selected and this draft cannot tell them apart; state which one was used for each channel]`);
                }
            });
            sentences.push(group.template.replace("{label}", humanJoin(Array.from(counts.keys()))));
        });

        return { sentences: dedupeSentences(sentences), prompts: uniqueTexts(prompts) };
    }

    function getCheckedIds(prefix) {
        return getCheckedSelections(prefix).map(item => item.id).sort();
    }

    /**
     * Sentence for the legacy modality compatibility list.
     *
     * Every other category now renders through `mergeByPublicationTemplate`, which
     * merges by sentence frame instead of restating the frame per checkbox.
     */
    function groupedLabelSentence(prefix, selections) {
        const labels = uniqueTexts(selections.map(item => item.displayLabel));
        if (!labels.length) {
            return dedupeSentences(selections.map(item => item.methodSentence)).join(" ");
        }
        if (prefix === "modality") {
            return labels.length === 1
                ? `Imaging modality used was ${labels[0]}.`
                : `Imaging modalities used included ${humanJoin(labels)}.`;
        }
        return dedupeSentences(selections.map(item => item.methodSentence)).join(" ");
    }

    function getExportedRuntimeSelectedConfiguration(dto) {
        const candidate = dto?.runtime_selected_configuration;
        return candidate && typeof candidate === "object" ? candidate : null;
    }

    function getRuntimeSelectedConfigurationFromLocalStorage() {
        try {
            if (typeof window === "undefined" || !window.localStorage) return null;
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
        const identifiers = [scopeId, instrumentId].filter(Boolean);
        return Boolean(dtoId) && identifiers.length > 0 && identifiers.every(id => id === dtoId);
    }

    function availableRuntimeSelectedConfiguration(dto) {
        const exported = getExportedRuntimeSelectedConfiguration(dto);
        // Prefer the DTO as a proposal, never as evidence of an acquisition. A
        // configuration that carries no instrument identity cannot be attributed to
        // this microscope, so it is refused here exactly as it is on the
        // localStorage path below; absence of identity is not permission.
        if (exported) {
            if (!runtimeConfigurationMatchesInstrument(dto, exported)) {
                return { source: "", config: null };
            }
            return { source: "exported_dto", config: exported };
        }
        const localStorageFallback = getRuntimeSelectedConfigurationFromLocalStorage();
        if (localStorageFallback && runtimeConfigurationMatchesInstrument(dto, localStorageFallback)) {
            return { source: "local_storage", config: localStorageFallback };
        }
        return { source: "", config: null };
    }

    function renderRuntimeReview(dto) {
        runtimeCandidate = availableRuntimeSelectedConfiguration(dto);
        const candidate = runtimeCandidate.config;
        const invalid = candidate && (candidate.validSelection === false || candidate.simulationError === true);
        // A plan naming a route this instrument no longer records cannot be checked
        // against anything, so it must not become a Methods claim. Stale plans and
        // renamed routes both land here.
        const routeName = cleanText(candidate?.route);
        const unknownRoute = Boolean(candidate) && !invalid && !findRouteFactsForRuntimeRoute(dto, routeName);

        runtimeConfirm.checked = false;
        runtimeConfirm.disabled = !candidate || invalid || unknownRoute;
        document.getElementById("runtime-review").style.display = candidate ? "" : "none";
        document.getElementById("runtime-preview").textContent = candidate ? JSON.stringify(candidate, null, 2) : "";
        document.getElementById("runtime-review-status").textContent = invalid
            ? "This simulator plan is invalid and cannot be imported."
            : unknownRoute
                ? `This simulator plan refers to ${routeName || "an unnamed route"}, which is not present in the instrument's recorded routes. It cannot be imported into publication Methods; verify the configuration in the simulator or with facility staff.`
                : "This is a planning record, not an acquisition record. Review it and confirm that these settings were actually used. Missing validation or historical information remains unverified.";
    }

    /**
     * Report whether a DTO carries enough structure to build a draft from.
     *
     * The export is read with optional chaining throughout, so a record that lost
     * its `methods` block to a schema change used to produce an empty but
     * apparently successful entry - and still credited that instrument in the
     * acknowledgements. Missing structure is now refused, not rendered.
     */
    function instrumentDtoIsRenderable(dto) {
        return Boolean(dto) && Boolean(cleanText(dto?.methods?.base_sentence));
    }

    function exportDiagnosticNotes(dto) {
        return uniqueTexts((Array.isArray(dto?.diagnostics) ? dto.diagnostics : [])
            .filter(entry => entry && typeof entry === "object")
            .map(entry => cleanText(entry.message) || cleanText(entry.code)));
    }

    function resolveRuntimeSelectedConfiguration(dto) {
        // Use the reviewed snapshot, not a fresh localStorage read after confirmation.
        if (!runtimeConfirm.checked || runtimeConfirm.disabled || dto !== currentInst) {
            return { source: "", config: null };
        }
        return runtimeCandidate;
    }

    /**
     * Resolve the route a runtime plan names against this instrument's contract.
     *
     * Plans store the route id, but older plans and hand-written records may carry
     * the display label instead, so the id is tried first and the label only as a
     * fallback: a label must never shadow a different route's id.
     */
    function findRouteFactsForRuntimeRoute(dto, routeNameOrId) {
        const routeViews = routeViewsForInstrument(dto);
        const target = cleanText(routeNameOrId);
        if (!target) return null;
        return routeViews.find(route => cleanText(route?.id) === target)
            || routeViews.find(route => cleanText(route?.illumination_mode) === target)
            || routeViews.find(route => cleanText(route?.display_label) === target)
            || null;
    }

    /**
     * Index every recorded component of this instrument by each identifier a
     * runtime plan might name it with.
     *
     * A confirmed simulator plan is a planning record, not an inventory. Matching
     * its components against the canonical record is what lets the draft (a) use
     * the instrument's own publication label and recorded role, and (b) refuse to
     * report hardware that is no longer part of the instrument.
     */
    function inventoryIndex(dto) {
        const index = new Map();
        opticalPathInventory(dto).forEach((item) => {
            [
                item?.id,
                item?.hardware_id,
                item?.display_label,
                item?.canonical_display_label,
                item?.publication_label,
            ].map(cleanText).filter(Boolean).forEach((key) => {
                const normalized = key.toLowerCase();
                if (!index.has(normalized)) index.set(normalized, item);
            });
        });
        return index;
    }

    function matchRecordedComponent(index, ...candidates) {
        for (const candidate of candidates) {
            const key = cleanText(candidate).toLowerCase();
            if (key && index.has(key)) return index.get(key);
        }
        return null;
    }

    function unrecordedComponentPrompt(label) {
        return `[PLEASE VERIFY: the reviewed plan names “${label}”, which is not in the current instrument record; confirm the component that was actually used]`;
    }

    function withWavelength(label, wavelength) {
        if (wavelength === null || !(wavelength > 0)) return label;
        return label.includes(`${wavelength} nm`) ? label : `${label} (${wavelength} nm)`;
    }

    function branchLabelLookup(route) {
        const lookup = new Map();
        const branches = Array.isArray(route?.branch_summary?.branches) ? route.branch_summary.branches : [];
        branches.forEach((branch) => {
            const id = cleanText(branch?.branch_id);
            const label = cleanText(branch?.label);
            if (id && label) lookup.set(id, label);
        });
        return lookup;
    }

    /**
     * Build publication prose and review requests from a confirmed runtime plan.
     *
     * Everything here is rendered from the plan's structured fields. Nothing is
     * emitted as an intermediate diagnostic sentence for a later pass to rewrite,
     * so no transformation can merge two facts or leave a clause unterminated.
     */
    function runtimeAcquisitionFacts(dto) {
        const empty = { components: [], sentences: [], prompts: [], routeLabels: [], hasRuntimeSelection: false };
        const resolved = resolveRuntimeSelectedConfiguration(dto);
        const runtimeConfig = resolved.config;
        if (!runtimeConfig) return empty;

        const matchedRoute = findRouteFactsForRuntimeRoute(dto, cleanText(runtimeConfig.route));
        // renderRuntimeReview refuses to enable confirmation for a plan whose route
        // is not in this instrument's route contract, so an unresolved route here
        // means the plan must not contribute at all.
        if (!matchedRoute) return empty;

        const index = inventoryIndex(dto);
        const prompts = [];
        const components = [];
        // Only a recorded display label may name a route in prose; an internal id
        // is not a route name, so an unlabelled route is reported as a gap instead.
        const routeLabel = cleanText(matchedRoute.display_label);

        function addFact(template, label, recorded, planLabel) {
            if (!template || !label) return;
            components.push({
                id: cleanText(recorded?.id) || `plan::${planLabel}`,
                publicationTemplate: template,
                publicationLabel: label,
                reviewPrompts: [],
            });
        }

        (Array.isArray(runtimeConfig.sources) ? runtimeConfig.sources : []).forEach((source) => {
            const planLabel = cleanText(source?.display_label || source?.name || source?.id);
            if (!planLabel) return;
            const recorded = matchRecordedComponent(index, source?.id, source?.mechanismId, planLabel);
            if (!recorded) prompts.push(unrecordedComponentPrompt(planLabel));
            const label = cleanText(recorded?.publication_label) || planLabel;
            const wavelength = optionalNumber(source?.selected_wavelength_nm ?? source?.wavelength_nm);
            // The role comes from the instrument record, never from the plan: a plan
            // knows which source was switched on, not what it was used for.
            const template = cleanText(recorded?.publication_template) || "Illumination was provided by {label}.";
            (recorded?.review_prompts || []).forEach(prompt => prompts.push(cleanText(prompt)));
            addFact(template, withWavelength(label, wavelength), recorded, planLabel);
        });

        (Array.isArray(runtimeConfig.detectors) ? runtimeConfig.detectors : []).forEach((detector) => {
            const planLabel = cleanText(detector?.display_label || detector?.id);
            if (!planLabel) return;
            const recorded = matchRecordedComponent(index, detector?.id, detector?.mechanismId, planLabel);
            if (!recorded) prompts.push(unrecordedComponentPrompt(planLabel));
            const label = cleanText(recorded?.publication_label) || planLabel;
            const minimum = optionalNumber(detector?.collection_min_nm);
            const maximum = optionalNumber(detector?.collection_max_nm);
            const hasWindow = minimum !== null && maximum !== null && minimum > 0 && maximum > minimum;
            const template = cleanText(recorded?.publication_template) || "Images were recorded using {label}.";
            addFact(template, hasWindow ? `${label} (detection ${minimum}–${maximum} nm)` : label, recorded, planLabel);
        });

        const routeSteps = Array.isArray(runtimeConfig.selected_route_steps) ? runtimeConfig.selected_route_steps : [];
        routeSteps.filter(step => step?.kind === "optical_component").forEach((step) => {
            const planLabel = cleanText(step?.display_label || step?.position_label || step?.component_type);
            if (!planLabel) return;
            const recorded = matchRecordedComponent(index, step?.component_id, planLabel);
            const label = cleanText(recorded?.publication_label) || planLabel;
            const position = cleanText(step?.position_label) || cleanText(step?.position_key) || cleanText(step?.position_id);
            const template = cleanText(recorded?.publication_template) || "The light path included {label}.";
            addFact(template, position ? `${label} (position ${position})` : label, recorded, planLabel);
            if (step?._cube_incomplete) {
                prompts.push(`[PLEASE VERIFY: the recorded optical configuration is incomplete for ${label}; confirm the exact excitation filter, dichroic and emission filter used]`);
            }
            if (step?._unsupported_spectral_model || cleanText(step?.unsupported_reason)) {
                prompts.push(`[PLEASE VERIFY: the recorded spectral information for ${label} could not be interpreted; confirm its transmission bands]`);
            }
        });

        const branchLabels = branchLabelLookup(matchedRoute);
        (Array.isArray(runtimeConfig.splitters) ? runtimeConfig.splitters : []).forEach((splitter) => {
            const planLabel = cleanText(splitter?.display_label || splitter?.id);
            if (!planLabel) return;
            const recorded = matchRecordedComponent(index, splitter?.id, splitter?.mechanismId, planLabel);
            if (!recorded) prompts.push(unrecordedComponentPrompt(planLabel));
            const label = cleanText(recorded?.publication_label) || planLabel;
            const rawBranches = Array.isArray(splitter?.selected_branch_ids) ? splitter.selected_branch_ids.filter(Boolean) : [];
            const named = rawBranches.map(id => branchLabels.get(cleanText(id)) || "").filter(Boolean);
            if (rawBranches.length && named.length !== rawBranches.length) {
                prompts.push(`[PLEASE SPECIFY: which output of ${label} was recorded; the reviewed plan identifies its branches only by internal reference]`);
            }
            const template = cleanText(recorded?.publication_template) || "The emission light was divided by {label}.";
            addFact(template, named.length ? `${label} (${humanJoin(named)} outputs)` : label, recorded, planLabel);
        });

        const sentences = [];
        const acquisitionPlan = runtimeConfig.acquisition_plan && typeof runtimeConfig.acquisition_plan === "object"
            ? runtimeConfig.acquisition_plan
            : null;
        // `requiresSequentialAcquisition` is the simulator's conclusion about what
        // the chosen fluorophores and optics would need, not a record of what was
        // done: an operator may have accepted crosstalk and imaged simultaneously.
        // It is therefore a question for the author, never a claim about execution.
        if (acquisitionPlan?.requiresSequentialAcquisition) {
            const steps = Array.isArray(acquisitionPlan.steps) ? acquisitionPlan.steps : [];
            const labels = uniqueTexts(steps.map(step => cleanText(step?.fluorophoreName)));
            prompts.push(labels.length > 1
                ? `[PLEASE SPECIFY: the reviewed plan indicates that ${humanJoin(labels)} require sequential acquisition; state whether the channels were acquired sequentially or simultaneously, and in what order]`
                : "[PLEASE SPECIFY: the reviewed plan indicates that the channels require sequential acquisition; state whether they were acquired sequentially or simultaneously, and in what order]");
        }

        if (!routeLabel) {
            prompts.push("[PLEASE SPECIFY: the optical route used; the reviewed plan names a route that has no recorded name]");
        }

        return {
            components,
            sentences: dedupeSentences(sentences),
            prompts: uniqueTexts(prompts),
            routeLabels: routeLabel ? [routeLabel] : [],
            hasRuntimeSelection: true,
        };
    }

    function updateOutputText() {
        if (accumulatedEntries.size === 0) {
            outputText.value = 'Select an instrument, then choose “Add to methods”.';
            return;
        }

        const blocks = Array.from(accumulatedEntries.values()).map(entry => entry.text).filter(Boolean);
        let finalOutput = `${outputTitle}:\n\n${blocks.join("\n\n")}`;

        const usedInstrumentIds = new Set(Array.from(usedInstruments.keys()).map(value => String(value)));
        const acknowledgementParts = [
            ackStandard,
            ...ackAdditional
                .filter(entry => Array.from(entry.instrumentIds).some(id => usedInstrumentIds.has(id)))
                .map(entry => entry.text),
        ];

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
        renderRuntimeReview(currentInst);
        toggleSectionVisibility("section-confirmed", bindCheckboxes("confirmed-list", confirmedActionOptions(currentInst), "confirmed") > 0);

        const dto = currentInst;

        const routeCount = bindRoutes(dto);
        toggleSectionVisibility("section-route", routeCount > 0);
        const showLegacyModalities = shouldUseLegacyModalities(dto);
        const modalityCount = bindCheckboxes("modality-list", showLegacyModalities ? (dto.modalities || []) : [], "modality");
        toggleSectionVisibility("section-modality", modalityCount > 0);
        toggleSectionVisibility("section-module", bindCheckboxes("module-list", dto.modules || [], "module") > 0);
        toggleSectionVisibility("section-scanner", bindCheckboxes("scanner-list", dto.hardware?.scanner?.present ? [dto.hardware.scanner] : [], "scanner") > 0);
        toggleSectionVisibility("section-obj", bindCheckboxes("obj-list", dto.hardware?.objectives || [], "obj") > 0);
        toggleSectionVisibility("section-magnification-changer", bindCheckboxes("magnification-changer-list", dto.hardware?.magnification_changers || [], "magnification-changer") > 0);
        toggleSectionVisibility("section-optical-modulator", bindCheckboxes("optical-modulator-list", dto.hardware?.optical_modulators || [], "optical-modulator") > 0);
        toggleSectionVisibility("section-illumination-logic", bindCheckboxes("illumination-logic-list", dto.hardware?.illumination_logic || [], "illumination-logic") > 0);
        updateHardwareVisibility(dto, false);
    });

    // Container-level change listener for modality checkboxes. Registered once at
    // initialization so it survives instrument switches; reads currentInst at call time.
    document.getElementById("modality-list").addEventListener("change", () => {
        if (currentInst) updateHardwareVisibility(currentInst);
    });

    // Container-level change listener for route/readout checkboxes. Route selection
    // is authoritative; modality filter only activates when no route is checked.
    document.getElementById("route-list").addEventListener("change", (event) => {
        const target = event?.target;
        if (target?.dataset.category === "readout" && target.checked) {
            document.querySelectorAll('input[id^="route-"]').forEach(route => {
                if (route.value === target.dataset.routeId) route.checked = true;
            });
        } else if (target?.dataset.category === "route" && !target.checked) {
            document.querySelectorAll('input[id^="readout-"]').forEach(readout => {
                if (readout.dataset.routeId === target.value) readout.checked = false;
            });
        }
        if (currentInst) updateHardwareVisibility(currentInst);
    });

    // Picking a position means the holder was in the path; clearing the holder
    // clears the positions under it, mirroring the route/readout pairing.
    document.getElementById("filter-list").addEventListener("change", (event) => {
        const target = event?.target;
        if (target?.dataset.category === "filter-position" && target.checked) {
            document.querySelectorAll('input[id^="filter-"]').forEach((filter) => {
                if (filter.value === target.dataset.componentId) filter.checked = true;
            });
        } else if (target?.dataset.category === "filter" && !target.checked) {
            document.querySelectorAll('input[id^="filterposition-"]').forEach((position) => {
                if (position.dataset.componentId === target.value) position.checked = false;
            });
        }
    });

    hwOptions.addEventListener("change", event => {
        if (event.target === runtimeConfirm || !runtimeConfirm.checked) return;
        // Changing the selection invalidates the reviewed plan, which is the safe
        // behaviour, but it used to happen silently: a user who confirmed first and
        // picked hardware afterwards lost the import without being told.
        runtimeConfirm.checked = false;
        document.getElementById("runtime-review-status").textContent =
            "Your selection changed, so the Virtual Microscope plan is no longer included. Review it again and re-confirm it if those were the settings used.";
    });

    /**
     * Assemble one acquisition entry: finished prose, then the review block.
     *
     * Publication prose is built from the structured selections and, when the user
     * has confirmed one, the runtime plan. Review requests are collected from the
     * places that produce them, not recovered from the finished text, so a
     * component whose own name contains brackets is never mistaken for a request
     * and no request can be corrupted by a later rewrite.
     */
    function buildAcquisitionEntry(dto) {
        const prompts = [];
        const methods = dto.methods || {};

        const routeSelections = getCheckedSelections("route");
        const runtime = runtimeAcquisitionFacts(dto);
        const routeLabels = uniqueTexts([
            ...routeSelections.map(item => item.displayLabel),
            ...runtime.routeLabels,
        ]);

        // A single acquisition travels one optical route. Claiming several without
        // comment would read as though they were used together.
        if (routeLabels.length > 1) {
            prompts.push(`[PLEASE VERIFY: ${routeLabels.length} optical routes are reported for a single acquisition (${humanJoin(routeLabels)}); confirm that each was used, or add a separate entry per route]`);
        }

        const identitySentence = cleanText(methods.base_sentence);
        // The route joins the microscope sentence rather than restating "Images were
        // acquired using ..." a second time. A sentence that already carries an
        // appositive ("..., an inverted microscope") needs the comma to keep reading.
        const routeClause = routeLabels.length
            ? `${identitySentence.includes(",") ? ", " : " "}with the ${humanJoin(routeLabels)} ${routeLabels.length === 1 ? "route" : "routes"}`
            : "";
        const openingSentence = routeClause && identitySentence.endsWith(".")
            ? `${identitySentence.slice(0, -1)}${routeClause}.`
            : identitySentence;

        const readoutSentences = dedupeSentences(getCheckedSelections("readout").map(item => item.methodSentence));
        const objectives = mergeByPublicationTemplate(getCheckedSelections("obj"));
        prompts.push(...objectives.prompts);

        const otherHardware = dedupeSentences([
            ...getCheckedSelections("module").map(item => item.methodSentence),
            ...getCheckedSelections("scanner").map(item => item.methodSentence),
            ...getCheckedSelections("magnification-changer").map(item => item.methodSentence),
            ...getCheckedSelections("confirmed").map(item => item.methodSentence),
        ]);

        const paragraphHardware = dedupeSentences([
            openingSentence,
            ...readoutSentences,
            ...objectives.sentences,
            ...otherHardware,
        ]).join(" ");

        // Manual selections and confirmed plan components are merged in one pass,
        // keyed by component id, so a component the user ticked and the plan also
        // names is stated once - using the plan's reading, which carries the
        // wavelength, filter position or detection window the checkbox cannot.
        // A named position supersedes its holder: "the CYR71010 cube in the Filter
        // Turret" is the fact, "the Filter Turret" only the container.
        const positionSelections = getCheckedSelections("filterposition");
        const resolvedComponentIds = new Set(positionSelections.map(item => cleanText(item.id).split("::")[0]));
        const lightPathSelections = [
            ...getCheckedSelections("light"),
            ...positionSelections,
            ...getCheckedSelections("filter").filter(item => !resolvedComponentIds.has(cleanText(item.id))),
            ...getCheckedSelections("splitter"),
            ...getCheckedSelections("det"),
        ];
        const lightPath = mergeByPublicationTemplate([...runtime.components, ...lightPathSelections]);
        prompts.push(...lightPath.prompts, ...runtime.prompts);

        const specialistSentences = dedupeSentences([
            ...getCheckedSelections("optical-modulator").map(item => item.methodSentence),
            ...getCheckedSelections("illumination-logic").map(item => item.methodSentence),
        ]);

        const paragraphLightPath = dedupeSentences([
            ...lightPath.sentences,
            ...runtime.sentences,
            ...specialistSentences,
        ]).join(" ");

        // More than one illumination line or detector leaves the reader unable to
        // tell simultaneous from sequential acquisition, which changes how
        // bleed-through and phototoxicity are judged.
        const channelCount = getCheckedSelections("light").length;
        const detectorCount = getCheckedSelections("det").length;
        if (channelCount > 1 || detectorCount > 1) {
            prompts.push("[PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]");
        }

        prompts.push(cleanText(methods.retired_review_prompt));
        // Ask about the selectors whose position is still unknown, not about the
        // ones the user has just named.
        const unresolvedOptics = (Array.isArray(methods.unresolved_optics) ? methods.unresolved_optics : [])
            .filter(entry => entry && !resolvedComponentIds.has(cleanText(entry.inventory_id)));
        if (Array.isArray(methods.unresolved_optics) && methods.unresolved_optics.length) {
            if (unresolvedOptics.length) {
                prompts.push(`[PLEASE SPECIFY: which position of ${humanJoin(unresolvedOptics.map(entry => cleanText(entry.scoped_label)))} was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalog number)]`);
            }
        } else if (methods.quarep_light_path_recommendation_needed) {
            prompts.push(cleanText(methods.quarep_light_path_recommendation));
        }
        prompts.push(cleanText(methods.specimen_preparation_recommendation));
        prompts.push(cleanText(methods.acquisition_settings_recommendation));

        const methodsMetadataStatus = getMethodsMetadataStatus(dto);
        if (methodsMetadataStatus.isBlocked) {
            const labels = uniqueTexts(methodsMetadataStatus.blockers.map(formatBlockerLabel));
            prompts.push(labels.length
                ? `[PLEASE VERIFY: ${humanJoin(labels)} ${labels.length === 1 ? "is" : "are"} not recorded for this instrument; confirm the exact values with facility staff]`
                : "[PLEASE VERIFY: some instrument metadata is not recorded; confirm the exact values with facility staff]");
        }
        exportDiagnosticNotes(dto).forEach((note) => {
            prompts.push(`[PLEASE VERIFY: the instrument export reported "${note}"; confirm the affected details with facility staff]`);
        });

        const compatModalityText = shouldUseLegacyModalities(dto)
            ? cleanText(groupedLabelSentence("modality", getCheckedSelections("modality")))
            : "";
        const paragraphCompatModality = compatModalityText ? `(Compatibility) ${compatModalityText}` : "";

        const reviewPrompts = uniqueTexts(prompts.map(prompt => cleanText(prompt).replace(/\.$/, "")));
        const reviewBlock = reviewPrompts.length
            ? `Review before publication:\n${reviewPrompts.map(prompt => `- ${prompt}`).join("\n")}`
            : "";

        return [
            paragraphHardware,
            paragraphLightPath,
            paragraphCompatModality,
            reviewBlock,
        ].map(cleanText).filter(Boolean);
    }

    addBtn.addEventListener("click", () => {
        if (!currentInst) return;

        const dto = currentInst;
        if (!instrumentDtoIsRenderable(dto)) {
            outputText.value = `The record for ${cleanText(dto.display_name) || cleanText(dto.id) || "this instrument"} is incomplete, so a Methods draft cannot be generated from it. Ask facility staff to complete the instrument record.`;
            return;
        }
        renderMethodsMetadataWarning(dto);

        const textParts = buildAcquisitionEntry(dto);
        const sessionLabel = cleanText(document.getElementById("session-label").value);
        const text = [sessionLabel, ...textParts].filter(Boolean).join("\n\n");
        // An unchanged second click is idempotent; a different acquisition is not
        // allowed to replace an earlier entry just because it used the same scope.
        const selections = ["route", "readout", "modality", "module", "scanner", "obj", "light", "det", "filter", "filterposition", "splitter", "magnification-changer", "optical-modulator", "illumination-logic", "confirmed"];
        const signature = JSON.stringify([dto.id, sessionLabel,
            selections.map(prefix => getCheckedIds(prefix)), runtimeConfirm.checked, text]);
        accumulatedEntries.set(signature, { instrumentId: dto.id, text });
        usedInstruments.set(dto.id, dto.display_name || dto.id);
        updateOutputText();
    });


    clearBtn.addEventListener("click", () => {
        accumulatedEntries = new Map();
        usedInstruments = new Map();
        updateOutputText();
    });

    copyBtn.addEventListener("click", async () => {
        if (accumulatedEntries.size === 0) return;
        const feedback = document.getElementById("copy-feedback");
        feedback.style.display = "none";
        try {
            await navigator.clipboard.writeText(outputText.value);
            feedback.textContent = "Copied!";
            feedback.style.display = "inline";
            setTimeout(() => feedback.style.display = "none", 2000);
        } catch (error) {
            outputText.focus();
            outputText.select();
            feedback.textContent = "Automatic copying failed. The text is selected; copy it manually.";
            feedback.style.display = "inline";
        }
    });

    addBtn.disabled = true;
    systemSelect.disabled = true;
    await loadInstruments();
});
