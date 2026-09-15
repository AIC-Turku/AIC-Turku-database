document.addEventListener("DOMContentLoaded", () => {
    const outputText = document.getElementById("output-text");
    const addBtn = document.getElementById("add-btn");
    const systemSelect = document.getElementById("system-select");
    const runtimeConfirm = document.getElementById("runtime-confirm");
    const runtimePreview = document.getElementById("runtime-preview");
    const runtimeStatus = document.getElementById("runtime-review-status");
    if (!outputText || !addBtn) return;

    const PUBLICATION_NEXT = String.raw`(?=\s+(?:Images were|Excitation used|The optical path|A\s|Review before publication:|\[PLEASE|Acknowledgements:)|\s*$)`;
    const RUNTIME_NEXT = String.raw`(?=\s+(?:Selected sources:|Selected endpoints\/detectors:|Selected wheel\/turret positions:|Selected splitter branches:|Exact runtime-selected configuration|Route-specific optical selections\/facts:|Sequential acquisition is planned as|Flattened\/incomplete optics were present for|Unsupported spectral model flags were present)|\s*$)`;

    function cleanText(value) {
        return typeof value === "string" ? value.trim() : "";
    }

    function uniqueTexts(values) {
        return Array.from(new Set((Array.isArray(values) ? values : []).map(cleanText).filter(Boolean)));
    }

    function humanJoin(values) {
        const items = uniqueTexts(values);
        if (!items.length) return "";
        if (items.length === 1) return items[0];
        if (items.length === 2) return `${items[0]} and ${items[1]}`;
        return `${items.slice(0, -1).join(", ")}, and ${items[items.length - 1]}`;
    }

    function escapeRegExp(value) {
        return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    }

    function publicationStatementRegex(start, end = "") {
        return new RegExp(
            `${escapeRegExp(start)}(.+?)${escapeRegExp(end)}\\.${PUBLICATION_NEXT}`,
            "g"
        );
    }

    function runtimeStatementRegex(start, end = "") {
        return new RegExp(
            `${escapeRegExp(start)}(.+?)${escapeRegExp(end)}\\.${RUNTIME_NEXT}`,
            "g"
        );
    }

    function normalizePositionNotation(value) {
        return cleanText(value).replace(
            /\s+@\s+([^—,\n]+?)(?=\s*(?:—|,|$))/g,
            (_, position) => ` (position ${cleanText(position)})`
        );
    }

    function normalizeOpticalIdentity(value) {
        return cleanText(value)
            .replace(/\s*\(position [^)]+\)/gi, "")
            .replace(/\s*\(branches [^)]+\)/gi, "")
            .replace(/\s*\[[^\]]+\]/g, "")
            .toLowerCase();
    }

    function parseRuntimeCandidate() {
        const raw = cleanText(runtimePreview?.textContent);
        if (!raw) return null;
        try {
            const parsed = JSON.parse(raw);
            return parsed && typeof parsed === "object" ? parsed : null;
        } catch (error) {
            return null;
        }
    }

    function runtimeRouteIsRecorded(route) {
        const target = cleanText(route);
        if (!target) return false;
        return Array.from(document.querySelectorAll('input[id^="route-"]')).some((checkbox) =>
            cleanText(checkbox.value) === target || cleanText(checkbox.dataset.displayLabel) === target
        );
    }

    function guardRuntimeRouteCandidate() {
        if (!runtimeConfirm) return true;
        const candidate = parseRuntimeCandidate();
        if (!candidate) return true;

        const route = cleanText(candidate.route);
        if (runtimeRouteIsRecorded(route)) return true;

        runtimeConfirm.checked = false;
        runtimeConfirm.disabled = true;
        if (runtimeStatus) {
            const label = route || "unspecified route";
            runtimeStatus.textContent =
                `This simulator plan refers to ${label}, which is not present in the instrument's recorded routes. ` +
                "It cannot be imported into publication Methods; verify the configuration in the simulator or with facility staff.";
        }
        return false;
    }

    function combineRepeatedStatement(text, start, end, formatter) {
        const regex = publicationStatementRegex(start, end);
        const matches = [];
        let match;
        while ((match = regex.exec(text)) !== null) {
            matches.push({ full: match[0], value: cleanText(match[1]) });
        }
        const values = uniqueTexts(matches.map(item => item.value));
        if (values.length < 2) return text;

        const replacement = formatter(values);
        let replaced = text;
        matches.forEach((item, index) => {
            replaced = replaced.replace(item.full, index === 0 ? replacement : "");
        });
        return replaced.replace(/\s{2,}/g, " ").trim();
    }

    function formatSplitterSelection(value) {
        return normalizePositionNotation(value).replace(/\s*\[([^\]]+)\]/g, (_, branchText) => {
            const branches = branchText.split(",").map(cleanText).filter(Boolean);
            return branches.length ? ` (branches ${humanJoin(branches)})` : "";
        });
    }

    function formatRouteFacts(value) {
        return normalizePositionNotation(value)
            .replace(
                /\s*—\s*cube internals\s*\(EX\s*([^;]+);\s*DI\s*([^;]+);\s*EM\s*([^)]+)\)/gi,
                (_, excitation, dichroic, emission) =>
                    `; excitation ${cleanText(excitation)}, dichroic ${cleanText(dichroic)}, emission ${cleanText(emission)}`
            )
            .replace(
                /\s*—\s*product code\s+(.+?)(?=\s*(?:—|$))/gi,
                (_, productCode) => ` (product code ${cleanText(productCode)})`
            )
            .replace(
                /\s*—\s*channel\s+(.+?)(?=\s*(?:—|$))/gi,
                (_, channel) => `; channel ${cleanText(channel)}`
            )
            .replace(
                /\s*—\s*selectable positions:\s*(.+?)(?=\s*(?:—|$))/gi,
                (_, positions) => `; selectable positions ${cleanText(positions)}`
            )
            .replace(
                /\s*—\s*caveats:\s*(.+?)(?=\s*(?:—|$))/gi,
                (_, caveat) => `; ${cleanText(caveat)}`
            )
            .replace(/\s*—\s*/g, "; ")
            .replace(/\s+;/g, ";")
            .replace(/;\s*;/g, "; ")
            .trim();
    }

    function formatSequentialAcquisition(value) {
        const steps = Array.from(value.matchAll(/step\s+\d+\s+\((.+?),\s*route\s+([^)]+)\)/gi))
            .map(match => ({ fluorophore: cleanText(match[1]), route: cleanText(match[2]) }))
            .filter(step => step.fluorophore);

        if (steps.length >= 2) {
            const routes = uniqueTexts(steps.map(step => step.route));
            if (routes.length <= 1) {
                return `${humanJoin(steps.map(step => step.fluorophore))} were acquired sequentially.`;
            }
            const labelled = steps.map(step =>
                step.route ? `${step.fluorophore} (${step.route} route)` : step.fluorophore
            );
            return `${humanJoin(labelled)} were acquired sequentially.`;
        }
        return `Images were acquired sequentially as ${cleanText(value)}.`;
    }

    function rewriteRuntimeLanguage(text) {
        let out = text;

        out = out.replace(
            new RegExp(`Exact runtime-selected configuration \\([^)]*\\) used route (.+?)\\.${RUNTIME_NEXT}`, "g"),
            (_, route) => `Images were acquired using the ${cleanText(route)} route.`
        );
        out = out.replace(runtimeStatementRegex("Selected sources: "),
            (_, value) => `Excitation used ${cleanText(value)}.`);
        out = out.replace(runtimeStatementRegex("Selected endpoints/detectors: "),
            (_, value) => `Images were recorded using ${cleanText(value)}.`);
        out = out.replace(runtimeStatementRegex("Selected wheel/turret positions: "), (_, value) =>
            `The optical path used ${normalizePositionNotation(value)}.`
        );
        out = out.replace(runtimeStatementRegex("Selected splitter branches: "), (_, value) =>
            `The optical path used ${formatSplitterSelection(value)}.`
        );
        out = out.replace(runtimeStatementRegex("Route-specific optical selections/facts: "), (_, value) =>
            `The optical path included ${formatRouteFacts(value)}.`
        );
        out = out.replace(runtimeStatementRegex("Sequential acquisition is planned as "), (_, value) =>
            formatSequentialAcquisition(value)
        );
        out = out.replace(runtimeStatementRegex("Flattened/incomplete optics were present for "), (_, value) =>
            `[PLEASE VERIFY: the optical configuration record is incomplete for ${cleanText(value)}].`
        );
        out = out.replace(
            new RegExp(`Unsupported spectral model flags were present \\((.+?)\\)\\.${RUNTIME_NEXT}`, "g"),
            (_, value) => `[PLEASE VERIFY: the recorded optical configuration contains unsupported spectral information for ${cleanText(value)}].`
        );

        return out;
    }

    function preferSpecificOpticalFacts(text) {
        const specificRegex = publicationStatementRegex("The optical path included ");
        const specific = specificRegex.exec(text);
        if (!specific) return text;

        const specificBody = cleanText(specific[1]).toLowerCase();
        return text.replace(publicationStatementRegex("The optical path used "), (full, value) => {
            const identity = normalizeOpticalIdentity(value);
            return identity && specificBody.includes(identity) ? "" : full;
        });
    }

    function combineBaseAndRouteSentences(text) {
        let out = text;
        out = out.replace(
            /Images were acquired using the (.+?)\.\s+Images were acquired using the (.+?) (route|routes)\./g,
            (_, instrument, routeLabel, routeWord) =>
                `Images were acquired using the ${cleanText(instrument)} with the ${cleanText(routeLabel)} ${routeWord}.`
        );
        out = out.replace(
            /Images were acquired on the (.+?)\.\s+Images were acquired using the (.+?) (route|routes)\./g,
            (_, instrument, routeLabel, routeWord) =>
                `Images were acquired on the ${cleanText(instrument)} using the ${cleanText(routeLabel)} ${routeWord}.`
        );
        out = out.replace(
            /Images were acquired using the (.+?) route\.\s+Images were acquired using the (.+?)\./g,
            (_, routeLabel, instrument) =>
                `Images were acquired using the ${cleanText(instrument)} with the ${cleanText(routeLabel)} route.`
        );
        return out;
    }

    function combineReadoutWithRoute(text) {
        let out = text;
        out = out.replace(
            /Images were acquired using the (.+?) with the (.+?) route\.\s+(.+?) readout was acquired using the \2 route\./g,
            (_, instrument, routeLabel, readout) =>
                `Images were acquired using the ${cleanText(instrument)} with the ${cleanText(routeLabel)} route using ${cleanText(readout)} readout.`
        );
        out = out.replace(
            /Images were acquired on the (.+?) using the (.+?) route\.\s+(.+?) readout was acquired using the \2 route\./g,
            (_, instrument, routeLabel, readout) =>
                `Images were acquired on the ${cleanText(instrument)} using the ${cleanText(routeLabel)} route with ${cleanText(readout)} readout.`
        );
        return out;
    }

    function promoteRouteSentence(text) {
        const match = text.match(/Images were acquired using the (.+?) route\.(?=\s|$)/);
        if (!match || text.startsWith(match[0])) return text;
        const remainder = text.replace(match[0], "").replace(/\s{2,}/g, " ").trim();
        return [match[0], remainder].filter(Boolean).join(" ");
    }

    function combinePublicationSentences(text) {
        let out = preferSpecificOpticalFacts(text);

        out = combineRepeatedStatement(
            out,
            "A ",
            " objective was used",
            values => `The ${humanJoin(values)} objectives were used.`
        );
        out = combineRepeatedStatement(
            out,
            "Images were recorded using ",
            "",
            values => `Images were recorded using ${humanJoin(values)}.`
        );
        out = combineRepeatedStatement(
            out,
            "Images were recorded on ",
            "",
            values => `Images were recorded on ${humanJoin(values)}.`
        );
        out = combineRepeatedStatement(
            out,
            "Excitation used ",
            "",
            values => `Excitation used ${humanJoin(values)}.`
        );

        out = combineBaseAndRouteSentences(out);
        out = combineReadoutWithRoute(out);
        out = promoteRouteSentence(out);

        return out.replace(/\s{2,}/g, " ").trim();
    }

    function reviewPromptLines(paragraph) {
        const prompts = [];
        const bracketPattern = /\[(PLEASE SPECIFY|PLEASE VERIFY):\s*([^\]]+)\]\.?/g;
        let match;
        while ((match = bracketPattern.exec(paragraph)) !== null) {
            prompts.push(`[${match[1]}: ${cleanText(match[2])}]`);
        }

        const missingMetadata = paragraph.match(/^Some instrument metadata is missing(?: \(([^)]+)\))?; ask staff to confirm the exact settings\.?$/i);
        if (missingMetadata) {
            const details = cleanText(missingMetadata[1]);
            prompts.push(details
                ? `[PLEASE VERIFY: instrument metadata is incomplete (${details})]`
                : "[PLEASE VERIFY: instrument metadata is incomplete]"
            );
        }
        return uniqueTexts(prompts);
    }

    function stripReviewPrompts(paragraph) {
        return paragraph
            .replace(/\[(PLEASE SPECIFY|PLEASE VERIFY):\s*[^\]]+\]\.?/g, "")
            .replace(/^Some instrument metadata is missing(?: \([^)]+\))?; ask staff to confirm the exact settings\.?$/i, "")
            .replace(/\s{2,}/g, " ")
            .trim();
    }

    function formatParagraph(paragraph) {
        const rewritten = combinePublicationSentences(rewriteRuntimeLanguage(paragraph));
        return {
            prose: stripReviewPrompts(rewritten),
            prompts: reviewPromptLines(rewritten),
        };
    }

    function appendReviewBlock(formatted, prompts) {
        const newPrompts = uniqueTexts(prompts);
        if (!newPrompts.length) return;

        const lastIndex = formatted.length - 1;
        const last = lastIndex >= 0 ? formatted[lastIndex] : "";
        if (last.startsWith("Review before publication:\n")) {
            const existing = last.split("\n").slice(1)
                .map(line => line.replace(/^-\s*/, ""))
                .filter(Boolean);
            const merged = uniqueTexts([...existing, ...newPrompts]);
            formatted[lastIndex] = `Review before publication:\n${merged.map(prompt => `- ${prompt}`).join("\n")}`;
            return;
        }

        formatted.push(`Review before publication:\n${newPrompts.map(prompt => `- ${prompt}`).join("\n")}`);
    }

    function composeAcrossParagraphs(value) {
        let out = value;
        out = out.replace(
            /Images were acquired using the (.+?)\.\n\nImages were acquired using the (.+?) route\./g,
            (_, instrument, routeLabel) =>
                `Images were acquired using the ${cleanText(instrument)} with the ${cleanText(routeLabel)} route.\n\n`
        );
        out = out.replace(
            /Images were acquired on the (.+?)\.\n\nImages were acquired using the (.+?) route\./g,
            (_, instrument, routeLabel) =>
                `Images were acquired on the ${cleanText(instrument)} using the ${cleanText(routeLabel)} route.\n\n`
        );
        return out
            .replace(/\n\n[ \t]+/g, "\n\n")
            .replace(/[ \t]+\n/g, "\n")
            .trim();
    }

    function formatOutput(value) {
        const text = cleanText(value);
        if (!text || text === 'Select an instrument, then choose “Add to methods”.') return value;

        const paragraphs = text.split(/\n\n+/).map(cleanText).filter(Boolean);
        const formatted = [];
        paragraphs.forEach((paragraph) => {
            if (paragraph.startsWith("Review before publication:\n")) {
                const prompts = paragraph.split("\n").slice(1)
                    .map(line => line.replace(/^-\s*/, ""))
                    .filter(Boolean);
                appendReviewBlock(formatted, prompts);
                return;
            }

            const result = formatParagraph(paragraph);
            if (result.prose) formatted.push(result.prose);
            appendReviewBlock(formatted, result.prompts);
        });
        return composeAcrossParagraphs(formatted.join("\n\n"));
    }

    // Reject stale or foreign simulator route identifiers before the acquisition
    // renderer can turn them into publication claims. This listener runs in the
    // capture phase, before the main renderer's click handler.
    addBtn.addEventListener("click", () => {
        guardRuntimeRouteCandidate();
    }, true);

    if (runtimeConfirm) {
        runtimeConfirm.addEventListener("change", () => {
            guardRuntimeRouteCandidate();
        });
    }
    if (systemSelect) {
        systemSelect.addEventListener("change", () => {
            queueMicrotask(() => guardRuntimeRouteCandidate());
        });
    }

    // The acquisition renderer writes the auditable literal draft synchronously.
    // Format only after all click handlers have completed so this layer never
    // changes the evidence used to generate the draft.
    addBtn.addEventListener("click", () => {
        queueMicrotask(() => {
            outputText.value = formatOutput(outputText.value);
        });
    });
});
