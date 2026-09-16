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
    const newAcquisitionBtn = document.getElementById("new-acquisition-btn");

    const methodsMetadataWarning = document.getElementById("methods-metadata-warning");
    const methodsMetadataBlockers = document.getElementById("methods-metadata-blockers");

    let instruments = [];
    let currentInst = null;
    let accumulatedEntries = new Map();
    let usedInstruments = new Map();
    // The entry the form is currently describing. While it is set, adding again
    // updates that entry instead of appending a near-identical second copy of the
    // same acquisition; it is released whenever the user signals a new acquisition.
    let activeEntryKey = "";
    let entrySequence = 0;
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
        const options = [];

        // Acquisition software is a canonical structured record. Build its
        // confirmable sentence from that record instead of reusing a Methods string
        // that may contain a placeholder such as "vunknown" or an embedded
        // [PLEASE SPECIFY] request. The request stays structured and therefore lands
        // in the review block only when the user confirms that software was used.
        const placeholderValues = new Set([
            "unknown", "n/a", "na", "none", "not applicable", "tbd", "-", "--", "?",
        ]);
        const acquisitionSoftware = (Array.isArray(dto?.software) ? dto.software : []).filter((row) => {
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
            const numericVersion = /^\d+(?:[.\-]\d+)*(?:\s|$)/.test(version);
            const softwareLabel = version
                ? `${name} (${numericVersion ? `v${version}` : `version ${version}`})`
                : name;
            const sentence = `Instrument control and image acquisition were performed using ${softwareLabel}.`;
            options.push({
                id: `action-acquisition-software-${softwareIndex}`,
                display_label: sentence,
                method_sentence: sentence,
                // Confirming five LAS X modules used to produce five sentences each
                // claiming to have performed the acquisition. Sharing one frame lets
                // them merge into the single sentence an author would write.
                publication_template: "Instrument control and image acquisition were performed using {label}.",
                publication_label: softwareLabel,
                review_prompts: version
                    ? []
                    : [`[PLEASE SPECIFY: acquisition software version for ${name}]`],
            });
        });
        if (!acquisitionSoftware.length && !Array.isArray(dto?.software)) {
            // Compatibility for older/synthetic DTOs that predate the canonical
            // software list. Production exports always carry `software`, so this
            // path cannot reintroduce placeholder software prose there.
            const fallback = cleanText(methods.acquisition_software_sentence);
            if (fallback) {
                options.push({
                    id: "action-acquisition-software-legacy",
                    display_label: fallback,
                    method_sentence: fallback,
                    review_prompts: uniqueTexts([methods.acquisition_software_review_prompt]),
                });
            }
        }

        const otherSentences = dedupeSentences([
            methods.environment_sentence,
            ...(methods.stage_sentences || []),
            methods.autofocus_sentence,
            methods.triggering_sentence,
        ]);
        otherSentences.forEach((text, index) => {
            options.push({
                id: `action-${index}`,
                display_label: text,
                method_sentence: text,
                review_prompts: [],
            });
        });

        // Processing tools share a frame for the same reason acquisition software
        // does: three analysis packages are one sentence, not three.
        const processingSentences = dedupeSentences(methods.processing_sentences || []);
        const PROCESSING_FRAME = "Post-acquisition processing and analysis were performed using ";
        processingSentences.forEach((text, index) => {
            const label = text.startsWith(PROCESSING_FRAME)
                ? text.slice(PROCESSING_FRAME.length).replace(/\.$/, "")
                : "";
            options.push({
                id: `action-processing-${index}`,
                display_label: text,
                method_sentence: text,
                publication_template: label ? `${PROCESSING_FRAME}{label}.` : "",
                publication_label: label,
                review_prompts: [],
            });
        });
        return options;
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

    // Acronyms are read letter by letter, so the article follows the letter name.
    const ACRONYM_VOWEL_LETTERS = new Set("AEFHILMNORSX".split(""));

    /**
     * Prefix a generated label with the article a reader would say.
     *
     * Labels are assembled from recorded fields, so "Excitation was provided by
     * 640 nm laser" is a sentence no author would write. The article depends on
     * how the label is read aloud, not on its first letter alone: "an LED",
     * "a UV lamp", "an 800 nm laser".
     */
    function withArticle(label) {
        const cleaned = cleanText(label);
        if (!cleaned) return "";
        const firstWord = cleaned.split(/\s+/)[0];
        const first = firstWord[0];
        let article = "a";
        if (/[0-9]/.test(first)) {
            article = (/^(8|11|18)/.test(firstWord)) ? "an" : "a";
        } else if (firstWord.length > 1 && firstWord === firstWord.toUpperCase() && /[A-Z]/.test(first)) {
            article = ACRONYM_VOWEL_LETTERS.has(first) ? "an" : "a";
        } else if ("aeiou".includes(first.toLowerCase())) {
            article = "an";
        }
        return `${article} ${cleaned}`;
    }

    /**
     * Lower-case a picker label for mid-sentence use, keeping acronyms intact.
     *
     * Control labels are written for a column heading ("Spectral Imaging", "TIRF").
     * Dropping them into prose unchanged is how catalogue capitalisation reaches a
     * manuscript.
     */
    function lowerLabel(label) {
        return cleanText(label).split(/\s+/).map((word) => {
            const bare = word.replace(/[^A-Za-z]/g, "");
            if (bare.length > 1 && bare === bare.toUpperCase()) return word;
            if (/\d/.test(word)) return word;
            return word.toLowerCase();
        }).join(" ");
    }

    /**
     * Lower-case the first word of a sentence-form phrase so it can follow another.
     */
    function decapitalizePhrase(phrase) {
        const cleaned = cleanText(phrase);
        if (!cleaned) return "";
        const firstWord = cleaned.split(/\s+/)[0];
        const bare = firstWord.replace(/[^A-Za-z]/g, "");
        if (bare.length > 1 && bare === bare.toUpperCase()) return cleaned;
        return cleaned.charAt(0).toLowerCase() + cleaned.slice(1);
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

    function bindCheckboxes(containerId, items, prefix, selectedIds = new Set(), selectedPositionIds = new Set()) {
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
            checkbox.type = item.selection_group ? "radio" : "checkbox";
            if (item.selection_group) checkbox.name = `${prefix}-${item.selection_group}`;
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
            // Which recorded light paths this component sits on. An acquisition may
            // travel more than one path, and the draft describes each separately
            // rather than merging a transmitted lamp into a fluorescence clause.
            checkbox.dataset.routeIds = JSON.stringify(Array.isArray(item.route_ids) ? item.route_ids : []);
            checkbox.dataset.inventoryClass = item.inventory_class || "";
            // The recorded component type, used to check a specialist module against
            // the techniques the user says the acquisition used.
            checkbox.dataset.componentType = item.type || "";
            // What technique this component implements, as vocab/modules.yaml
            // records it. Exported rather than restated here: a table in this file
            // duplicated the vocabulary and drifted from it.
            checkbox.dataset.providesCapability = JSON.stringify(
                item.provides_capability && typeof item.provides_capability === "object"
                    ? item.provides_capability
                    : {});
            // Two cameras recorded under one model name are told apart by the port
            // the record routes each of them to, never by inventing a difference.
            checkbox.dataset.portLabel = item.port_label || "";

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
            bindSelectablePositions(container, item, prefix, index, selectedPositionIds);
        });
        return normalizedItems.length;
    }

    /**
     * Keep only the positions recorded on a route the user selected.
     *
     * A holder shared by two routes may carry different positions on each, so
     * offering all of them would let a user report a route together with a
     * position that route cannot reach.
     */
    function positionsOnSelectedRoutes(positions) {
        const checkedRouteIds = new Set(getCheckedIds("route"));
        if (!checkedRouteIds.size) return positions;
        return positions.filter((position) => {
            const routeIds = Array.isArray(position?.route_ids) ? position.route_ids.map(cleanText) : [];
            return !routeIds.length || routeIds.some(id => checkedRouteIds.has(id));
        });
    }

    /**
     * Offer the positions a filter turret or wheel can be set to.
     *
     * Ticking the holder only says light passed through it, which tells a reader
     * nothing about the filter that was used - the fact a fluorescence Methods
     * section turns on. The positions are recorded per route, so they are offered
     * as nested choices and the holder is ticked automatically when one is picked.
     */
    function bindSelectablePositions(container, item, prefix, itemIndex, selectedPositionIds = new Set()) {
        const allPositions = Array.isArray(item?.selectable_positions) ? item.selectable_positions : [];
        const positions = positionsOnSelectedRoutes(allPositions);
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
            // A holder is set to one position at a time, but an acquisition is not:
            // a two-colour experiment uses two emission filters on the same wheel.
            // The recorded exclusivity is kept as information - it becomes a
            // question about channel order - rather than as a limit on what the
            // user can report.
            const selectionMode = cleanText(position?.selection_mode).toLowerCase() || "exclusive";
            checkbox.type = "checkbox";
            checkbox.dataset.selectionMode = selectionMode;
            checkbox.id = `${prefix}position-${itemIndex}-${positionIndex}`;
            checkbox.value = `${componentId}::${positionId}`;
            checkbox.checked = selectedPositionIds.has(checkbox.value);
            checkbox.dataset.category = `${prefix}-position`;
            checkbox.dataset.componentId = componentId;
            checkbox.dataset.componentLabel = componentLabel;
            checkbox.dataset.displayLabel = positionLabel;
            checkbox.dataset.incomplete = position?.incomplete ? "1" : "";
            checkbox.dataset.routeIds = JSON.stringify(Array.isArray(position?.route_ids) ? position.route_ids : []);
            const productCode = cleanText(position?.product_code);
            const isEmpty = Boolean(position?.is_empty);
            // Two empty slots of one turret are different configurations: a bare
            // brightfield position and one that carries a polariser both record
            // no filter. Keeping the recorded slot identity is what lets a user
            // tell them apart here and state which one was used.
            const emptyIdentity = position?.has_identity ? ` (position ${positionLabel})` : "";
            const identity = isEmpty
                ? `Empty (no filter)${emptyIdentity}`
                : productCode ? `${positionLabel} (catalogue no. ${productCode})` : positionLabel;
            // The recorded transmission is what a reader checks; the catalogue name
            // alone is a facility shorthand. The phrase is built where the spectral
            // model lives, so prose and the simulator cannot disagree about it.
            const publicationPhrase = cleanText(position?.publication_phrase) || identity;
            checkbox.dataset.publicationTemplate = isEmpty
                ? "No filter was installed in {label}."
                : "The light path included {label}.";
            checkbox.dataset.publicationLabel = isEmpty
                ? `${componentLabel}${emptyIdentity}`
                : componentLabel ? `${publicationPhrase} in the ${componentLabel}` : publicationPhrase;
            // The filter alone, so positions sharing a holder can be named together
            // instead of repeating "in the CSU-W1 Emission Wheel" once per filter.
            checkbox.dataset.positionPhrase = publicationPhrase;
            checkbox.dataset.isEmptyPosition = isEmpty ? "1" : "";
            checkbox.dataset.componentDisplayLabel = componentLabel;
            const componentType = cleanText(position?.component_type).toLowerCase();
            const cubeLike = !componentType || componentType === "filter_cube";
            const incompletePrompt = cubeLike
                ? `[PLEASE VERIFY: the recorded transmission bands for ${positionLabel} are incomplete; confirm its excitation filter, dichroic and emission filter]`
                : `[PLEASE VERIFY: the recorded optical details for ${positionLabel} are incomplete; confirm the exact setting used]`;
            checkbox.dataset.reviewPrompts = JSON.stringify(position?.incomplete ? [incompletePrompt] : []);

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
            // One acquisition can travel two recorded paths when two methods were
            // used, so the path is a checkbox and the draft describes each path's
            // hardware in its own sentence group.
            routeCheckbox.type = "checkbox";
            routeCheckbox.id = `route-${routeIdx}`;
            routeCheckbox.value = routeId;
            routeCheckbox.dataset.displayLabel = routeLabel;
            // The opening sentence states the method. Naming the light path here put
            // routing vocabulary - "with the Multiphoton route" - into finished prose.
            routeCheckbox.dataset.methodSentence = "";
            routeCheckbox.dataset.publicationPhrase = cleanText(route.publication_phrase)
                || `${routeLabel} imaging`;
            routeCheckbox.dataset.category = "route";
            routeCheckbox.dataset.routeType = cleanText(route.route_type);
            const relevantHardware = route?.relevant_hardware && typeof route.relevant_hardware === "object"
                ? route.relevant_hardware : {};
            const hasRecordedRouteHardware = ["sources", "filters", "splitters", "endpoints"]
                .some(key => Array.isArray(relevantHardware[key]) && relevantHardware[key].length > 0);
            routeCheckbox.dataset.topologyIncomplete = hasRecordedRouteHardware ? "" : "1";

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
                // The method sentence already states what was done, and the route
                // label is the broader family ("Widefield fluorescence") which can
                // contradict the selected method ("TIRF"). Naming the light path
                // here also puts internal routing vocabulary into publication prose.
                readoutCheckbox.dataset.methodSentence = `${readoutLabel} data were acquired.`;
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

    function methodOptionsForInstrument(dto) {
        const byMethod = new Map();
        routeViewsForInstrument(dto).forEach((route) => {
            const routeId = cleanText(route?.id);
            const identity = route?.route_identity && typeof route.route_identity === "object"
                ? route.route_identity : {};
            const explicit = [
                ...(Array.isArray(identity.imaging_modes) ? identity.imaging_modes : []),
                ...(Array.isArray(identity.contrast_methods) ? identity.contrast_methods : []),
            ];
            const candidates = explicit;
            candidates.forEach((entry) => {
                const methodId = cleanText(entry?.id || entry);
                const displayLabel = cleanText(entry?.display_label || entry?.id || entry);
                if (!methodId || !displayLabel || !routeId) return;
                // The picker label and the sentence form are different strings:
                // "Confocal point scanning" names a column, and the generic
                // "<label> imaging" frame turns it into "Confocal point scanning
                // imaging". The vocabulary authors the sentence form, which is
                // also where an acronym is expanded on first use.
                const publicationPhrase = cleanText(entry?.publication_phrase)
                    || `${displayLabel} imaging`;
                if (!byMethod.has(methodId)) {
                    byMethod.set(methodId, {
                        id: methodId, display_label: displayLabel, route_ids: [],
                        publication_phrase: publicationPhrase,
                        method_sentence: `${publicationPhrase} was performed.`,
                    });
                }
                const option = byMethod.get(methodId);
                if (!option.route_ids.includes(routeId)) option.route_ids.push(routeId);
            });
        });
        return Array.from(byMethod.values());
    }

    function bindMethods(dto) {
        const container = document.getElementById("method-list");
        container.innerHTML = "";
        const options = methodOptionsForInstrument(dto);
        options.forEach((option, index) => {
            const wrapper = document.createElement("div");
            const input = document.createElement("input");
            // Several methods can describe one acquisition - brightfield alongside
            // fluorescence, a confocal reference beside its readout - and the method
            // choice only decides which components are offered.
            input.type = "checkbox";
            input.id = `method-${index}`;
            input.value = option.id;
            input.dataset.category = "method";
            input.dataset.displayLabel = option.display_label;
            input.dataset.publicationPhrase = option.publication_phrase;
            input.dataset.methodSentence = option.method_sentence;
            input.dataset.routeIds = JSON.stringify(option.route_ids);
            const label = document.createElement("label");
            label.htmlFor = input.id;
            label.textContent = ` ${option.display_label}`;
            wrapper.appendChild(input);
            wrapper.appendChild(label);
            container.appendChild(wrapper);
        });
        return options.length;
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
        if (!modalities.length) return false;
        const routeViews = routeViewsForInstrument(dto);
        const hasRoutes = routeViews.length > 0;
        if (dto?.retired) return !hasRoutes;
        const caps = dto?.capabilities && typeof dto.capabilities === "object" ? dto.capabilities : {};
        const hasCapabilities = Object.values(caps).some(value => Array.isArray(value) && value.length > 0);
        const hasExplicitRouteMethods = routeViews.some(route => {
            const identity = route?.route_identity && typeof route.route_identity === "object"
                ? route.route_identity : {};
            return (Array.isArray(identity.imaging_modes) && identity.imaging_modes.length > 0)
                || (Array.isArray(identity.contrast_methods) && identity.contrast_methods.length > 0);
        });
        return !hasCapabilities && !hasExplicitRouteMethods;
    }

    function updateHardwareVisibility(dto, preserveSelections = true) {
        const retained = Object.fromEntries(["light", "det", "filter", "splitter"].map(prefix =>
            [prefix, new Set(preserveSelections ? getCheckedIds(prefix) : [])]
        ));
        const retainedPositions = new Set(preserveSelections ? getCheckedIds("filterposition") : []);
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

        // Which recorded paths each component sits on, over every route rather than
        // only the selected ones, so a selection keeps its provenance when the
        // selected set changes.
        const routeIdsByHardwareId = new Map();
        routeViews.forEach((rv) => {
            const routeId = cleanText(rv?.id);
            if (!routeId) return;
            ["sources", "filters", "splitters", "endpoints"].forEach((key) => {
                (rv.relevant_hardware?.[key] || []).forEach((item) => {
                    const id = cleanText(item?.id);
                    if (!id) return;
                    if (!routeIdsByHardwareId.has(id)) routeIdsByHardwareId.set(id, []);
                    const routes = routeIdsByHardwareId.get(id);
                    if (!routes.includes(routeId)) routes.push(routeId);
                });
            });
        });

        // The port a branch routes an endpoint to. Two cameras recorded under the
        // same model name are indistinguishable in prose without it; the record
        // already names the branches ("To Kinetix Master"), so nothing is invented.
        const portLabelByHardwareId = new Map();
        routeViews.forEach((rv) => {
            (Array.isArray(rv?.branch_summary?.branches) ? rv.branch_summary.branches : []).forEach((branch) => {
                const label = cleanText(branch?.label).replace(/^to\s+/i, "");
                if (!label) return;
                (branch?.endpoint_inventory_ids || []).forEach((id) => {
                    const key = cleanText(id);
                    if (key && !portLabelByHardwareId.has(key)) portLabelByHardwareId.set(key, label);
                });
            });
        });

        function annotate(items) {
            return items.map((item) => {
                const id = cleanText(item?.id);
                return {
                    ...item,
                    route_ids: routeIdsByHardwareId.get(id) || [],
                    port_label: portLabelByHardwareId.get(id) || "",
                };
            });
        }

        function decorateExclusiveEndpoints(items) {
            if (checkedRouteIds.size !== 1) return items;
            const routeId = Array.from(checkedRouteIds)[0];
            const route = routeViews.find(item => cleanText(item?.id) === routeId);
            const groups = new Map();
            (Array.isArray(route?.branch_summary?.branches) ? route.branch_summary.branches : []).forEach((branch) => {
                if (cleanText(branch?.selection_mode).toLowerCase() !== "exclusive") return;
                const group = cleanText(branch?.block_id) || "exclusive-branch";
                (branch?.endpoint_inventory_ids || []).forEach(id => groups.set(cleanText(id), group));
            });
            return items.map(item => groups.has(cleanText(item?.id))
                ? {...item, selection_group: groups.get(cleanText(item?.id))}
                : item);
        }

        const allLightItems = inventoryItemsForClasses(dto, ["light_source"]);
        const allDetItems = inventoryItemsForClasses(dto, ["endpoint", "camera_port", "eyepiece"]);
        const allFilterItems = inventoryItemsForClasses(dto, ["optical_element"]);
        const allSplitterItems = inventoryItemsForClasses(dto, ["splitter"]);
        toggleSectionVisibility("section-light", bindCheckboxes("light-list", annotate(filterBySelection(allLightItems)), "light", retained.light) > 0);
        toggleSectionVisibility("section-det", bindCheckboxes("det-list", annotate(decorateExclusiveEndpoints(filterBySelection(allDetItems))), "det", retained.det) > 0);
        toggleSectionVisibility("section-filter", bindCheckboxes("filter-list", annotate(filterBySelection(allFilterItems)), "filter", retained.filter, retainedPositions) > 0);
        toggleSectionVisibility("section-splitter", bindCheckboxes("splitter-list", annotate(filterBySelection(allSplitterItems)), "splitter", retained.splitter) > 0);

        const renderedPositionIds = new Set(
            Array.from(document.querySelectorAll('input[id^="filterposition-"]')).map(input => input.value)
        );
        const droppedPositions = Array.from(retainedPositions).filter(id => !renderedPositionIds.has(id));

        // Ticking a position ticks its holder, so a dropped position leaves the
        // holder behind on its own. "The light path included CSU-W1 Dichroic
        // Slider." names the container and no filter, which is exactly the
        // uninformative claim offering positions is meant to replace. The holder
        // is released unless another of its positions is still selected.
        const holdersWithSelection = new Set(
            getCheckedSelections("filterposition").map(item => cleanText(item.id).split("::")[0])
        );
        droppedPositions
            .map(id => cleanText(id).split("::")[0])
            .filter(componentId => componentId && !holdersWithSelection.has(componentId))
            .forEach((componentId) => {
                document.querySelectorAll('input[id^="filter-"]').forEach((holder) => {
                    if (holder.value === componentId) holder.checked = false;
                });
            });

        // A selection that silently disappears is worse than one that is kept: the
        // user cannot tell that the draft no longer reports the camera they chose.
        const droppedHardware = ["light", "det", "filter", "splitter"].reduce((total, prefix) => {
            const rendered = new Set(
                Array.from(document.querySelectorAll(`input[id^="${prefix}-"]`)).map(input => input.value)
            );
            return total + Array.from(retained[prefix]).filter(id => !rendered.has(id)).length;
        }, 0);
        const droppedTotal = droppedPositions.length + droppedHardware;

        setSelectionStatus(droppedTotal
            ? `${droppedTotal} previously selected item${droppedTotal === 1 ? " was" : "s were"} cleared because ${droppedTotal === 1 ? "it is" : "they are"} not recorded on the light path now selected. Choose what was used on this path.`
            : "");
    }

    function setSelectionStatus(message) {
        const selectionStatus = document.getElementById("methods-selection-status");
        if (!selectionStatus) return;
        const text = cleanText(message);
        selectionStatus.textContent = text;
        selectionStatus.style.display = text ? "" : "none";
    }

    function getCheckedSelections(prefix) {
        return Array.from(document.querySelectorAll(`input[id^="${prefix}-"]:checked`)).map(cb => ({
            id: cb.value,
            displayLabel: cleanText(cb.dataset.displayLabel),
            methodSentence: cleanText(cb.dataset.methodSentence),
            role: cleanText(cb.dataset.role),
            routeType: cleanText(cb.dataset.routeType),
            routeIds: parseJsonArray(cb.dataset.routeIds),
            publicationPhrase: cleanText(cb.dataset.publicationPhrase),
            topologyIncomplete: cb.dataset.topologyIncomplete === "1",
            publicationTemplate: cleanText(cb.dataset.publicationTemplate),
            publicationLabel: cleanText(cb.dataset.publicationLabel),
            reviewPrompts: parseJsonArray(cb.dataset.reviewPrompts),
            inventoryClass: cleanText(cb.dataset.inventoryClass),
            componentType: cleanText(cb.dataset.componentType),
            providesCapability: parseJsonObject(cb.dataset.providesCapability),
            portLabel: cleanText(cb.dataset.portLabel),
            componentId: cleanText(cb.dataset.componentId),
            componentDisplayLabel: cleanText(cb.dataset.componentDisplayLabel),
            positionPhrase: cleanText(cb.dataset.positionPhrase),
            isEmptyPosition: cb.dataset.isEmptyPosition === "1",
            selectionMode: cleanText(cb.dataset.selectionMode),
        }));
    }

    function parseJsonObject(value) {
        try {
            const parsed = JSON.parse(value || "{}");
            return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
        } catch (error) {
            return {};
        }
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
    /**
     * Keep only the part of a port label the component name does not already carry.
     *
     * "Photometrics Kinetix (Kinetix Master)" says Kinetix twice; the port only has
     * to supply what tells the two cameras apart.
     */
    function distinguishingPortLabel(portLabel, componentLabel) {
        const port = cleanText(portLabel);
        if (!port) return "";
        const known = new Set(cleanText(componentLabel).toLowerCase().split(/[^a-z0-9]+/).filter(Boolean));
        const remainder = port.split(/\s+/).filter(word => !known.has(word.toLowerCase().replace(/[^a-z0-9]+/g, "")));
        return remainder.length ? remainder.join(" ").toLowerCase() : port;
    }

    function mergeByPublicationTemplate(selections, options = {}) {
        const articleFor = typeof options.articleFor === "function" ? options.articleFor : () => false;
        const groups = new Map();
        const seenIds = new Set();
        const prompts = [];

        const normalized = (Array.isArray(selections) ? selections : []).filter((item) => {
            const id = cleanText(item?.id);
            if (id && seenIds.has(id)) return false;
            if (id) seenIds.add(id);
            return true;
        });

        // Two components recorded under one name are told apart by the port the
        // record routes them to, so a dual-camera acquisition can say so instead of
        // reporting one camera and asking which.
        const labelCounts = new Map();
        normalized.forEach((item) => {
            const label = cleanText(item?.publicationLabel) || cleanText(item?.displayLabel);
            if (label) labelCounts.set(label, (labelCounts.get(label) || 0) + 1);
        });

        normalized.forEach((item) => {
            prompts.push(...(item?.reviewPrompts || []));

            const template = cleanText(item?.publicationTemplate);
            const baseLabel = cleanText(item?.publicationLabel) || cleanText(item?.displayLabel);
            if (!template || !template.includes("{label}") || !baseLabel) {
                const fallback = cleanText(item?.methodSentence);
                if (fallback) groups.set(`literal::${fallback}`, { literal: fallback });
                return;
            }
            let label = baseLabel;
            if ((labelCounts.get(baseLabel) || 0) > 1) {
                const port = distinguishingPortLabel(cleanText(item?.portLabel), baseLabel);
                if (port) {
                    label = `${baseLabel} (${port})`;
                } else {
                    prompts.push(`[PLEASE SPECIFY: ${labelCounts.get(baseLabel)} separate components recorded as “${baseLabel}” were selected and this draft cannot tell them apart; state which one was used for each channel]`);
                }
            }
            if (articleFor(item)) label = withArticle(label);
            if (!groups.has(template)) groups.set(template, { template, labels: [] });
            groups.get(template).labels.push(label);
        });

        const sentences = [];
        groups.forEach((group) => {
            if (group.literal) {
                sentences.push(group.literal);
                return;
            }
            const labels = uniqueTexts(group.labels);
            // A frame that names several components has to agree with them.
            const sentence = group.template
                .replace("{label}", humanJoin(labels))
                .replace(/\{be\}/g, labels.length === 1 ? "was" : "were")
                .replace(/\{plural\}/g, labels.length === 1 ? "" : "s");
            sentences.push(sentence);
        });

        return { sentences: dedupeSentences(sentences), prompts: uniqueTexts(prompts) };
    }

    /**
     * One sentence for every filter position the acquisition used.
     *
     * Positions are grouped by the holder they sit in, so a two-colour experiment
     * reads "a GFP filter and a Cy3 filter in the emission wheel" rather than
     * restating the wheel once per filter.
     */
    function filterPositionSentences(positionSelections) {
        const holders = new Map();
        const emptyClauses = [];
        (positionSelections || []).forEach((item) => {
            const holderLabel = cleanText(item.componentDisplayLabel);
            if (item.isEmptyPosition) {
                emptyClauses.push(cleanText(item.publicationLabel));
                return;
            }
            const phrase = cleanText(item.positionPhrase) || cleanText(item.publicationLabel);
            if (!phrase) return;
            const key = holderLabel || "";
            if (!holders.has(key)) holders.set(key, []);
            holders.get(key).push(phrase);
        });

        const clauses = [];
        holders.forEach((phrases, holderLabel) => {
            const named = humanJoin(phrases);
            clauses.push(holderLabel ? `${named} in the ${holderLabel}` : named);
        });

        const sentences = [];
        if (clauses.length) sentences.push(`The light path included ${humanJoin(clauses)}.`);
        uniqueTexts(emptyClauses).forEach((clause) => {
            sentences.push(`No filter was installed in ${clause}.`);
        });
        return sentences;
    }

    function getCheckedIds(prefix) {
        return getCheckedSelections(prefix).map(item => item.id).sort();
    }

    /**
     * Keep sentences and unresolved publication questions coupled for hardware
     * categories that do not use publication templates. Previously these categories
     * copied only `methodSentence`, silently dropping component `review_prompts`.
     */
    function selectedSentenceBundle(prefixes) {
        const selections = (Array.isArray(prefixes) ? prefixes : [])
            .flatMap(prefix => getCheckedSelections(prefix));
        return {
            sentences: dedupeSentences(selections.map(item => item.methodSentence)),
            prompts: uniqueTexts(selections.flatMap(item => item.reviewPrompts || [])),
        };
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
        const byId = routeViews.find(route => cleanText(route?.id) === target);
        if (byId) return byId;
        // A display label or a broad illumination mode may be shared by two routes
        // that use different filters, branches or endpoints. Either identifies a
        // route only when exactly one route answers to it.
        const uniqueMatch = (accessor) => {
            const matches = routeViews.filter(route => cleanText(route?.[accessor]) === target);
            return matches.length === 1 ? matches[0] : null;
        };
        return uniqueMatch("display_label") || uniqueMatch("illumination_mode") || null;
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
        // Canonical ids identify exactly one component. Labels do not: an instrument
        // with two identical cameras records the same label twice, so a label that
        // resolves to more than one component identifies neither and must not be
        // allowed to bind a plan to whichever happened to be indexed first.
        const byId = new Map();
        const byLabel = new Map();
        opticalPathInventory(dto).forEach((item) => {
            [item?.id, item?.hardware_id].map(cleanText).filter(Boolean).forEach((key) => {
                byId.set(key.toLowerCase(), item);
            });
            [item?.display_label, item?.canonical_display_label, item?.publication_label]
                .map(cleanText).filter(Boolean).forEach((key) => {
                    const normalized = key.toLowerCase();
                    const known = byLabel.get(normalized);
                    if (!known) {
                        byLabel.set(normalized, item);
                    } else if (known !== item) {
                        byLabel.set(normalized, "ambiguous");
                    }
                });
        });
        return { byId, byLabel };
    }

    /**
     * Resolve a plan component against the instrument record.
     *
     * Returns the recorded component, or a reason it could not be resolved.
     * "Ambiguous" is not a weaker match than "unmatched": binding a plan to the
     * wrong one of two identical detectors produces a confident sentence about
     * the wrong physical component, so both refuse to produce a claim.
     */
    // Both fields come from the instrument record, so either is canonical; only
    // the plan's own label is not.
    function recordedLabel(item) {
        return cleanText(item?.publication_label) || cleanText(item?.display_label);
    }

    function matchRecordedComponent(index, ids, labels) {
        for (const candidate of ids) {
            const key = cleanText(candidate).toLowerCase();
            if (key && index.byId.has(key)) return { item: index.byId.get(key), reason: "" };
        }
        for (const candidate of labels) {
            const key = cleanText(candidate).toLowerCase();
            if (!key || !index.byLabel.has(key)) continue;
            const hit = index.byLabel.get(key);
            if (hit === "ambiguous") return { item: null, reason: "ambiguous" };
            return { item: hit, reason: "" };
        }
        return { item: null, reason: "unmatched" };
    }

    function unresolvedComponentPrompt(label, reason) {
        return reason === "ambiguous"
            ? `[PLEASE SPECIFY: more than one recorded component is called “${label}”, so the reviewed plan does not identify which one was used; state the exact component]`
            : `[PLEASE VERIFY: the reviewed plan names “${label}”, which is not in the current instrument record; confirm the component that was actually used]`;
    }

    function withWavelength(label, wavelength) {
        if (wavelength === null || !(wavelength > 0)) return label;
        return label.includes(`${wavelength} nm`) ? label : `${label} (${wavelength} nm)`;
    }

    /**
     * Check a plan's excitation wavelength against what the source can produce.
     *
     * Matching a component by its canonical id says the right laser was named; it
     * says nothing about the line. A fixed 488 nm laser matched by id while the
     * plan carries 594 would otherwise be published as "488 nm laser (594 nm)".
     */
    // Earlier work stopped the draft calling a STED depletion beam an excitation
    // source. The request about its wavelength must not reintroduce that.
    const WAVELENGTH_NOUN_BY_ROLE = {
        excitation: "excitation wavelength",
        depletion: "depletion wavelength",
        activation: "photoactivation wavelength",
    };

    function wavelengthNoun(recorded) {
        const metadata = recorded?.source_metadata && typeof recorded.source_metadata === "object"
            ? recorded.source_metadata
            : {};
        const role = cleanText(metadata.role || recorded?.role).toLowerCase();
        return WAVELENGTH_NOUN_BY_ROLE[role] || "wavelength";
    }

    function resolveRuntimeWavelength(recorded, wavelength, label) {
        if (wavelength === null || !(wavelength > 0)) return { wavelength: null, prompt: "" };
        const noun = wavelengthNoun(recorded);
        const metadata = recorded?.source_metadata && typeof recorded.source_metadata === "object"
            ? recorded.source_metadata
            : {};
        const tunableMin = optionalNumber(metadata.tunable_min_nm);
        const tunableMax = optionalNumber(metadata.tunable_max_nm);
        const fixed = optionalNumber(metadata.wavelength_nm);

        if (tunableMin !== null && tunableMax !== null) {
            if (wavelength < tunableMin || wavelength > tunableMax) {
                return {
                    wavelength: null,
                    prompt: `[PLEASE VERIFY: the reviewed plan reports ${wavelength} nm from ${label}, which is outside its recorded tunable range of ${tunableMin}–${tunableMax} nm; confirm the ${noun} used]`,
                };
            }
            return { wavelength, prompt: "" };
        }
        if (fixed !== null) {
            if (fixed !== wavelength) {
                return {
                    wavelength: null,
                    prompt: `[PLEASE VERIFY: the reviewed plan reports ${wavelength} nm from ${label}, which the instrument record gives as a fixed ${fixed} nm source; confirm the ${noun} used]`,
                };
            }
            return { wavelength, prompt: "" };
        }
        return {
            wavelength: null,
            prompt: `[PLEASE VERIFY: the reviewed plan reports ${wavelength} nm from ${label}, but no wavelength is recorded for this source; confirm the ${noun} used]`,
        };
    }

    /**
     * Check a plan's detection window against the detector's recorded range.
     *
     * Where the record states no range there is nothing to contradict, so the
     * confirmed setting stands; where it does, a window outside it is a question.
     */
    function resolveRuntimeDetectionWindow(recorded, minimum, maximum, label) {
        const hasWindow = minimum !== null && maximum !== null && minimum > 0 && maximum > minimum;
        if (!hasWindow) return { window: "", prompt: "" };
        const metadata = recorded?.endpoint_metadata && typeof recorded.endpoint_metadata === "object"
            ? recorded.endpoint_metadata
            : {};
        // The schema makes each bound independently optional, so a detector may
        // record only a lower or only an upper limit. Each known bound is enforced
        // on its own: requiring both would let a window contradict the one bound
        // that is actually recorded.
        const recordedMin = optionalNumber(metadata.collection_min_nm ?? metadata.min_nm);
        const recordedMax = optionalNumber(metadata.collection_max_nm ?? metadata.max_nm);
        const breaches = [];
        if (recordedMin !== null && minimum < recordedMin) {
            breaches.push(`below its recorded collection minimum of ${recordedMin} nm`);
        }
        if (recordedMax !== null && maximum > recordedMax) {
            breaches.push(`above its recorded collection maximum of ${recordedMax} nm`);
        }
        if (breaches.length) {
            return {
                window: "",
                prompt: `[PLEASE VERIFY: the reviewed plan reports a ${minimum}–${maximum} nm detection window on ${label}, which is ${humanJoin(breaches)}; confirm the window used]`,
            };
        }
        return { window: `${minimum}–${maximum} nm`, prompt: "" };
    }

    /**
     * Resolve a plan's position against the positions recorded for the element.
     *
     * A plan can name the right turret and the wrong position. The reported
     * position is taken from the record, never from the plan, and must be one the
     * element offers on the route being reported.
     */
    function resolveRuntimePosition(recorded, step, routeId, label) {
        // The stable key identifies the position; the display label is a rendering
        // of it. A stale plan can carry a key and a label that name different
        // positions, so the key decides and a label that disagrees with it - or
        // that names nothing recorded - makes the position review-only.
        const key = cleanText(step?.position_key) || cleanText(step?.position_id);
        const labelText = cleanText(step?.position_label);
        const raw = key || labelText;
        if (!raw) return { position: "", prompt: "" };
        const positions = Array.isArray(recorded?.selectable_positions) ? recorded.selectable_positions : [];
        if (!positions.length) {
            return {
                position: "",
                prompt: `[PLEASE VERIFY: the reviewed plan reports ${label} at “${raw}”, but the instrument record does not list the positions of this element; confirm the filter that was used]`,
            };
        }
        // A stable position key must resolve only against canonical position ids.
        // Display labels are a legacy/user-facing fallback and are accepted only
        // when they identify exactly one recorded position. This prevents a label
        // collision from shadowing a real id and prevents duplicate labels from
        // silently selecting the first position in the record.
        const resolveById = (value) => {
            const normalized = cleanText(value).toLowerCase();
            if (!normalized) return null;
            return positions.find(position => cleanText(position?.id).toLowerCase() === normalized) || null;
        };
        const resolveUniqueByLabel = (value) => {
            const normalized = cleanText(value).toLowerCase();
            if (!normalized) return { match: null, ambiguous: false };
            const matches = positions.filter(position =>
                cleanText(position?.display_label).toLowerCase() === normalized);
            return {
                match: matches.length === 1 ? matches[0] : null,
                ambiguous: matches.length > 1,
            };
        };

        const keyMatch = key ? resolveById(key) : null;
        const labelResolution = labelText ? resolveUniqueByLabel(labelText) : { match: null, ambiguous: false };
        const labelMatch = labelResolution.match;
        if (key && !keyMatch) {
            return {
                position: "",
                prompt: `[PLEASE VERIFY: the reviewed plan reports ${label} at “${key}”, which is not one of its recorded positions; confirm the filter that was used]`,
            };
        }
        if (labelResolution.ambiguous) {
            return {
                position: "",
                prompt: `[PLEASE VERIFY: the reviewed plan reports ${label} at “${labelText}”, but more than one recorded position has that label; confirm the exact filter position that was used]`,
            };
        }
        if (keyMatch && labelText && labelMatch !== keyMatch) {
            return {
                position: "",
                prompt: `[PLEASE VERIFY: the reviewed plan gives ${label} position “${key}” and “${labelText}”, which do not describe the same recorded position; confirm the filter that was used]`,
            };
        }
        const match = keyMatch || labelMatch;
        if (!match) {
            return {
                position: "",
                prompt: `[PLEASE VERIFY: the reviewed plan reports ${label} at “${raw}”, which is not one of its recorded positions; confirm the filter that was used]`,
            };
        }
        const positionRoutes = Array.isArray(match.route_ids) ? match.route_ids.map(cleanText) : [];
        if (routeId && positionRoutes.length && !positionRoutes.includes(routeId)) {
            return {
                position: "",
                prompt: `[PLEASE VERIFY: the reviewed plan reports ${label} at “${cleanText(match.display_label)}”, which is not recorded on the light path being reported; confirm the light path and filter that were used]`,
            };
        }
        const productCode = cleanText(match.product_code);
        const identity = cleanText(match.display_label);
        return {
            position: productCode ? `${identity} (catalogue no. ${productCode})` : identity,
            prompt: "",
        };
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
    // A runtime plan contributes the same kinds of fact a tick box does, so the
    // completeness check has to read it the same way: a plan that names a camera
    // reports a detector, and a plan that names only a filter reports no
    // illumination. Counting its components as one undifferentiated list is how an
    // entry asked for a detector it had just named, and stopped asking for the
    // illumination it had not.
    const RUNTIME_SOURCE_CLASSES = new Set(["light_source"]);
    const RUNTIME_ENDPOINT_CLASSES = new Set(["endpoint", "camera_port", "eyepiece"]);

    function runtimeAcquisitionFacts(dto) {
        const empty = {
            components: [], sentences: [], prompts: [], routeLabels: [],
            hasRuntimeSelection: false, sources: [], endpoints: [],
        };
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
        const routeId = cleanText(matchedRoute.id);

        function addFact(template, label, recorded, planLabel) {
            if (!template || !label) return;
            components.push({
                id: cleanText(recorded?.id) || `plan::${planLabel}`,
                publicationTemplate: template,
                publicationLabel: label,
                reviewPrompts: [],
                inventoryClass: cleanText(recorded?.inventory_class),
                role: cleanText(recorded?.role),
            });
        }

        (Array.isArray(runtimeConfig.sources) ? runtimeConfig.sources : []).forEach((source) => {
            const planLabel = cleanText(source?.display_label || source?.name || source?.id);
            if (!planLabel) return;
            const { item: recorded, reason } = matchRecordedComponent(
                index, [source?.id, source?.mechanismId], [planLabel]);
            // A component the record cannot confirm is a question, not a fact. It
            // must not also appear as finished prose: a reader takes the sentence
            // and not the caveat.
            if (!recorded) {
                prompts.push(unresolvedComponentPrompt(planLabel, reason));
                return;
            }
            // The role comes from the instrument record, never from the plan: a plan
            // knows which source was switched on, not what it was used for.
            (recorded.review_prompts || []).forEach(prompt => prompts.push(cleanText(prompt)));
            const label = recordedLabel(recorded);
            const { wavelength, prompt: wavelengthPrompt } = resolveRuntimeWavelength(
                recorded, optionalNumber(source?.selected_wavelength_nm ?? source?.wavelength_nm), label);
            if (wavelengthPrompt) prompts.push(wavelengthPrompt);
            addFact(
                cleanText(recorded.publication_template) || "Illumination was provided by {label}.",
                withWavelength(label, wavelength),
                recorded,
                planLabel,
            );
        });

        (Array.isArray(runtimeConfig.detectors) ? runtimeConfig.detectors : []).forEach((detector) => {
            const planLabel = cleanText(detector?.display_label || detector?.id);
            if (!planLabel) return;
            const { item: recorded, reason } = matchRecordedComponent(
                index, [detector?.id, detector?.mechanismId], [planLabel]);
            if (!recorded) {
                prompts.push(unresolvedComponentPrompt(planLabel, reason));
                return;
            }
            const label = recordedLabel(recorded);
            const { window, prompt: windowPrompt } = resolveRuntimeDetectionWindow(
                recorded,
                optionalNumber(detector?.collection_min_nm),
                optionalNumber(detector?.collection_max_nm),
                label,
            );
            if (windowPrompt) prompts.push(windowPrompt);
            addFact(
                cleanText(recorded.publication_template) || "Images were recorded using {label}.",
                window ? `${label} (detection ${window})` : label,
                recorded,
                planLabel,
            );
        });

        const routeSteps = Array.isArray(runtimeConfig.selected_route_steps) ? runtimeConfig.selected_route_steps : [];
        routeSteps.filter(step => step?.kind === "optical_component").forEach((step) => {
            const planLabel = cleanText(step?.display_label || step?.position_label || step?.component_type);
            if (!planLabel) return;
            const { item: recorded, reason } = matchRecordedComponent(
                index, [step?.hardware_inventory_id, step?.component_id], [planLabel]);
            if (!recorded) {
                prompts.push(unresolvedComponentPrompt(planLabel, reason));
                return;
            }
            const label = recordedLabel(recorded);
            const { position, prompt: positionPrompt } = resolveRuntimePosition(recorded, step, routeId, label);
            if (positionPrompt) prompts.push(positionPrompt);
            addFact(
                cleanText(recorded.publication_template) || "The light path included {label}.",
                position ? `${position} in the ${label}` : label,
                recorded,
                planLabel,
            );
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
            const { item: recorded, reason } = matchRecordedComponent(
                index, [splitter?.id, splitter?.mechanismId], [planLabel]);
            if (!recorded) {
                prompts.push(unresolvedComponentPrompt(planLabel, reason));
                return;
            }
            const label = recordedLabel(recorded);
            const rawBranches = Array.isArray(splitter?.selected_branch_ids) ? splitter.selected_branch_ids.filter(Boolean) : [];
            const named = rawBranches.map(id => branchLabels.get(cleanText(id)) || "").filter(Boolean);
            if (rawBranches.length && named.length !== rawBranches.length) {
                prompts.push(`[PLEASE SPECIFY: which output of ${label} was recorded; the reviewed plan identifies its branches only by internal reference]`);
            }
            addFact(
                cleanText(recorded.publication_template) || "The emission light was divided by {label}.",
                named.length ? `${label} (${humanJoin(named)} outputs)` : label,
                recorded,
                planLabel,
            );
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
            prompts.push("[PLEASE SPECIFY: the light path used; the reviewed plan names a light path that has no recorded name]");
        }

        return {
            components,
            sentences: dedupeSentences(sentences),
            prompts: uniqueTexts(prompts),
            routeLabels: routeLabel ? [routeLabel] : [],
            hasRuntimeSelection: true,
            sources: components.filter(item => RUNTIME_SOURCE_CLASSES.has(item.inventoryClass)),
            endpoints: components.filter(item => RUNTIME_ENDPOINT_CLASSES.has(item.inventoryClass)),
        };
    }

    function reviewBlock(prompts, heading) {
        const items = uniqueTexts(prompts);
        if (!items.length) return "";
        return `${heading}\n${items.map(prompt => `- ${prompt}`).join("\n")}`;
    }

    function updateOutputText() {
        if (accumulatedEntries.size === 0) {
            outputText.value = 'Select an instrument, then choose “Add to methods”.';
            return;
        }

        const entries = Array.from(accumulatedEntries.values());
        // Specimen preparation and the generic settings checklist are the same
        // request for every acquisition. Repeating them per entry is what made a
        // three-acquisition section read as concatenated form output.
        const sharedPrompts = uniqueTexts(entries.flatMap(entry => entry.sectionPrompts || []));
        const single = entries.length === 1;

        const blocks = entries.map((entry) => {
            const parts = [
                cleanText(entry.reference),
                ...(entry.paragraphs || []),
                reviewBlock(
                    single ? [...(entry.entryPrompts || []), ...sharedPrompts] : (entry.entryPrompts || []),
                    "Review before publication:",
                ),
            ];
            return parts.map(cleanText).filter(Boolean).join("\n\n");
        }).filter(Boolean);

        if (!single) {
            const shared = reviewBlock(sharedPrompts, "Review before publication — applies to every acquisition above:");
            if (shared) blocks.push(shared);
        }

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
        const methodCount = bindMethods(dto);
        toggleSectionVisibility("section-method", methodCount > 0);
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
        // A different microscope is always a different acquisition.
        activeEntryKey = "";
        setSelectionStatus("");
        if (methodCount > 0) {
            // Offering every light path before a method is chosen invites the user
            // to build a whole selection the first method click would then withdraw.
            // The path question is asked once the method has narrowed it.
            ["section-route", "section-light", "section-filter", "section-splitter", "section-det"].forEach(id => {
                const section = document.getElementById(id);
                if (section) section.style.display = "none";
            });
        } else if (routeCount === 1) {
            confirmSoleRouteWithoutMethodControl(dto);
        }
    });

    /**
     * Confirm the only recorded path on a record that offers no method control.
     *
     * A record with no imaging-method control still has to state a path before it
     * can state anything else, and there is nothing to ask when only one is
     * recorded. This runs on selecting the microscope and again whenever the
     * acquisition is cleared, because clearing used to leave such a record with no
     * path at all and no control to restore one, so the next Add was refused.
     */
    function confirmSoleRouteWithoutMethodControl(dto) {
        const methodSection = document.getElementById("section-method");
        if (methodSection && methodSection.style.display !== "none") return;
        const routeInputs = Array.from(document.querySelectorAll('input[id^="route-"]'));
        if (routeInputs.length !== 1) return;
        routeInputs[0].checked = true;
        updateHardwareVisibility(dto, false);
    }

    // A new acquisition reference names a different acquisition, so the next Add
    // starts an entry rather than rewriting the one just added.
    document.getElementById("session-label").addEventListener("input", () => {
        if (!activeEntryKey) return;
        // Naming a different figure names a different acquisition, and the page
        // says so. It used to say so while leaving every box ticked, so the second
        // entry silently republished the first one's objective, laser and filters
        // under a new reference. The methods stay: the user has said which figure
        // this is, not that the technique changed.
        startNewAcquisition({ keepMethods: true, keepLabel: true });
        setSelectionStatus("This reference names a new acquisition, so the selections have been cleared. The imaging method is kept; change it if this acquisition used another.");
    });

    /**
     * Re-derive what the instrument offers from the methods the user has ticked.
     *
     * Methods are additive and only gate availability: ticking one more offers more
     * hardware, unticking one withdraws whatever only that method reached. A
     * selection therefore survives exactly as long as it is still offered, which is
     * the rule that keeps a previous method's depletion laser or filter from
     * surviving invisibly - and keeps a still-valid laser from being wiped when two
     * methods share one recorded path.
     */
    function applyMethodAvailability(dto) {
        const methodSelections = getCheckedSelections("method");
        const allowed = new Set();
        methodSelections.forEach(method => (method.routeIds || []).forEach(id => allowed.add(id)));
        const constrained = methodSelections.length > 0;

        const routeInputs = Array.from(document.querySelectorAll('input[id^="route-"]'));
        routeInputs.forEach((route) => {
            const compatible = !constrained || allowed.has(route.value);
            if (route.parentElement) route.parentElement.style.display = compatible ? "" : "none";
            route.disabled = !compatible;
            if (!compatible) route.checked = false;
        });

        // A method recorded on exactly one path leaves nothing to choose, so the
        // path is confirmed for the user rather than asked as a second question.
        methodSelections.forEach((method) => {
            if ((method.routeIds || []).length !== 1) return;
            const route = routeInputs.find(input => input.value === method.routeIds[0]);
            if (route && !route.disabled) route.checked = true;
        });

        const checkedRoutes = new Set(getCheckedIds("route"));
        document.querySelectorAll('input[id^="readout-"]').forEach((readout) => {
            const routeId = cleanText(readout.dataset.routeId);
            const compatible = (!constrained || allowed.has(routeId));
            if (readout.parentElement) readout.parentElement.style.display = compatible ? "" : "none";
            readout.disabled = !compatible;
            if (!compatible || !checkedRoutes.has(routeId)) readout.checked = false;
        });

        toggleSectionVisibility("section-route", routeInputs.some(route => !route.disabled));
        // Hardware cannot belong to a path the acquisition does not name, and a
        // hidden control that stays ticked is reported without being visible.
        if (!checkedRoutes.size && routeInputs.some(route => !route.disabled)) {
            clearInputsByPrefixes(["light", "det", "filter", "filterposition", "splitter"]);
        }
        updateHardwareVisibility(dto, true);
        if (!checkedRoutes.size) {
            ["section-light", "section-filter", "section-splitter", "section-det"].forEach((id) => {
                const section = document.getElementById(id);
                if (section) section.style.display = "none";
            });
        }
    }

    document.getElementById("method-list").addEventListener("change", (event) => {
        if (!currentInst || event?.target?.dataset.category !== "method") return;
        // Changing what was imaged after an acquisition has been added describes a
        // different acquisition. Carrying the previous one's objective and modules
        // into it is how a confocal reference ends up claiming a STED module.
        if (activeEntryKey) {
            const target = event.target;
            const startedWith = target.checked ? target.value : "";
            startNewAcquisition({ keepMethods: true });
            if (startedWith) {
                // Ticking a method after adding means "this next acquisition was
                // that", not "the one I just added was also that". The methods of
                // the finished entry are released and only the new one is kept;
                // further methods can still be added to this entry.
                clearInputsByPrefixes(["method"]);
                target.checked = true;
            }
            setSelectionStatus("Started a new acquisition. The selections confirmed for the previous entry were cleared, so this one describes only what you tick now.");
        } else {
            setSelectionStatus("");
        }
        applyMethodAvailability(currentInst);
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
        // A readout is recorded on a path, so confirming one confirms that path.
        // Withdrawing a path withdraws the readouts recorded on it. Paths are no
        // longer mutually exclusive, so nothing else is cleared here.
        if (target?.dataset.category === "readout" && target.checked) {
            const targetRouteId = cleanText(target.dataset.routeId);
            document.querySelectorAll('input[id^="route-"]').forEach(route => {
                if (route.value === targetRouteId) route.checked = true;
            });
        } else if (target?.dataset.category === "route" && !target.checked) {
            document.querySelectorAll('input[id^="readout-"]').forEach(readout => {
                if (readout.dataset.routeId === target.value) readout.checked = false;
            });
        }
        if (currentInst) updateHardwareVisibility(currentInst, true);
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

    // The generic settings list is the same for a brightfield snapshot and a FLIM
    // measurement. These are the parameters a reader needs for the specific
    // technique, which no reviewer can reconstruct from the instrument record.
    // These name the parameters a reader needs for the technique, without assuming
    // a particular implementation of it: spectral imaging does not necessarily
    // involve unmixing, FRET is not necessarily intensity-based, and a disk's
    // pinhole geometry is usually a fixed specification rather than a choice.
    const REPORTING_METADATA_HINT =
        "These values are often stored in the original image metadata; see “Recover acquisition settings from image metadata” above.";

    function reportingRecommendation(details) {
        const cleaned = cleanText(details)
            .replace(/^\[PLEASE SPECIFY:\s*/i, "")
            .replace(/\]\.?$/, "")
            .replace(/\.$/, "");
        if (!cleaned) return "";
        return `[RECOMMENDED FOR REPORTING: the light-microscopy community recommends also reporting ${cleaned}. ${REPORTING_METADATA_HINT}]`;
    }

    const METHOD_SETTINGS_PROMPTS = {
        multiphoton: reportingRecommendation(
            "excitation wavelength, mean power at the sample, and pulse width"),
        light_sheet: reportingRecommendation(
            "light-sheet thickness, sheet numerical aperture, and the detection/illumination objective pairing"),
        tirf: reportingRecommendation(
            "TIRF excitation wavelength and the incidence angle or estimated evanescent-field penetration depth, where available"),
        sted: reportingRecommendation(
            "STED depletion wavelength and power at the sample, time-gating settings where used, and the phase-mask/beam-shaping configuration"),
        sim: reportingRecommendation(
            "SIM pattern/orientation settings and the reconstruction software/version and parameters used"),
        smlm: reportingRecommendation(
            "number of frames, exposure time, activation/excitation settings, localization software/version, and drift-correction method"),
        ism: reportingRecommendation(
            "detector/reconstruction mode and the reconstruction software/version and settings used"),
        resolft: reportingRecommendation(
            "the on/off switching wavelengths and illumination doses, the switching cycle timing, and the number of switching cycles per pixel"),
        // Contrast optics are the part of a transmitted-light acquisition a reader
        // cannot reconstruct from the objective alone.
        phase_contrast: reportingRecommendation(
            "the condenser and phase annulus used (for example Ph1, Ph2 or Ph3) and the matching phase objective"),
        dic: reportingRecommendation(
            "the DIC prism/Wollaston set, the polariser and analyser, and the condenser setting used"),
        darkfield: reportingRecommendation(
            "the darkfield condenser used and its numerical-aperture range"),
    };
    const PATH_SETTINGS_PROMPTS = {
        confocal_point: reportingRecommendation(
            "confocal pinhole diameter (in Airy units), when a confocal pinhole was used, plus scan zoom, pixel dwell time, and line/frame averaging"),
        confocal_spinning_disk: reportingRecommendation(
            "camera exposure per channel, and any disk setting that was varied (for example rotation speed or the pinhole pattern, if the system offers a choice)"),
    };
    const READOUT_SETTINGS_PROMPTS = {
        "flim": "[PLEASE SPECIFY: how fluorescence lifetimes were acquired and analysed, including whether acquisition was time-domain or frequency-domain; report the relevant timing or modulation settings, calibration and how the instrument response was determined, signal or photon statistics where applicable, and the fitting or phasor analysis used]",
        "spectral imaging": "[PLEASE SPECIFY: the spectral detection windows (start, end and step) and, if the spectra were unmixed, the method and reference spectra used]",
        "fcs": "[PLEASE SPECIFY: FCS measurement duration, number of repeats, how the confocal volume was calibrated, and the fitting model]",
        "fret": "[PLEASE SPECIFY: how FRET was measured (for example sensitised emission, acceptor photobleaching or lifetime) and, for intensity-based measurements, the bleed-through and cross-excitation correction factors]",
    };

    function modalitySettingsPrompts(methodSelections, routeSelections, readoutSelections) {
        // Method and path answer different questions. The selected method supplies
        // technique-specific settings (for example STED depletion power); the
        // physical route can add implementation settings (for example scan dwell
        // time) without claiming that the route family is itself the method. For
        // legacy records with no method mapping, retain the old route-as-fallback
        // recommendation so retired instruments do not lose useful guidance.
        const methodPrompts = methodSelections.map(
            item => METHOD_SETTINGS_PROMPTS[cleanText(item.id).toLowerCase()] || "");
        const pathPrompts = routeSelections.map(
            item => PATH_SETTINGS_PROMPTS[cleanText(item.routeType).toLowerCase()] || "");
        const legacyMethodPrompts = methodSelections.length
            ? []
            : routeSelections.map(
                item => METHOD_SETTINGS_PROMPTS[cleanText(item.routeType).toLowerCase()] || "");
        const prompts = uniqueTexts([...methodPrompts, ...pathPrompts, ...legacyMethodPrompts]);
        readoutSelections.forEach((item) => {
            const prompt = READOUT_SETTINGS_PROMPTS[cleanText(item.displayLabel).toLowerCase()];
            if (prompt) prompts.push(prompt);
        });
        return uniqueTexts(prompts);
    }

    /**
     * Assemble one acquisition entry: finished prose, then the review block.
     *
     * Publication prose is built from the structured selections and, when the user
     * has confirmed one, the runtime plan. Review requests are collected from the
     * places that produce them, not recovered from the finished text, so a
     * component whose own name contains brackets is never mistaken for a request
     * and no request can be corrupted by a later rewrite.
     */
    // The role a source can plausibly have follows from the path it sits on. The
    // record is still the only thing that can state it, but the question put to the
    // author should not offer alternatives the selected path rules out.
    const ROUTE_TYPE_ROLE_EXAMPLES = {
        transmitted_light: "transmitted illumination",
        reflected_light: "reflected illumination",
    };
    const DEFAULT_ROLE_EXAMPLES = "excitation or, on a depletion-based system, depletion";
    const SOURCE_ROLE_PROMPT_PREFIX = "[PLEASE SPECIFY: the role of ";
    // Roles that do not create an imaging channel. Counting them as channels asked
    // a STED author in what order their depletion beam was acquired.
    const NON_CHANNEL_SOURCE_ROLES = new Set(["depletion", "activation", "alignment", "switching"]);
    // Methods whose defining hardware is selectable, so its absence is a fact about
    // the draft rather than about the instrument.
    const METHOD_REQUIRED_SOURCE_ROLES = {
        sted: {
            role: "depletion",
            missing: "[PLEASE VERIFY: STED imaging is reported but no depletion source was selected; confirm the depletion laser and the power used at the sample]",
        },
    };
    const DEPLETION_METHOD_IDS = new Set(["sted", "resolft"]);

    /**
     * Name a light path without repeating the word it already ends with.
     *
     * The recorded label for the transmitted path is "Transmitted light", so
     * appending "light path" produced "the transmitted light light path".
     */
    function lightPathPhrase(displayLabel) {
        const label = lowerLabel(displayLabel);
        return /\blight$/.test(label) ? `${label} path` : `${label} light path`;
    }

    function roleExamplesForRoutes(routeSelections) {
        const examples = uniqueTexts(routeSelections
            .map(item => ROUTE_TYPE_ROLE_EXAMPLES[cleanText(item.routeType).toLowerCase()])
            .filter(Boolean));
        // A source on a transmitted path is not plausibly a depletion beam, and a
        // fluorescence line is not plausibly the condenser lamp. The alternatives
        // offered follow the path the source itself sits on, not the whole entry.
        return examples.length ? humanJoin(examples) : DEFAULT_ROLE_EXAMPLES;
    }

    function roleExamplesForSource(source, routeSelections) {
        const owning = routeSelections.filter(route => (source.routeIds || []).includes(route.id));
        return roleExamplesForRoutes(owning.length ? owning : routeSelections);
    }

    /**
     * The phrases that name what was done, method first and path only as a fallback.
     *
     * A record with no imaging-method control (the retired multiphoton system) used
     * to fall through to an instrument-only sentence and a "with the Multiphoton
     * route" clause, so the finished text never said what the technique was.
     */
    function methodPhrasesForEntry(methodSelections, routeSelections) {
        const fromMethods = uniqueTexts(methodSelections.map(
            item => item.publicationPhrase || `${item.displayLabel} imaging`));
        if (fromMethods.length) return fromMethods;
        return uniqueTexts(routeSelections.map(
            item => item.publicationPhrase || `${item.displayLabel} imaging`));
    }

    function buildOpeningSentence(phrases, instrumentName, readoutLabels) {
        const ordered = phrases.length
            ? [phrases[0], ...phrases.slice(1).map(decapitalizePhrase)]
            : [];
        const subject = humanJoin(ordered);
        const verb = ordered.length > 1 ? "were" : "was";
        let sentence = subject
            ? `${subject} ${verb} performed using ${instrumentName}.`
            : `Images were acquired using ${instrumentName}.`;
        if (readoutLabels.length) {
            // A readout is something the same acquisition also recorded, not a
            // separate one-clause statement bolted onto the paragraph.
            sentence = `${sentence.replace(/\.$/, "")}, with ${humanJoin(readoutLabels.map(lowerLabel))} data acquired on the same light path.`;
        }
        return sentence;
    }

    /**
     * Group light-path selections by the recorded path each one sits on.
     *
     * With several methods in one acquisition the entry can travel two paths, and
     * merging them would put a transmitted lamp and a fluorescence laser into one
     * illumination clause. A component recorded on none of the selected paths, or on
     * all of them, belongs to the first group rather than to a group of its own.
     */
    const SHARED_ROUTE_GROUP = "";

    function groupSelectionsByRoute(selections, routeIds) {
        const groups = new Map(routeIds.map(id => [id, []]));
        const single = routeIds.length < 2;
        // A camera on both paths belongs to neither clause on its own. With one path
        // everything is that path's; with two, shared components are stated once,
        // after the per-path clauses.
        if (!single) groups.set(SHARED_ROUTE_GROUP, []);
        const fallback = single ? (routeIds[0] || SHARED_ROUTE_GROUP) : SHARED_ROUTE_GROUP;
        (selections || []).forEach((item) => {
            const owned = (item.routeIds || []).filter(id => groups.has(id) && id !== SHARED_ROUTE_GROUP);
            const target = owned.length === 1 ? owned[0] : fallback;
            if (!groups.has(target)) groups.set(target, []);
            groups.get(target).push(item);
        });
        return groups;
    }

    function routeGroupLead(routeId, methodSelections, routeSelections) {
        const labels = uniqueTexts(methodSelections
            .filter(method => (method.routeIds || []).includes(routeId))
            .map(method => method.displayLabel));
        if (labels.length) return humanJoin(labels.map(lowerLabel));
        const route = routeSelections.find(item => item.id === routeId);
        return route ? lowerLabel(route.displayLabel) : "";
    }

    /**
     * Assemble one acquisition entry: finished prose, then the review requests.
     *
     * Publication prose is built from the structured selections and, when the user
     * has confirmed one, the runtime plan. Review requests are collected from the
     * places that produce them, not recovered from the finished text, and are split
     * into requests about this acquisition and requests that apply to the whole
     * Methods section, so a three-acquisition draft does not repeat the same generic
     * advice three times.
     */
    function buildAcquisitionEntry(dto) {
        const prompts = [];
        const sectionPrompts = [];
        const methods = dto.methods || {};

        const methodSelections = getCheckedSelections("method");
        const routeSelections = getCheckedSelections("route");
        routeSelections
            .filter(item => item.topologyIncomplete)
            .forEach(item => prompts.push(
                `[PLEASE VERIFY: the recorded hardware for the ${lightPathPhrase(item.displayLabel)} is incomplete; confirm the illumination and detection components used]`
            ));
        const runtime = runtimeAcquisitionFacts(dto);
        const routeIds = routeSelections.map(item => item.id);

        // Two paths in one entry is now something the user can state deliberately by
        // ticking two methods. It is still worth confirming when only one method
        // explains it, because an extra path is easy to tick by accident.
        if (routeIds.length > 1 && methodSelections.length < 2) {
            prompts.push(`[PLEASE VERIFY: ${routeIds.length} light paths are reported for a single acquisition (${humanJoin(routeSelections.map(item => lowerLabel(item.displayLabel)))}); confirm that each was used, or add a separate entry per acquisition]`);
        }

        const displayName = cleanText(dto.display_name) || cleanText(dto.id);
        const instrumentName = cleanText(methods.instrument_reference)
            || (displayName ? `the ${displayName}` : "the microscope");
        const methodPhrases = methodPhrasesForEntry(methodSelections, routeSelections);
        const readoutSelections = getCheckedSelections("readout");
        const openingSentence = buildOpeningSentence(
            methodPhrases, instrumentName, readoutSelections.map(item => item.displayLabel));

        const techniquePrompts = modalitySettingsPrompts(methodSelections, routeSelections, readoutSelections);
        prompts.push(...techniquePrompts);
        const objectives = mergeByPublicationTemplate(getCheckedSelections("obj"));
        prompts.push(...objectives.prompts);

        // A component recorded in two categories - the RESCue STED module and the
        // adaptive-illumination entry naming the same unit - is one fact.
        const moduleSelections = getCheckedSelections("module");
        const moduleLabels = moduleSelections.map(item => cleanText(item.displayLabel).toLowerCase());
        const specialistSelections = ["optical-modulator", "illumination-logic"]
            .flatMap(prefix => getCheckedSelections(prefix))
            .filter(item => {
                const label = cleanText(item.displayLabel).toLowerCase();
                return !label || !moduleLabels.some(moduleLabel => moduleLabel.includes(label) || label.includes(moduleLabel));
            });

        const equipment = mergeByPublicationTemplate([
            ...moduleSelections,
            ...getCheckedSelections("scanner"),
            ...getCheckedSelections("magnification-changer"),
        ]);
        prompts.push(...equipment.prompts);
        const confirmedActions = mergeByPublicationTemplate(getCheckedSelections("confirmed"));
        // One request for the versions of the products confirmed, rather than one
        // per LAS X workflow module.
        const versionPattern = /^\[PLEASE SPECIFY: acquisition software version for (.+)\]$/;
        const missingVersions = uniqueTexts(confirmedActions.prompts
            .map(prompt => (versionPattern.exec(cleanText(prompt)) || [])[1]));
        prompts.push(...confirmedActions.prompts.filter(prompt => !versionPattern.test(cleanText(prompt))));
        if (missingVersions.length) {
            prompts.push(`[PLEASE SPECIFY: the version of ${humanJoin(missingVersions)}]`);
        }

        const paragraphHardware = dedupeSentences([
            openingSentence,
            ...objectives.sentences,
            ...equipment.sentences,
            ...confirmedActions.sentences,
        ]).join(" ");

        // Manual selections and confirmed plan components are merged in one pass,
        // keyed by component id, so a component the user ticked and the plan also
        // names is stated once - using the plan's reading, which carries the
        // wavelength, filter position or detection window the checkbox cannot.
        const checkedRouteIds = new Set(routeIds);
        const allPositionSelections = getCheckedSelections("filterposition");
        const positionSelections = allPositionSelections.filter(item =>
            !checkedRouteIds.size
            || !item.routeIds.length
            || item.routeIds.some(id => checkedRouteIds.has(id)));
        allPositionSelections
            .filter(item => !positionSelections.includes(item))
            .forEach((item) => {
                prompts.push(`[PLEASE VERIFY: ${item.displayLabel} is not recorded on the light path being reported, so it is not described; confirm the path and the filter that were used]`);
            });

        // Several positions of one holder is a legitimate multi-channel report, but
        // the holder can only be at one of them at a time, so the order matters.
        const positionsByHolder = new Map();
        positionSelections.forEach((item) => {
            const holder = cleanText(item.componentId) || cleanText(item.id).split("::")[0];
            if (!positionsByHolder.has(holder)) positionsByHolder.set(holder, []);
            positionsByHolder.get(holder).push(item);
        });
        positionsByHolder.forEach((items, holder) => {
            if (items.length < 2) return;
            if (items.every(item => cleanText(item.selectionMode) === "multiple")) return;
            const holderLabel = cleanText(items[0].componentDisplayLabel) || holder;
            prompts.push(`[PLEASE SPECIFY: ${items.length} positions of the ${holderLabel} are reported, and it holds one at a time; state which filter was used for which channel]`);
        });

        // Ticking a holder says light passed through the container, which is the
        // uninformative claim that offering positions exists to replace. Where
        // positions are on offer the holder itself is never a sentence.
        const holdersWithPositions = new Set(
            Array.from(document.querySelectorAll('input[id^="filterposition-"]'))
                .map(input => cleanText(input.dataset.componentId))
                .filter(Boolean)
        );
        const lightSelections = getCheckedSelections("light");
        const detectorSelections = getCheckedSelections("det");
        const lightPathSelections = [
            ...lightSelections,
            ...getCheckedSelections("filter").filter(item => !holdersWithPositions.has(cleanText(item.id))),
            ...getCheckedSelections("splitter"),
            ...detectorSelections,
            ...specialistSelections,
        ];
        prompts.push(...positionSelections.flatMap(item => item.reviewPrompts || []));

        const positionGroups = groupSelectionsByRoute(positionSelections, routeIds);
        const routeGroups = groupSelectionsByRoute(
            [...runtime.components, ...lightPathSelections], routeIds);
        const lightPathParagraphs = [];
        let lightPathPrompts = [];
        routeGroups.forEach((items, routeId) => {
            const positions = positionGroups.get(routeId) || [];
            if (!items.length && !positions.length) return;
            const merged = mergeByPublicationTemplate(items, {
                articleFor: item => cleanText(item.inventoryClass) === "light_source",
            });
            lightPathPrompts = lightPathPrompts.concat(merged.prompts);
            // Illumination, then the optics it passed through, then detection.
            const illumination = merged.sentences.filter(sentence => /provided by|performed using/i.test(sentence));
            const detection = merged.sentences.filter(sentence => /recorded using|observed through/i.test(sentence));
            const other = merged.sentences.filter(
                sentence => !illumination.includes(sentence) && !detection.includes(sentence));
            let sentences = [
                ...illumination,
                ...filterPositionSentences(positions),
                ...other,
                ...detection,
            ];
            if (!sentences.length) return;
            if (routeGroups.size > 1 && routeId !== SHARED_ROUTE_GROUP) {
                const lead = routeGroupLead(routeId, methodSelections, routeSelections);
                if (lead) {
                    sentences = [`For the ${lead} images, ${decapitalizePhrase(sentences[0])}`, ...sentences.slice(1)];
                }
            }
            lightPathParagraphs.push(dedupeSentences(sentences).join(" "));
        });
        if (runtime.sentences.length) {
            lightPathParagraphs.push(dedupeSentences(runtime.sentences).join(" "));
        }

        // One grouped question instead of one per source, with the alternatives the
        // selected light path actually allows.
        const roleFreeLightPathPrompts = lightPathPrompts.filter(
            prompt => !cleanText(prompt).startsWith(SOURCE_ROLE_PROMPT_PREFIX));
        prompts.push(...roleFreeLightPathPrompts, ...runtime.prompts);
        const unroledSources = lightSelections.filter(item => !cleanText(item.role));
        const unroledByExamples = new Map();
        unroledSources.forEach((item) => {
            const examples = roleExamplesForSource(item, routeSelections);
            if (!unroledByExamples.has(examples)) unroledByExamples.set(examples, []);
            unroledByExamples.get(examples).push(item.publicationLabel || item.displayLabel);
        });
        unroledByExamples.forEach((rawLabels, examples) => {
            const labels = uniqueTexts(rawLabels);
            if (!labels.length) return;
            prompts.push(`[PLEASE SPECIFY: the role of ${humanJoin(labels)} in this acquisition (for example ${examples}); it is not recorded ${labels.length === 1 ? "for this source" : "for these sources"}]`);
        });

        // More than one imaging channel leaves the reader unable to tell simultaneous
        // from sequential acquisition. A depletion or activation beam is not a channel.
        const channelCount = lightSelections.filter(
            item => !NON_CHANNEL_SOURCE_ROLES.has(cleanText(item.role).toLowerCase())).length;
        if (channelCount > 1 || detectorSelections.length > 1) {
            prompts.push("[PLEASE SPECIFY: whether the channels were acquired sequentially or simultaneously, and in what order]");
        }

        // What the entry states about itself, checked against what a Methods section
        // has to contain. These are not database gaps: the record has the answer and
        // the draft is silent because nothing was ticked.
        if (!objectives.sentences.length) {
            prompts.push("[PLEASE SPECIFY: the objective used for this acquisition, including magnification, numerical aperture and immersion medium]");
        }
        if (!lightSelections.length && !runtime.sources.length) {
            prompts.push("[PLEASE SPECIFY: the illumination used for this acquisition, including the source and the wavelength or spectral range]");
        }
        if (!detectorSelections.length && !runtime.endpoints.length) {
            prompts.push("[PLEASE SPECIFY: the detector, camera or eyepieces used to record this acquisition]");
        }

        const selectedMethodIds = new Set(methodSelections.map(item => cleanText(item.id).toLowerCase()));
        const selectedSourceRoles = new Set(lightSelections.map(item => cleanText(item.role).toLowerCase()).filter(Boolean));
        selectedMethodIds.forEach((methodId) => {
            const requirement = METHOD_REQUIRED_SOURCE_ROLES[methodId];
            if (requirement && !selectedSourceRoles.has(requirement.role)) {
                prompts.push(requirement.missing);
            }
        });
        // A module that belongs to a technique the acquisition does not claim is the
        // most common way a previous acquisition's hardware survives into this one.
        const selectedTechniqueIds = new Set([
            ...selectedMethodIds,
            ...readoutSelections.map(item => cleanText(item.id).split(":").pop().toLowerCase()),
            ...readoutSelections.map(item => cleanText(item.displayLabel).toLowerCase()),
        ]);
        const offeredTechniqueIds = new Set(Array.from(
            document.querySelectorAll('input[id^="method-"], input[id^="readout-"]'))
            .flatMap(input => [
                cleanText(input.value).split(":").pop().toLowerCase(),
                cleanText(input.dataset.displayLabel).toLowerCase(),
            ]));
        moduleSelections.forEach((module) => {
            // The module's own record says which technique it implements, from
            // vocab/modules.yaml `tags.provides_capability`. Nothing here decides
            // that, and nothing here hides a module: a record may legitimately
            // describe a use the vocabulary does not anticipate. This only asks the
            // author to confirm when the acquisition claims none of the techniques
            // the module is for.
            const provided = Object.values(module.providesCapability || {})
                .filter(Array.isArray)
                .flat()
                .filter(entry => entry && cleanText(entry.id));
            if (!provided.length) return;
            const unclaimed = provided.filter(entry => !selectedTechniqueIds.has(cleanText(entry.id).toLowerCase()));
            if (unclaimed.length < provided.length) return;
            // Never ask about a technique this microscope does not record.
            const askable = unclaimed.filter(entry => offeredTechniqueIds.has(cleanText(entry.id).toLowerCase()));
            if (!askable.length) return;
            const names = humanJoin(askable.map(entry => cleanText(entry.display_label) || cleanText(entry.id)));
            prompts.push(`[PLEASE VERIFY: the ${module.displayLabel} module is reported but ${names} ${askable.length > 1 ? "are" : "is"} not among the methods selected for this acquisition; confirm the methods and the modules that were used]`);
        });

        if (selectedSourceRoles.has("depletion")
            && methodPhrases.length
            && !Array.from(selectedMethodIds).some(id => DEPLETION_METHOD_IDS.has(id))) {
            prompts.push(`[PLEASE VERIFY: a depletion source is reported for an acquisition described as ${humanJoin(methodPhrases.map(decapitalizePhrase))}; confirm the method and the sources that were used]`);
        }

        prompts.push(cleanText(methods.retired_review_prompt));
        // Ask about the selectors whose position is still unknown, not about the
        // ones the user has just named, and only on the paths in use.
        const resolvedComponentIds = new Set(positionSelections.map(item => cleanText(item.id).split("::")[0]));
        const selectedRouteLabels = new Set(routeSelections.map(item => item.displayLabel));
        const unresolvedOptics = (Array.isArray(methods.unresolved_optics) ? methods.unresolved_optics : [])
            .filter(entry => entry && !resolvedComponentIds.has(cleanText(entry.inventory_id)))
            .filter(entry => !selectedRouteLabels.size
                || !cleanText(entry.route_label)
                || selectedRouteLabels.has(cleanText(entry.route_label)));
        if (Array.isArray(methods.unresolved_optics) && methods.unresolved_optics.length) {
            if (unresolvedOptics.length) {
                // The scoped label carries the route name, which is a routing term.
                // The question is about the holder, so only the holder is named.
                const holders = uniqueTexts(unresolvedOptics.map(entry => cleanText(entry.display_label) || cleanText(entry.scoped_label)));
                prompts.push(`[PLEASE SPECIFY: which position of the ${humanJoin(holders)} was used for acquisition, including the filter/dichroic identity (manufacturer + model/catalogue number)]`);
            }
        } else if (methods.quarep_light_path_recommendation_needed) {
            prompts.push(cleanText(methods.quarep_light_path_recommendation));
        }

        // Specimen preparation and the catch-all settings list are the same request
        // whatever the acquisition, so they are stated once for the whole section.
        sectionPrompts.push(cleanText(methods.specimen_preparation_recommendation));
        const acquisitionSettingsRecommendation = cleanText(methods.acquisition_settings_recommendation);
        if (techniquePrompts.length && acquisitionSettingsRecommendation) {
            sectionPrompts.push(reportingRecommendation(
                "any remaining acquisition settings needed to reproduce the experiment that are not already reported above, including pixel size (µm/px), z-step (µm), time interval, and tiling overlap where applicable"));
        } else {
            sectionPrompts.push(reportingRecommendation(acquisitionSettingsRecommendation));
        }

        // A record-quality gap belongs in this draft only when the draft reports the
        // thing it is about. The page banner lists every gap for the instrument.
        const reportedCategories = new Set();
        if (confirmedActions.sentences.length) reportedCategories.add("software");
        if (moduleSelections.length) reportedCategories.add("module");
        if (detectorSelections.length) reportedCategories.add("detector");
        if (objectives.sentences.length) reportedCategories.add("objective");
        if (getCheckedSelections("scanner").length) reportedCategories.add("scanner");
        if (lightSelections.length) reportedCategories.add("source");
        // The draft has already asked for the version of the software the user
        // confirmed; repeating it as a record-quality note asks twice.
        if (missingVersions.length) reportedCategories.delete("software");
        const methodsMetadataStatus = getMethodsMetadataStatus(dto);
        if (methodsMetadataStatus.isBlocked) {
            const labels = uniqueTexts(methodsMetadataStatus.blockers
                .filter(blocker => blockerAppliesToEntry(blocker, reportedCategories))
                .map(formatBlockerLabel));
            if (labels.length) {
                prompts.push(`[PLEASE VERIFY: ${humanJoin(labels)} ${labels.length === 1 ? "is" : "are"} not recorded for this instrument; confirm the exact values with facility staff]`);
            }
        }

        const compatModalityText = shouldUseLegacyModalities(dto)
            ? cleanText(groupedLabelSentence("modality", getCheckedSelections("modality")))
            : "";

        return {
            paragraphs: [paragraphHardware, ...lightPathParagraphs, compatModalityText]
                .map(cleanText).filter(Boolean),
            entryPrompts: uniqueTexts(prompts.map(prompt => cleanText(prompt).replace(/\.$/, ""))),
            sectionPrompts: uniqueTexts(sectionPrompts.map(prompt => cleanText(prompt).replace(/\.$/, ""))),
        };
    }

    // Which part of a draft a recorded metadata gap is about. Schema-shaped gaps
    // (route types, element ids, capability axes) describe the record itself and
    // belong in the page banner, never in a manuscript checklist.
    const BLOCKER_CATEGORY_PATTERNS = [
        [/software/i, "software"],
        [/module/i, "module"],
        [/detector|camera/i, "detector"],
        [/objective/i, "objective"],
        [/scanner/i, "scanner"],
        [/light source|laser|lamp|illumination/i, "source"],
    ];

    function blockerAppliesToEntry(blocker, reportedCategories) {
        const text = `${blocker?.title || ""} ${blocker?.path || ""}`;
        const match = BLOCKER_CATEGORY_PATTERNS.find(([pattern]) => pattern.test(text));
        if (!match) return false;
        return reportedCategories.has(match[1]);
    }

    // Everything a single acquisition asserts. The acquisition reference and the
    // confirmed session actions (software, incubation, autofocus) describe the
    // session rather than one image set, so they are not cleared between them.
    // Everything a user ticks to describe one acquisition. "confirmed" belongs here
    // with the rest: the confirmable actions include the acquisition software, the
    // environmental control and the post-acquisition processing, and a processing
    // step that survives into the next acquisition is a claim nobody made.
    const ACQUISITION_SCOPED_PREFIXES = [
        "route", "readout", "light", "det", "filter", "filterposition", "splitter",
        "modality", "module", "scanner", "obj", "magnification-changer",
        "optical-modulator", "illumination-logic", "confirmed",
    ];

    function clearInputsByPrefixes(prefixes) {
        prefixes.forEach((prefix) => {
            document.querySelectorAll(`input[id^="${prefix}-"]`).forEach((input) => { input.checked = false; });
        });
    }

    /**
     * Begin describing a different acquisition on the same microscope.
     *
     * Selections are per acquisition. Keeping them ticked after one has been added
     * is what let an objective, a module or a scanner from the first entry be stated
     * as a fact about the second.
     */
    function startNewAcquisition({ keepMethods = false, keepLabel = false } = {}) {
        clearInputsByPrefixes(ACQUISITION_SCOPED_PREFIXES);
        // A reviewed runtime plan describes one acquisition too. Leaving it
        // confirmed would republish its sources, detector and filters under the
        // next entry without the user confirming them again.
        if (runtimeConfirm) runtimeConfirm.checked = false;
        if (!keepMethods) clearInputsByPrefixes(["method"]);
        if (!keepLabel) {
            const sessionLabel = document.getElementById("session-label");
            if (sessionLabel) sessionLabel.value = "";
        }
        activeEntryKey = "";
        if (currentInst) {
            applyMethodAvailability(currentInst);
            confirmSoleRouteWithoutMethodControl(currentInst);
        }
    }

    addBtn.addEventListener("click", () => {
        if (!currentInst) {
            setSelectionStatus("Choose a microscope first.");
            return;
        }

        const methodSection = document.getElementById("section-method");
        const methodFirst = Boolean(methodSection && methodSection.style.display !== "none");
        if (methodFirst && getCheckedIds("method").length === 0) {
            setSelectionStatus("Choose the imaging method used for this acquisition.");
            return;
        }
        // A record with no imaging-method control still records a light path, and an
        // acquisition that names none of them describes nothing.
        const routeSection = document.getElementById("section-route");
        const routeAvailable = Boolean(routeSection && routeSection.style.display !== "none");
        // A legacy record states its modality instead of a path, and answering that
        // question is the same answer.
        const legacyModalityChosen = getCheckedIds("modality").length > 0;
        if (routeAvailable && !legacyModalityChosen && getCheckedIds("route").length === 0) {
            setSelectionStatus("Choose the light path used for this acquisition.");
            return;
        }
        setSelectionStatus("");

        const dto = currentInst;
        if (!instrumentDtoIsRenderable(dto)) {
            outputText.value = `The record for ${cleanText(dto.display_name) || cleanText(dto.id) || "this instrument"} is incomplete, so a Methods draft cannot be generated from it. Ask facility staff to complete the instrument record.`;
            return;
        }
        renderMethodsMetadataWarning(dto);

        const entry = buildAcquisitionEntry(dto);
        const sessionLabel = cleanText(document.getElementById("session-label").value);
        const updating = Boolean(activeEntryKey) && accumulatedEntries.has(activeEntryKey);
        if (!updating) {
            entrySequence += 1;
            activeEntryKey = `entry-${entrySequence}`;
        }
        accumulatedEntries.set(activeEntryKey, {
            instrumentId: dto.id,
            reference: sessionLabel,
            paragraphs: entry.paragraphs,
            entryPrompts: entry.entryPrompts,
            sectionPrompts: entry.sectionPrompts,
        });
        usedInstruments.set(dto.id, dto.display_name || dto.id);
        updateOutputText();
        setSelectionStatus(updating
            ? `Updated the acquisition you last added${sessionLabel ? ` (${sessionLabel})` : ""}. Choose “Start another acquisition” to describe a different one.`
            : `Added acquisition ${accumulatedEntries.size}. Change a selection to correct it, or choose “Start another acquisition” to describe a different one.`);
    });

    if (newAcquisitionBtn) {
        newAcquisitionBtn.addEventListener("click", () => {
            startNewAcquisition();
            setSelectionStatus("Cleared the selections. Choose what you used for the next acquisition.");
        });
    }

    clearBtn.addEventListener("click", () => {
        accumulatedEntries = new Map();
        usedInstruments = new Map();
        entrySequence = 0;
        // "Start again" has to mean the controls too: leaving every box ticked is
        // how a cleared draft still produced the previous acquisition's hardware.
        startNewAcquisition();
        setSelectionStatus("");
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
