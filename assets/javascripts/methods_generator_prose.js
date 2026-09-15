document.addEventListener("DOMContentLoaded", () => {
    const outputText = document.getElementById("output-text");
    const addBtn = document.getElementById("add-btn");
    if (!outputText || !addBtn) return;

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

    function normalizePositionNotation(value) {
        return cleanText(value).replace(/\s+@\s+([^—,.]+)(?=\s*(?:—|,|\.|$))/g, " (position $1)");
    }

    function normalizeOpticalIdentity(value) {
        return cleanText(value)
            .replace(/\s*\(position [^)]+\)/gi, "")
            .replace(/\s*\[[^\]]+\]/g, "")
            .toLowerCase();
    }

    function combineRepeatedSentences(text, pattern, formatter) {
        const matches = [];
        let match;
        const regex = new RegExp(pattern.source, pattern.flags.includes("g") ? pattern.flags : `${pattern.flags}g`);
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

    function rewriteRuntimeLanguage(text) {
        let out = text;

        out = out.replace(
            /Exact runtime-selected configuration \([^)]*\) used route ([^.]+)\./g,
            "Images were acquired using the $1 route."
        );
        out = out.replace(/Selected sources:\s*([^.]+)\./g, "Excitation used $1.");
        out = out.replace(/Selected endpoints\/detectors:\s*([^.]+)\./g, "Images were recorded using $1.");
        out = out.replace(/Selected wheel\/turret positions:\s*([^.]+)\./g, (_, value) => {
            return `The optical path used ${normalizePositionNotation(value)}.`;
        });
        out = out.replace(/Selected splitter branches:\s*([^.]+)\./g, (_, value) => {
            return `The optical path used ${normalizePositionNotation(value)}.`;
        });
        out = out.replace(/Route-specific optical selections\/facts:\s*([^\n]+?)\.(?=\s|$)/g, (_, value) => {
            const cleaned = normalizePositionNotation(value)
                .replace(/\s+—\s+product code\s+([^—,.]+)/g, " (product code $1)")
                .replace(/\s+—\s+/g, "; ");
            return `The optical path included ${cleaned}.`;
        });
        out = out.replace(/Sequential acquisition is planned as\s+([^.]+)\./g, "Images were acquired sequentially as $1.");
        out = out.replace(/Flattened\/incomplete optics were present for\s+([^.]+)\./g,
            "[PLEASE VERIFY: the optical configuration record is incomplete for $1]."
        );
        out = out.replace(/Unsupported spectral model flags were present \(([^)]+)\)\./g,
            "[PLEASE VERIFY: the recorded optical configuration contains unsupported spectral information for $1]."
        );

        return out;
    }

    function preferSpecificOpticalFacts(text) {
        const specific = text.match(/The optical path included ([^.]+)\./);
        if (!specific) return text;
        const specificBody = specific[1].toLowerCase();
        return text.replace(/The optical path used ([^.]+)\./g, (full, value) => {
            const identity = normalizeOpticalIdentity(value);
            return identity && specificBody.includes(identity) ? "" : full;
        });
    }

    function combinePublicationSentences(text) {
        let out = preferSpecificOpticalFacts(text);

        out = combineRepeatedSentences(
            out,
            /A ([^.]+?) objective was used\./g,
            values => `The ${humanJoin(values)} objectives were used.`
        );
        out = combineRepeatedSentences(
            out,
            /Images were recorded using ([^.]+)\./g,
            values => `Images were recorded using ${humanJoin(values)}.`
        );
        out = combineRepeatedSentences(
            out,
            /Images were recorded on ([^.]+)\./g,
            values => `Images were recorded on ${humanJoin(values)}.`
        );
        out = combineRepeatedSentences(
            out,
            /Excitation used ([^.]+)\./g,
            values => `Excitation used ${humanJoin(values)}.`
        );

        out = out.replace(
            /Images were acquired using the ([^.]+)\.\s+Images were acquired using the ([^.]+) route\./g,
            "Images were acquired using the $1 with the $2 route."
        );
        out = out.replace(
            /Images were acquired on the ([^.]+)\.\s+Images were acquired using the ([^.]+) route\./g,
            "Images were acquired on the $1 using the $2 route."
        );
        out = out.replace(
            /Images were acquired using the ([^.]+) route\.\s+Images were acquired using the ([^.]+)\./g,
            "Images were acquired using the $2 with the $1 route."
        );

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
        const prompts = reviewPromptLines(rewritten);
        const prose = stripReviewPrompts(rewritten);

        if (!prompts.length) return prose;
        const reviewBlock = `Review before publication:\n${prompts.map(prompt => `- ${prompt}`).join("\n")}`;
        return [prose, reviewBlock].filter(Boolean).join("\n\n");
    }

    function formatOutput(value) {
        const text = cleanText(value);
        if (!text || text === 'Select an instrument, then choose “Add to methods”.') return value;

        const paragraphs = text.split(/\n\n+/).map(cleanText).filter(Boolean);
        const formatted = [];
        paragraphs.forEach((paragraph) => {
            if (paragraph === "Review before publication:" || paragraph.startsWith("- [PLEASE ")) {
                formatted.push(paragraph);
                return;
            }
            const result = formatParagraph(paragraph);
            if (result) formatted.push(result);
        });
        return formatted.join("\n\n");
    }

    // The acquisition renderer writes the auditable literal draft synchronously.
    // Format only after all click handlers have completed so this layer never
    // changes selection state or the evidence used to generate the draft.
    addBtn.addEventListener("click", () => {
        queueMicrotask(() => {
            outputText.value = formatOutput(outputText.value);
        });
    });
});